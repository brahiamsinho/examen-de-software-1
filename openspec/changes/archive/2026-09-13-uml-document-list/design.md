# Design: UML Document List

## Technical Approach

Additive on both sides. Backend adds one row to the existing three-file
shape: `GET ""` in `api.py` → `list_documents` in `services.py` →
`DocumentSummaryOut` in `schemas.py`, gated exactly like
`get_document_view` — **verified against source**: `api.py:50-54` calls
`resolve_membership` and nothing else, so any member (including `VIEWER`)
reads. Frontend adds `listDocuments` + `DocumentSummary` to
`lib/uml_documents.ts`, a `useDocuments(orgSlug)` container hook, a
presentational `DocumentList`, and a "Mis Diagramas" section in
`dashboard/page.tsx`. No model, migration, or command-bus change.

## Decision Drivers

- `services.py`'s module docstring pins it as the **only** place that
  reassembles a `ProjectDocument` from a row + decoded codec triple.
  Nothing outside it may read `row.data`.
- `UmlDocument.objects` raises `TenantScopeViolation` on unscoped access;
  every query goes through `.for_organization(org)`.
- `UmlDocument.Meta` declares only an index — **no `ordering`** — so list
  order is undefined unless the service states it.
- `org_slug` lives in the mount prefix, so django-ninja 1.7 needs
  `Path[str]` explicitly (see `organizations/api.py`'s memberships note);
  a plain `str` defaults to "query" and 404s every request.
- `state/document.ts` and `state/members.ts` both rejected a Jotai atom for
  per-tenant/per-entity data; `useOrganizations`' atom exists because org
  state is genuinely shared across `AppSidebar`/`AppTopbar`/dashboard.
- No modal primitive exists in `components/ui/` (established by the prior
  cycle's DD4), and no date-formatting helper exists anywhere.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | `list_documents(*, organization: Organization) -> list[ProjectDocument]` = `[_to_project_document(row) for row in UmlDocument.objects.for_organization(organization).order_by("-updated_at")]`. Keyword-only, mirroring `create_document`/`get_document`/`list_memberships` | Return `QuerySet[UmlDocument]` like `list_memberships`, letting `api.py` map rows; a `.values("id", "revision", "updated_at", "data__metadata__name")` projection | Returning rows forces `api.py` to reach into `row.data["metadata"]["name"]`, breaking the services-is-sole-reassembler invariant and teaching the HTTP layer the persistence blob layout. The `.values()` projection hardcodes blob paths and bypasses `codec` entirely. Reusing `_to_project_document` keeps **one** row→domain decode path; decoding model/layout and discarding it costs microseconds at this project's scale and never reaches the wire (DD2) |
| DD2 | New `DocumentSummaryOut(Schema)` with `id: UUID`, `name: str`, `revision: int`, `updated_at: datetime` — types copied verbatim from `DocumentOut`, but `name` **flat**, not nested under `MetadataOut` | Reuse `DocumentOut`; nest `metadata: MetadataOut` for symmetry | `DocumentOut.model`/`.layout` are full `codec._encode_model`/`_encode_layout` dicts — every class, attribute, relationship and position serialized per row for data no row shows. Nesting would carry `description` (required on `MetadataOut`) that the list never renders; flat `name` matches `OrganizationOut`. Consequence, pinned for the frontend: `DocumentSummary.name` is flat while `UmlDocument.metadata.name` stays nested — the two are **not** interchangeable |
| DD3 | `@documents_router.get("", response=list[DocumentSummaryOut])` with `org_slug: Path[str]`, body `resolve_membership` → `services.list_documents` → `[_document_summary_out(d) for d in documents]`. **No `require_role`.** Registered above `create_document_view`, mirroring `list_organizations` before `create_organization` | `require_role(membership, Role.OWNER, Role.EDITOR)`, as create/commands do | The read gate is pinned to the endpoint it duplicates: `get_document_view` has no role check at all (verified, `api.py:50-54`), so a `VIEWER` who can open a document must also be able to see it listed. Adding a role check here would be an unrequested permission tightening. `resolve_membership` already 404s a non-member indistinguishably from an unknown slug, which is the tenant-isolation contract |
| DD4 | `listDocuments(orgSlug: string): Promise<DocumentSummary[]>` = `apiFetch<DocumentSummary[]>(base(orgSlug))`, no `try/catch`; `DocumentSummary = { id: string; name: string; revision: number; updated_at: string }` | A `try/catch` returning `[]` on failure | Copies the module's stated convention verbatim — no `try/catch` so `ApiError` (including the 404 from a stale slug) reaches the caller. Swallowing it would render "no tienes diagramas" for a permission failure. `id`/`updated_at` are `string` because UUID/datetime arrive JSON-serialized, exactly as in the existing `UmlDocument` type |
| DD5 | `useDocuments(orgSlug: string \| null)` uses **local `useState` + render-time tracked-slug reset**, cloned from `useMembers` — not a Jotai atom. Returns `{ documents, loading, error }` (read-only) | The proposal's suggestion: mirror `useOrganizations`' atom + mount-effect | The codebase's own reasoning points the other way. `useOrganizations`' atom exists because `AppSidebar` and the dashboard are **siblings** that must agree on the active org; a document list has exactly one consumer (the dashboard container), the same condition under which `state/document.ts` DD2 and `state/members.ts` DD2 both chose local state. A module atom would additionally paint org A's documents for a frame after switching to org B — the precise leak `useMembers`' render-time reset prevents. No mutators: `handleCreateDocument` navigates away on success, so there is nothing to append to |
| DD6 | `DocumentList({ documents }: { documents: DocumentSummary[] })` — presentational, no `"use client"` directive (like `OrgSwitcher`), `<ul aria-label="Diagramas">` of two-line rows. Each row is `<Link href={\`/documents/${doc.id}\`}>`. Zero documents renders a `<p>` empty state, **not** `null` | `onClick` + `router.push`, citing `handleCreateDocument`; returning `null` when empty, as `OrgSwitcher` does | `CreateDocumentForm`'s `router.push` is a post-mutation redirect to an id that does not exist until the POST resolves — it has no href to render ahead of time. A list row is a real destination, so it must be a real anchor: middle-click, open-in-new-tab, keyboard focus and prefetch all come free, and `AppSidebar` already establishes `next/link` as the navigation primitive. `OrgSwitcher`'s `null` is correct for a switcher with nothing to switch; here an empty list is a first-run state the user must see |
| DD7 | Row body mirrors `OrgSwitcher`'s two-line shape: `{doc.name}` over a muted `Revisión {doc.revision}`. **No date column** | Render `updated_at` via `toLocaleDateString` | No date-formatting helper exists in this codebase, and locale/timezone-dependent formatting in a client component is a hydration-mismatch and test-brittleness source for a field no success criterion requires. `updated_at` is still fetched and still orders the list server-side, so a date column is a one-line follow-up |
| DD8 | `dashboard/page.tsx`: `useDocuments(activeOrg?.slug ?? null)` and a `showCreateForm` `useState` are called **above** the existing `organizations.length === 0` early return. A new `<section>` after `CreateOrgForm` holds a header row (`<h2>Mis Diagramas</h2>` + a "Nuevo Diagrama" `Button`) that discloses the **unmodified** `CreateDocumentForm` beneath it, then `{loading ? "Cargando…" : <DocumentList …/>}`. `VerifyEmailBanner`, the org-empty-state branch, the org card, `CreateOrgForm` and `handleCreateDocument` are untouched | Lay `CreateDocumentForm` out horizontally inside the header row; open it in a modal; leave the form always visible below the heading with no header button | The header button must be a button, but `CreateDocumentForm` is a full labeled form — inlining it demands restyling an already-verified component and its tests. No modal primitive exists and introducing one for a single call site was already rejected in the prior cycle. Disclosure puts "Nuevo Diagrama" in the header exactly as the proposal requires while `CreateDocumentForm`'s props, markup and tests stay byte-identical. Hooks sit above the early return because React forbids conditional hooks; `orgSlug === null` keeps the hook idle, so the org-empty-state branch fires no request. Gating the empty state behind `loading` prevents "no tienes diagramas" flashing on every mount |

## Data Flow

    DashboardPage ──useDocuments(activeOrg?.slug ?? null)──→ listDocuments(orgSlug)
         │                                                          │
         │                                                   GET /api/orgs/{slug}/documents
         │                                                          ▼
         │                             resolve_membership (404 non-member, no require_role)
         │                                                          ▼
         │                    services.list_documents → .for_organization(org).order_by("-updated_at")
         │                                                          ▼
         │                       _to_project_document(row) ──→ _document_summary_out(...)
         │                                                          │  {id, name, revision, updated_at}
         ▼                                                          ▼
    {loading ? "Cargando…" : <DocumentList documents={…} />}  ←─────┘
         │                              │
         │ header: [Nuevo Diagrama] ────┴──→ rows: <Link href="/documents/{id}">
         │              ↓ (disclosure)                          │
         └──→ CreateDocumentForm ──→ handleCreateDocument ──────┴──→ /documents/{id}
              (unchanged: createDocument + router.push)

Org switch: `activeSlug` changes → `useDocuments`' render-time reset clears
`documents` **before** paint → effect refetches. No stale tenant frame.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/uml_documents/services.py` | Modify | `list_documents(*, organization)` (DD1) |
| `backend/apps/uml_documents/schemas.py` | Modify | `DocumentSummaryOut` (DD2) |
| `backend/apps/uml_documents/api.py` | Modify | `list_documents_view` + `_document_summary_out`; import `DocumentSummaryOut` (DD3) |
| `backend/apps/uml_documents/tests/` | Create/Modify | Service + endpoint suites (tenant, ordering, `VIEWER`) |
| `frontend/src/lib/uml_documents.ts` | Modify | `DocumentSummary` type + `listDocuments` (DD4) |
| `frontend/src/state/documents.ts` | Create | `useDocuments(orgSlug)` (DD5) |
| `frontend/src/components/workspace/DocumentList.tsx` | Create | Presentational list + empty state (DD6/DD7) |
| `frontend/src/app/(app)/dashboard/page.tsx` | Modify | "Mis Diagramas" section, disclosure, list (DD8) |
| `frontend/src/**/__tests__/*` | Create/Modify | Wrapper, hook, component, container suites |
| `docs/ai/DECISIONS_LOG.md`, `docs/ai/CURRENT_STATE.md` | Modify | `config.yaml` `rules.design` requires DD1–DD8 be logged there too |
| `backend/apps/uml_documents/models.py`, migrations | **None** | Zero diff — no schema change |

## Interfaces / Contracts

### `services.py` (DD1)

```python
def list_documents(*, organization: Organization) -> list[ProjectDocument]:
    """Newest-updated first — `UmlDocument.Meta` declares no `ordering`,
    so the order is stated here or it is undefined."""
    rows = UmlDocument.objects.for_organization(organization).order_by("-updated_at")
    return [_to_project_document(row) for row in rows]
```

### `schemas.py` (DD2) — types copied from `DocumentOut`

```python
class DocumentSummaryOut(Schema):
    id: UUID            # same as DocumentOut.id
    name: str           # FLAT — DocumentOut nests this under `metadata`
    revision: int
    updated_at: datetime
```

### `api.py` (DD3) — `Path[str]` is load-bearing

```python
def _document_summary_out(document) -> dict:
    return {
        "id": document.id,
        "name": document.metadata.name,
        "revision": document.revision,
        "updated_at": document.updated_at,
    }

@documents_router.get("", response=list[DocumentSummaryOut])
def list_documents_view(request: HttpRequest, org_slug: Path[str]):
    membership = resolve_membership(request, org_slug)   # no require_role — DD3
    documents = services.list_documents(organization=membership.organization)
    return [_document_summary_out(document) for document in documents]
```

### `state/documents.ts` (DD5) — the `useMembers` shape

```ts
export function useDocuments(orgSlug: string | null) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(orgSlug !== null);
  const [error, setError] = useState<string | null>(null);
  const [trackedSlug, setTrackedSlug] = useState(orgSlug);

  if (orgSlug !== trackedSlug) {          // render-time reset, not an effect
    setTrackedSlug(orgSlug);
    setDocuments([]);
    setError(null);
    setLoading(orgSlug !== null);
  }

  useEffect(() => {
    if (orgSlug === null) return;         // org-empty-state fires no request
    let cancelled = false;
    listDocuments(orgSlug)
      .then((fetched) => { if (!cancelled) setDocuments(fetched); })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [orgSlug]);

  return { documents, loading, error };
}
```

### `DocumentList.tsx` (DD6) — empty branch returns copy, not `null`

```tsx
type DocumentListProps = { documents: DocumentSummary[] };

if (documents.length === 0) {
  return <p className="text-sm text-muted-foreground">Todavía no tienes diagramas. Crea el primero con «Nuevo Diagrama».</p>;
}
// else: <ul aria-label="Diagramas"> … <li key={doc.id}><Link href={`/documents/${doc.id}`}> …
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit — `services.list_documents` | Returns only the passed org's rows; `-updated_at` order asserted with three rows written out of order; empty org → `[]`; queries through `.for_organization` (no `TenantScopeViolation`) | pytest + pytest-django, existing `uml_documents` fixtures |
| Integration — `GET /orgs/{slug}/documents` | 200 for `VIEWER` **and** `OWNER`/`EDITOR` (DD3); org B's request never sees org A's documents; non-member gets 404, not 403; response items carry exactly `id`/`name`/`revision`/`updated_at` and **no** `model`/`layout` (DD2); `Path[str]` regression — the route resolves at all | pytest client, mirroring the `get_document_view` suite |
| Unit — `lib/uml_documents.ts` | `listDocuments("a b")` calls `/api/orgs/a%20b/documents` with no method override; a rejected `apiFetch` propagates `ApiError` verbatim | `vi.mock("@/lib/api")`, extending the existing suite |
| Unit — `useDocuments` | Idle (no fetch, `loading === false`) when `orgSlug` is `null`; fetches on mount; changing `orgSlug` clears `documents` in the same render as the refetch; a rejection sets `error` and leaves `documents` empty | `renderHook` + `rerender`, mirroring `useMembers`' suite |
| Component — `DocumentList` | One `<li>` per document with an `<a href="/documents/{id}">` (queried by role `link`, asserting `href` — proves DD6's anchor, which an `onClick` row would fail); empty array renders the empty-state copy, not an empty `<ul>`; row shows name and `Revisión N` | RTL |
| Container — `dashboard/page.tsx` | "Mis Diagramas" heading + "Nuevo Diagrama" button render when `activeOrg` exists; clicking it reveals `CreateDocumentForm`; `DocumentList` receives the hook's documents; `loading` shows the placeholder instead of the empty state; the zero-org branch still renders `OrgEmptyState` + `CreateOrgForm` and calls **no** document request | RTL with `useDocuments`/`useOrganizations` mocked, extending the existing dashboard suite |
| E2E | Deferred — no Cypress harness (`config.yaml` `testing.e2e`) | — |

## Threat Matrix

N/A — no routing decisions from untrusted input, shell, subprocess, VCS/PR
automation, executable-file classification, or process integration. Row
hrefs are built from UUIDs returned by the tenant-scoped endpoint itself,
and `orgSlug` passes through the existing `encodeURIComponent` in `base()`.

## Migration / Rollout

No migration, no feature flag, no data change. `config.yaml`'s sequence-diagram
rule does not apply — no Channels/realtime flow is touched. Rollback: delete
the two new frontend files plus `DocumentList`, restore `dashboard/page.tsx`,
and leave the additive endpoint unused and harmless.

## Open Questions

- [ ] DD7 drops the date column. If the spec author reads "newest first" as a
      requirement the user must *see*, a locale-safe formatter is needed first —
      is that this cycle or a follow-up?
- [ ] DD1 decodes `model`/`layout` per row and discards them. Acceptable at exam
      scale; if an org ever holds hundreds of documents the escape hatch is a
      `codec`-aware partial decode, recorded as tech debt.
