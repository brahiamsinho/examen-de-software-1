# Archive Report: UML Document List

**Change Name**: uml-document-list
**Archived**: 2026-09-13
**Archive Location**: `openspec/changes/archive/2026-09-13-uml-document-list/`
**Artifact Store Mode**: hybrid (OpenSpec + Engram)
**SDD Cycle Status**: CLOSED ✅

## Executive Summary

The `uml-document-list` change has been fully planned, implemented, verified, and archived. The backend now exposes `GET /orgs/{org_slug}/documents` to list an organization's UML documents newest-updated-first, and the frontend dashboard now displays the list via a new `useDocuments` hook and `DocumentList` component, with an empty state for zero documents. All 20 tasks are complete, 573 tests pass (319 backend + 254 frontend, including 3 new regression tests), lint is clean, model/migrations diff is empty, and all 10 spec scenarios are fully COMPLIANT. Verdict: **PASS** (0 CRITICAL, 0 WARNING).

## Verification Verdict

- **Verdict**: PASS
- **Critical Findings**: 0
- **Warnings**: 0 (both prior WARNINGs fixed in this cycle)
- **Requirements Compliant**: 3/3
- **Scenarios Compliant**: 10/10
- **Test Results**: 573 passed (319 backend + 254 frontend, including 3 new regression tests)
- **Build Status**: SUCCESS (docker compose build + next build)
- **Lint Status**: Clean (frontend: zero warnings; backend: no configured linter per project state)
- **Models/Migrations Diff**: Empty (confirmed `git diff --stat -- backend/apps/uml_documents/models.py backend/apps/uml_documents/migrations`)

Per `verify-report.md` (observation-id not persisted in openspec mode), verification was re-run fresh in the final cycle after both prior WARNINGs were fixed in implementation tasks:
1. **WARNING 1 (VIEWER saw Nuevo Diagrama despite 403)**: Fixed by computing `canCreateDocument = activeOrg?.my_role === OWNER || activeOrg?.my_role === EDITOR` and gating the button render behind it (line 74-78, `dashboard/page.tsx`). Two new runtime tests independently prove both directions.
2. **WARNING 2 (untested DOM-order assertion)**: Fixed by adding a new test (`places the Mis Diagramas header above the document list in DOM order`) that reads `container.innerHTML` and asserts heading index precedes list-item index — a genuine runtime DOM-order assertion.

Both fixes verified against the actual current file contents in this session, not trusted from task description alone.

## Specs Merged into Main Specs

### uml-document-persistence Spec

**File**: `openspec/specs/uml-document-persistence/spec.md`
**Action**: Delta spec merged (ADDED requirement)
**Changes**:
- ADDED: Requirement "Document List" (4 scenarios)
  - Scenario: Viewer lists documents for their organization
  - Scenario: Owner and Editor can also list
  - Scenario: Cross-tenant documents are absent, not 404
  - Scenario: Empty organization returns an empty list

**Merge Method**: `gentle-ai sdd-archive-compose` (native composition, requirement name matching)

### web-uml-canvas Spec

**File**: `openspec/specs/web-uml-canvas/spec.md`
**Action**: Delta spec merged (ADDED + MODIFIED requirements)
**Changes**:
- ADDED: Requirement "Dashboard Document List" (3 scenarios)
  - Scenario: Documents render as navigable rows
  - Scenario: Zero documents renders an empty state
  - Scenario: Switching organizations shows that organization's documents
- MODIFIED: Requirement "Create-Document Entry Point" (3 scenarios)
  - Updated to reflect button now in header row above list
  - Scenario: Entry point hidden without an active organization
  - Scenario: Creating a document navigates to its page
  - Scenario: Entry point renders in the header, above the list

**Merge Method**: `gentle-ai sdd-archive-compose` (native composition, requirement name matching)

## Archive Contents

The change folder has been moved from `openspec/changes/uml-document-list/` to `openspec/changes/archive/2026-09-13-uml-document-list/` and contains:

- ✅ **proposal.md** — Scope, capabilities, approach, risks, rollback plan
- ✅ **design.md** — 8 architecture decisions (DD1–DD8), interfaces, contracts, data flow, file changes
- ✅ **tasks.md** — 20 implementation tasks across 9 phases (all marked complete: 20/20)
- ✅ **verify-report.md** — Verification report showing PASS verdict, all scenarios COMPLIANT, both prior WARNINGs fixed
- ✅ **specs/**
  - `uml-document-persistence/spec.md` (delta spec for "Document List" requirement)
  - `web-uml-canvas/spec.md` (delta spec for "Dashboard Document List" + modified "Create-Document Entry Point")
- ✅ **exploration.md** — Original exploration findings

## Task Completion Status

All 20 implementation tasks are marked complete in `tasks.md` and independently re-confirmed against actual current source files (not trusted from checkbox state alone):

| Phase | Task Count | Completion |
|-------|-----------|------------|
| Phase 1: Backend `list_documents` Service | 2 | 2/2 ✅ |
| Phase 2: Backend `DocumentSummaryOut` Schema | 2 | 2/2 ✅ |
| Phase 3: Backend List Endpoint | 2 | 2/2 ✅ |
| Phase 4: Frontend `listDocuments` + `DocumentSummary` | 2 | 2/2 ✅ |
| Phase 5: Frontend `useDocuments` Hook | 2 | 2/2 ✅ |
| Phase 6: Frontend `DocumentList` Component | 2 | 2/2 ✅ |
| Phase 7: Frontend Dashboard Wiring | 2 | 2/2 ✅ |
| Phase 8: Documentation | 2 | 2/2 ✅ |
| Phase 9: Verification | 4 | 4/4 ✅ |
| **Total** | **20** | **20/20 ✅** |

## Architecture Decisions

Eight decisions were made and logged to `docs/ai/DECISIONS_LOG.md`:

1. **DD1**: `list_documents(*, organization)` returns full `ProjectDocument` list (not raw QuerySet), decoded and returned as `[_to_project_document(row) for row in UmlDocument.objects.for_organization(organization).order_by("-updated_at")]` — preserves services-as-sole-reassembler invariant
2. **DD2**: New `DocumentSummaryOut(Schema)` with flat `name` field (not nested), mirroring `OrganizationOut`, omitting `model`/`layout` to avoid serializing unused data per row
3. **DD3**: `@documents_router.get("", response=list[DocumentSummaryOut])` gated via `resolve_membership` **only** (no `require_role`), matching the read gate of the existing `get_document_view`
4. **DD4**: `listDocuments(orgSlug)` in `lib/uml_documents.ts` uses `apiFetch` with no `try/catch`, letting `ApiError` (including stale-slug 404s) propagate to caller
5. **DD5**: `useDocuments(orgSlug)` uses **local `useState` + render-time tracked-slug reset** (not a Jotai atom), mirroring `useMembers`, preventing stale-tenant render frames
6. **DD6**: `DocumentList` presentational component uses `<Link>` (not `onClick` + `router.push`), enabling middle-click and open-in-new-tab, aligned with `next/link` navigation precedent
7. **DD7**: Row body shows `{doc.name}` over `Revisión {doc.revision}` (no date column), avoiding formatter helper and hydration mismatch, with server-side ordering already capturing `updated_at` intent
8. **DD8**: `dashboard/page.tsx` calls hooks above the `organizations.length === 0` early return, adds header section with "Mis Diagramas" + "Nuevo Diagrama" button (disclosure), then list; `CreateDocumentForm` unchanged

All 8 decisions follow the existing architecture and codebase conventions. No modal primitive was introduced (rejected in prior cycle). Container/presentational split preserved. Additive only — no model, migration, or command-bus changes.

## Spec Compliance Matrix

### uml-document-persistence — Requirement: Document List

| Scenario | Test | Result |
|---|---|---|
| Viewer lists documents for their organization | `test_api.py::TestListDocuments::test_viewer_lists_documents_for_their_organization` | COMPLIANT |
| Owner and Editor can also list | `test_api.py::TestListDocuments::test_owner_and_editor_can_also_list` | COMPLIANT |
| Cross-tenant documents are absent, not 404 | `test_api.py::TestListDocuments::test_cross_tenant_documents_are_absent_not_404` | COMPLIANT |
| Empty organization returns an empty list | `test_api.py::TestListDocuments::test_empty_organization_returns_empty_list` | COMPLIANT |

### web-uml-canvas — Requirement: Dashboard Document List

| Scenario | Test | Result |
|---|---|---|
| Documents render as navigable rows | `DocumentList.test.tsx` (one `<li>` per document with link to `/documents/{id}`) + `page.test.tsx` (passes hook documents to `DocumentList`) | COMPLIANT |
| Zero documents renders an empty state | `DocumentList.test.tsx` (renders empty-state `<p>`, not empty `<ul>`) | COMPLIANT |
| Switching organizations shows that organization's documents | `documents.test.ts` (clears documents in same render as refetch when `orgSlug` changes) | COMPLIANT |

### web-uml-canvas — Requirement: Create-Document Entry Point (MODIFIED)

| Scenario | Test | Result |
|---|---|---|
| Entry point hidden without an active organization | `page.test.tsx` (hides "Nuevo Diagrama" with no active organization) | COMPLIANT |
| Creating a document navigates to its page | `page.test.tsx` (creating document calls `createDocument` and navigates to page) | COMPLIANT |
| Entry point renders in the header, above the list | `page.test.tsx` (renders "Mis Diagramas" and "Nuevo Diagrama" in header AND new DOM-order test asserts heading index precedes list-item index in `container.innerHTML`) | COMPLIANT |

**Summary**: 10/10 scenarios fully COMPLIANT. Up from 9/10 + 1 PARTIAL in prior cycle after both WARNINGs were fixed.

## Implementation Summary

### Backend Changes

**Three files modified, additive**:
1. `backend/apps/uml_documents/services.py` — Added `list_documents(*, organization: Organization) -> list[ProjectDocument]`
2. `backend/apps/uml_documents/schemas.py` — Added `DocumentSummaryOut(Schema)` with `id`, `name`, `revision`, `updated_at`
3. `backend/apps/uml_documents/api.py` — Added `list_documents_view` and `_document_summary_out` mapper; registered at `@documents_router.get("")` with path parameter `org_slug: Path[str]`

**Zero diff**:
- Models: No changes
- Migrations: No new migrations
- Command Bus: No changes (all three remove command shapes already exist)

**Backend Tests**: 319 tests pass (unchanged from prior cycle; all new scenarios covered by existing test infrastructure, no isolated new test file)

### Frontend Changes

**Two files created, two modified, additive**:
1. `frontend/src/state/documents.ts` — NEW — `useDocuments(orgSlug: string | null)` with local state, mount effect, render-time slug tracking
2. `frontend/src/components/workspace/DocumentList.tsx` — NEW — Presentational list component, `<ul aria-label="Diagramas">` of rows linking to `/documents/{id}`
3. `frontend/src/lib/uml_documents.ts` — MODIFIED — Added `DocumentSummary` type and `listDocuments(orgSlug)` function
4. `frontend/src/app/(app)/dashboard/page.tsx` — MODIFIED — Calls `useDocuments`, adds header section with "Mis Diagramas" + "Nuevo Diagrama" button (disclosure), then conditional list or loading state

**Frontend Tests**: 254 tests pass
- **New regression tests** (this cycle): 3
  - `page.test.tsx` (line 251–268): Hides Nuevo Diagrama for a VIEWER (button absent, heading still present)
  - `page.test.tsx` (line 251–268): Shows Nuevo Diagrama for an EDITOR, not just OWNER (guards against narrower fix)
  - `page.test.tsx` (line 188–206): Asserts DOM-order with `container.innerHTML.indexOf` (heading index > -1, list index > heading index)
- **Prior tests unchanged**: 251 (no regressions)

### Documentation Updates

1. `docs/ai/DECISIONS_LOG.md` — Appended DD1–DD8 with rationale
2. `docs/ai/CURRENT_STATE.md` — Updated to reflect `/dashboard` now lists organization documents with empty state; "Nuevo Diagrama" button moved into header row

## Handoff

**What's ready for the next change**:
- Both capability specs (`uml-document-persistence`, `web-uml-canvas`) are now up-to-date in `openspec/specs/`
- Backend endpoint and service fully implemented, tested, and verified
- Frontend hook and component layers ready for further list enhancements (e.g., pagination, search, inline actions)
- Role gate verified: any member (VIEWER+) can read the list, matching existing document-read permission model

**Known limitations** (unchanged from proposal, marked as Out of Scope):
- No document-level delete (requires CommandIn + model/service/API scope)
- No pagination, search, or filtering (no precedent in existing list endpoints)
- No rename, duplicate, share, or AppSidebar changes

**Suggestions** (from `verify-report.md`):
1. "Revisión N" placeholder for newly created documents (unchanged, explicit tradeoff per design.md DD7)
2. Reconcile Review Workload Forecast table (800-line budget citation) with shared SDD guard default (400 changed lines) — out of scope for this verify pass

## Source of Truth Updated

The following canonical specs now reflect the new behavior:

| Spec File | New Requirements | Modified Requirements |
|-----------|------------------|----------------------|
| `openspec/specs/uml-document-persistence/spec.md` | 1 (Document List) | — |
| `openspec/specs/web-uml-canvas/spec.md` | 1 (Dashboard Document List) | 1 (Create-Document Entry Point) |

Both files have been mechanically composed via `gentle-ai sdd-archive-compose` to preserve all existing requirements byte-for-byte while incorporating the new ones from the delta specs.

## Closure Checklist

- ✅ **Spec Sync**: Both delta specs merged into main specs via native `gentle-ai sdd-archive-compose`
- ✅ **Archive Move**: Change folder moved from active to `openspec/changes/archive/2026-09-13-uml-document-list/`
- ✅ **Active Directory Cleaned**: `openspec/changes/uml-document-list/` no longer exists
- ✅ **Task Completion**: All 20 tasks marked complete and independently re-confirmed
- ✅ **Build & Tests**: docker compose build + next build + full test suite (573/573 pass)
- ✅ **Verification**: PASS verdict, all 10 scenarios COMPLIANT, 0 CRITICAL, 0 WARNING
- ✅ **Handoff Updated**: `docs/ai/HANDOFF_LATEST.md` updated with new cycle entry

## SDD Cycle Complete

The `uml-document-list` change has been fully planned (proposal), designed (8 decisions), implemented (20 tasks, strict TDD, 2 new files + 3 modified files, additive only), verified (573 tests pass, all scenarios COMPLIANT, both prior WARNINGs fixed), and archived. Ready for the next change.

---

**Archive Report Generated**: 2026-09-13
**Artifact Store**: hybrid (filesystem + Engram)
**Next Recommended**: None — cycle complete, ready for next proposal/change
