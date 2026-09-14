# Exploration: UML document list (see-and-reopen existing documents)

## Current State

- **Backend has create + get-one, no list.** `backend/apps/uml_documents/api.py` defines `POST ""` (`create_document_view`, requires `Role.OWNER`/`EDITOR`) and `GET "/{doc_id}"` (`get_document_view`) — no `GET ""`. `get_document_view` calls only `resolve_membership`, with **no `require_role` call at all** — so any member (`OWNER`, `EDITOR`, or `VIEWER`) can read a document. A list endpoint should mirror this exact read-only gate, not the OWNER/EDITOR gate used by create/commands.
- **Tenant scoping**: `UmlDocument.objects.for_organization(org)` via `TenantScopedManager` (`backend/apps/organizations/models.py`), the same manager reused by `Membership`. Its default (unscoped) manager raises `TenantScopeViolation`; every real query must go through `.for_organization(...)`.
- **No pagination precedent anywhere in this codebase.** `list_organizations` and `list_members` (`backend/apps/organizations/api.py`) both return a plain `response=list[X]` with no `Paginate`/limit-offset — an unpaginated list is the established convention, appropriate at this exam project's scale.
- **No default ordering** on `UmlDocument.Meta` — only `models.Index(fields=["organization", "owner_id"])`. Ordering (e.g. most-recently-updated first) must be applied explicitly in the service query, e.g. `.order_by("-updated_at")`.
- **`DocumentOut` is heavy for a list item**: `model` and `layout` are full nested dicts from `codec._encode_model`/`_encode_layout`. A list item only needs `id`, `metadata.name`, `revision`, `updated_at` — serializing full model/layout per row would be wasteful.
- **Frontend has zero list UI.** `frontend/src/lib/uml_documents.ts` exports only `createDocument`, `getDocument`, `submitCommand` (thin `apiFetch` wrappers, no try/catch so `ApiError` propagates verbatim). `frontend/src/app/(app)/dashboard/page.tsx` renders org info + `CreateDocumentForm` only; on create it immediately does `router.push('/documents/{id}')` — there is no page showing multiple documents.
- **`AppSidebar.tsx`** already has a "Diagramas" nav link pointing at `/dashboard` — this is the natural home for a document list, avoiding a second nav destination for the same domain.
- **Existing list-UI convention to mirror**: `OrgSwitcher.tsx` is presentational (receives an array as a prop, renders a `<ul>`), and `useOrganizations()` (`frontend/src/state/organizations.ts`) is the container hook — a Jotai atom populated by a mount `useEffect` calling the list API. A `useDocuments(orgSlug)` hook following that exact shape is the natural fit for a document list.
- **No document-level delete exists anywhere.** `schemas.py`'s `CommandIn` discriminated union has only element-level `Add*`/`Remove*`/`RenameClass` commands, all operating inside an existing document. Deleting a whole document would require new backend scope (model, service, API route, error handling) not present today.

## Affected Areas

- `backend/apps/uml_documents/api.py` — add `GET ""` list view, mirroring `create_document_view`/`get_document_view`'s `resolve_membership -> service -> serialize` shape; no role check (matches `get_document_view`).
- `backend/apps/uml_documents/services.py` — add `list_documents(*, organization)` returning `UmlDocument.objects.for_organization(org).order_by("-updated_at")`.
- `backend/apps/uml_documents/schemas.py` — add a lightweight `DocumentSummaryOut` schema (`id`, `name`, `revision`, `updated_at`) distinct from the heavy `DocumentOut`.
- `frontend/src/lib/uml_documents.ts` — add `listDocuments(orgSlug)` wrapper + a `DocumentSummary` type.
- New `frontend/src/state/documents.ts` (or similar) — container hook mirroring `useOrganizations()`'s atom + mount-effect pattern.
- `frontend/src/app/(app)/dashboard/page.tsx` — extend to render the document list alongside (or above/below) the existing `CreateDocumentForm`.
- New presentational list component, mirroring `OrgSwitcher.tsx`'s prop-in convention, each item linking to `/documents/{id}`.
- No changes needed to `AppSidebar.tsx` — "Diagramas" already points at `/dashboard`.

## Approaches

1. **Extend `/dashboard` in place** — add the document list to the existing dashboard page, alongside org info and `CreateDocumentForm`.
   - Pros: matches existing information architecture (sidebar's "Diagramas" link already targets `/dashboard`); no new route, no new nav entry; reuses the page's existing `activeOrg`/org-empty-state branching.
   - Cons: dashboard page grows in responsibility (org info + create form + list).
   - Effort: Low.

2. **New dedicated `/documents` route** for the list, leaving `/dashboard` as an org-summary landing page.
   - Pros: clean separation of concerns per page.
   - Cons: contradicts the just-added "Diagramas" sidebar link (which points at `/dashboard`, not `/documents`) — would require either changing that link or adding a redirect/duplicate entry; adds a route for no material benefit at this scope.
   - Effort: Low-Medium.

## Recommendation

Approach 1 — extend `/dashboard` in place. The sidebar's "Diagramas" link already points there, so this is the path of least surprise and requires no navigation rework. Fetch documents via a new `useDocuments(orgSlug)` hook (mirroring `useOrganizations()`), render a presentational list component (mirroring `OrgSwitcher.tsx`) with an empty-state message when zero documents exist, and keep `CreateDocumentForm` visible regardless of list state so "Nuevo Diagrama" stays reachable.

## Risks

- No pagination anywhere in the codebase to lean on; if a future org accumulates many documents, an unpaginated list will need revisiting — acceptable for this exam-project cycle, not a blocker now.
- Document-level delete has no backend support at all (only element-level Remove* commands exist inside a document) — must be explicitly scoped out unless the user asks for it, since it implies new model/service/API/error-handling work well beyond a list view.
- `get_document_view`'s read gate has no role check; a list endpoint that diverges from that (e.g. by requiring OWNER/EDITOR) would be an inconsistent, unrequested permission tightening — must mirror the existing gate exactly.

## Scope Decisions (confirmed by user)

1. Location: **`/dashboard`** — extends the existing page; no new route, no sidebar change.
2. Document-level delete: **out of scope**. No backend command exists for it today; adding one is new scope, not part of this cycle.
3. Search/filter: not needed at this exam-project scale — a plain unpaginated list is sufficient (no real tradeoff, decided directly per the exploration's own recommendation).
4. "Nuevo Diagrama" placement: moves to a header button next to a "Mis Diagramas" heading, above the list, now that a list exists to anchor it against (no real tradeoff, decided directly).

## Ready for Proposal

Yes — all open questions resolved above.
