# Proposal: UML Document List

## Intent

A created document is reachable only through the redirect that follows its
creation: the backend has create and get-one but no list, and `/dashboard`
renders org info plus `CreateDocumentForm` and nothing else. Navigate away and
the only way back to a diagram is a remembered URL. The sidebar's "Diagramas"
link already points at `/dashboard`, so the destination exists — the inventory
behind it does not.

## Scope

### In Scope

- `GET /orgs/{org_slug}/documents` — `list_documents(*, organization)` over
  `UmlDocument.objects.for_organization(org).order_by("-updated_at")`, gated
  exactly like `get_document_view` (`resolve_membership`, no `require_role`),
  returning a lightweight `DocumentSummaryOut` (`id`, `name`, `revision`,
  `updated_at`).
- `listDocuments(orgSlug)` + `DocumentSummary` type in `lib/uml_documents.ts`.
- `useDocuments(orgSlug)` hook mirroring `useOrganizations()`'s atom +
  mount-effect shape.
- A presentational list component (prop-in array, like `OrgSwitcher.tsx`), rows
  linking to `/documents/{id}`, plus a zero-documents empty state.
- `dashboard/page.tsx` restructured: a "Mis Diagramas" heading with
  "Nuevo Diagrama" moved into that header row, above the list.

### Out of Scope

- Document-level delete — `CommandIn` carries only element-level commands, so
  this is new model/service/API scope, not a list view.
- Pagination, search, filtering — no pagination precedent exists
  (`list_organizations`, `list_members` are both plain lists).
- Rename, duplicate, share; any `AppSidebar.tsx` change or `/documents` route.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `uml-document-persistence`: adds list to its HTTP surface (currently
  "create, read, submit-command") under the tenant gate it already mandates.
- `web-uml-canvas`: adds the dashboard list and empty state, and modifies its
  existing "Create-Document Entry Point" requirement, whose button relocates.

A separate dashboard capability was rejected: `web-uml-canvas` already owns
dashboard-located UML behavior, so a new one would split one screen across two
specs and orphan the relocated button.

## Approach

Backend mirrors the existing three-file shape verbatim — `api.py` view →
`services.py` query → `schemas.py` out-schema. `DocumentSummaryOut` is new
rather than reusing `DocumentOut`, whose `model`/`layout` nested dicts would
be serialized per row for data no list item shows.

Frontend reuses the container/presentational split: state in `useDocuments`,
rendering in a prop-in component, wiring in `dashboard/page.tsx`. Ordering is
server-side; the client does not sort.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/uml_documents/api.py` | Modified | `GET ""` list view |
| `backend/apps/uml_documents/services.py` | Modified | `list_documents` |
| `backend/apps/uml_documents/schemas.py` | Modified | `DocumentSummaryOut` |
| `frontend/src/lib/uml_documents.ts` | Modified | `listDocuments` + type |
| `frontend/src/state/documents.ts` | New | `useDocuments(orgSlug)` |
| `frontend/src/components/workspace/DocumentList.tsx` | New | Presentational list |
| `frontend/src/app/(app)/dashboard/page.tsx` | Modified | Header, list, moved button |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| List tightens the read gate by adding `require_role` | Med | Flag for sdd-spec: pin to `get_document_view`'s gate — any member reads |
| No `Meta.ordering` on `UmlDocument`, so order is undefined | Med | Explicit `.order_by("-updated_at")`, asserted in tests |
| Unscoped manager raises `TenantScopeViolation` | Low | Service queries via `.for_organization(org)` |
| Stale list after creating elsewhere | Low | Flag for sdd-design: refetch on mount, like `useOrganizations()` |

## Rollback Plan

Backend is purely additive (no existing signature changes). Revert via
`git revert`, or delete the three new frontend files and restore
`dashboard/page.tsx`'s previous body, leaving the endpoint unused and harmless.

## Dependencies

None new.

## Success Criteria

- [ ] `GET /orgs/{slug}/documents` returns that org's documents newest-updated
      first, for a `VIEWER` as well as `OWNER`/`EDITOR`.
- [ ] Organization B never sees organization A's documents.
- [ ] `/dashboard` lists every document of the active org; each row opens
      `/documents/{id}`.
- [ ] Zero documents renders an empty state, not a blank region.
- [ ] "Nuevo Diagrama" sits in the "Mis Diagramas" header and still creates and
      navigates as before.
- [ ] pytest covers the list service and endpoint (cross-tenant and `VIEWER`
      cases); Vitest + RTL cover the list component and empty state.
