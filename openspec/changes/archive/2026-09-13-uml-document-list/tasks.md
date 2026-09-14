# Tasks: UML Document List

Strict TDD. Additive on both sides — no model/migration/command-bus change.

Test command: `cd backend && python -m pytest apps/uml_documents/tests/test_services.py apps/uml_documents/tests/test_schemas.py apps/uml_documents/tests/test_api.py && cd ../frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/state/__tests__/documents.test.ts src/components/workspace/__tests__/DocumentList.test.tsx "src/app/(app)/dashboard/__tests__/page.test.tsx"`
Full regression: `cd backend && python -m pytest && cd ../frontend && npm test`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~450-550 (backend 3 files ~40 + tests ~120; frontend 2 new files ~90 + 2 modified ~60 + 4 test suites/mods ~180; docs ~40) |
| 800-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR — estimate fits comfortably under the 800-line budget |
| Delivery strategy | single-pr |
| Chain strategy | pending (not needed) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
800-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Document list end to end (backend list endpoint + frontend fetch/hook/UI) | PR 1 | see Test command above | `cd backend && python manage.py runserver` + `cd frontend && npm run dev` — manual: log in, view `/dashboard` with 0 then 2+ documents, click a row, switch orgs | `git revert`, or delete `state/documents.ts` + `DocumentList.tsx` + their tests, revert `lib/uml_documents.ts`/`dashboard/page.tsx`, and revert the 3 backend files — endpoint is purely additive (proposal §Rollback Plan) |

## Phase 1: Backend — `list_documents` Service (DD1)

- [x] 1.1 RED: extend `backend/apps/uml_documents/tests/test_services.py` — `list_documents(organization=org)` returns only that org's rows; three rows written out of order assert `-updated_at` order; empty org returns `[]`; query path never raises `TenantScopeViolation` [Document List — all scenarios].
- [x] 1.2 GREEN: modify `backend/apps/uml_documents/services.py` — add `list_documents(*, organization: Organization) -> list[ProjectDocument]` = `[_to_project_document(row) for row in UmlDocument.objects.for_organization(organization).order_by("-updated_at")]` (DD1).

## Phase 2: Backend — `DocumentSummaryOut` Schema (DD2)

- [x] 2.1 RED: extend `backend/apps/uml_documents/tests/test_schemas.py` — `DocumentSummaryOut` accepts `id`/`name`/`revision`/`updated_at` and serializes `name` flat (not nested under a metadata object).
- [x] 2.2 GREEN: modify `backend/apps/uml_documents/schemas.py` — add `DocumentSummaryOut(Schema)` with `id: UUID`, `name: str`, `revision: int`, `updated_at: datetime` (DD2).

## Phase 3: Backend — List Endpoint (DD3)

- [x] 3.1 RED: extend `backend/apps/uml_documents/tests/test_api.py` — `GET /orgs/{org_slug}/documents` returns 200 with both `id`/`name`/`revision`/`updated_at` and no `model`/`layout` keys for `VIEWER` and `OWNER`/`EDITOR`; org B never sees org A's documents; non-member gets 404; response order is newest-updated-first [Viewer lists documents for their organization; Owner and Editor can also list; Cross-tenant documents are absent, not 404; Empty organization returns an empty list].
- [x] 3.2 GREEN: modify `backend/apps/uml_documents/api.py` — add `_document_summary_out(document)` mapper and `list_documents_view` on `@documents_router.get("", response=list[DocumentSummaryOut])` with `org_slug: Path[str]`, calling `resolve_membership` (no `require_role`) then `services.list_documents`; import `DocumentSummaryOut`; register above `create_document_view` (DD3).

## Phase 4: Frontend — `listDocuments` + `DocumentSummary` (DD4)

- [x] 4.1 RED: extend `frontend/src/lib/__tests__/uml_documents.test.ts` — `listDocuments("a b")` calls `GET /api/orgs/a%20b/documents` via `apiFetch`, no method override; a rejected `apiFetch` propagates `ApiError` verbatim (no `try/catch`).
- [x] 4.2 GREEN: modify `frontend/src/lib/uml_documents.ts` — add `DocumentSummary = { id: string; name: string; revision: number; updated_at: string }` type and `listDocuments(orgSlug: string): Promise<DocumentSummary[]>` = `apiFetch<DocumentSummary[]>(base(orgSlug))` (DD4).

## Phase 5: Frontend — `useDocuments` Hook (DD5)

- [x] 5.1 RED: create `frontend/src/state/__tests__/documents.test.ts` — idle with `loading === false` and no fetch when `orgSlug` is `null`; fetches on mount when `orgSlug` is set; changing `orgSlug` clears `documents` in the same render as the refetch (render-time reset, not a post-paint flash); a rejection sets `error` and leaves `documents` empty [Switching organizations shows that organization's documents].
- [x] 5.2 GREEN: create `frontend/src/state/documents.ts` — `useDocuments(orgSlug: string | null)` with local `useState` + render-time tracked-slug reset, cloned from `useMembers`'s shape; returns `{ documents, loading, error }` (DD5).

## Phase 6: Frontend — `DocumentList` Component (DD6/DD7)

- [x] 6.1 RED: create `frontend/src/components/workspace/__tests__/DocumentList.test.tsx` — one `<li>` per document with a link (role `link`) whose `href` is `/documents/{id}`; empty array renders the empty-state copy, not an empty `<ul>`; each row shows `{doc.name}` and `Revisión {doc.revision}` [Documents render as navigable rows; Zero documents renders an empty state].
- [x] 6.2 GREEN: create `frontend/src/components/workspace/DocumentList.tsx` — presentational, no `"use client"`; `<ul aria-label="Diagramas">` of `<li><Link href={\`/documents/${doc.id}\`}>` rows showing name + `Revisión N`; zero documents returns a `<p>` empty-state message (DD6/DD7).

## Phase 7: Frontend — Dashboard Wiring (DD8)

- [x] 7.1 RED: extend `frontend/src/app/(app)/dashboard/__tests__/page.test.tsx` — "Mis Diagramas" heading and "Nuevo Diagrama" button render together in a header row when `activeOrg` exists; clicking the button reveals `CreateDocumentForm`; `DocumentList` receives the hook's `documents`; `loading` shows a placeholder instead of the empty state; the zero-org branch still renders `OrgEmptyState` + `CreateOrgForm` and triggers no document request [Entry point hidden without an active organization; Creating a document navigates to its page; Entry point renders in the header, above the list].
- [x] 7.2 GREEN: modify `frontend/src/app/(app)/dashboard/page.tsx` — call `useDocuments(activeOrg?.slug ?? null)` and add `showCreateForm` state above the existing `organizations.length === 0` early return; add a `<section>` after `CreateOrgForm` with a header row (`<h2>Mis Diagramas</h2>` + "Nuevo Diagrama" `Button` disclosing `CreateDocumentForm`), then `{loading ? "Cargando…" : <DocumentList documents={documents} />}` (DD8).

## Phase 8: Documentation (`config.yaml` `rules.design`)

- [x] 8.1 Append DD1-DD8 to `docs/ai/DECISIONS_LOG.md`, one entry per decision with rationale, following the existing entry format.
- [x] 8.2 Update `docs/ai/CURRENT_STATE.md` — note `/dashboard` now lists an organization's documents with an empty state, and the "Nuevo Diagrama" entry point moved into the list's header row.

## Phase 9: Verification

- [x] 9.1 Run `cd backend && python -m pytest`; confirm zero regressions and the 4 new Document List scenarios pass. — 319/319 passed.
- [x] 9.2 Run `cd frontend && npm test`; confirm zero regressions and all Dashboard Document List + modified Create-Document Entry Point scenarios pass. — 251/251 passed.
- [x] 9.3 Run `cd frontend && npm run lint` and `cd backend && ruff check .` (or project's configured linter); confirm zero new warnings. — frontend lint clean; backend has no configured linter (`config.yaml`: "backend_linter: none detected"), consistent with the pre-existing project state.
- [x] 9.4 Confirm `backend/apps/uml_documents/models.py` and migrations have zero diff: `git diff --stat -- backend/apps/uml_documents/models.py backend/apps/uml_documents/migrations` returns empty. — confirmed empty.
