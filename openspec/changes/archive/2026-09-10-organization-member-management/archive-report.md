# Archive Report: Organization Member Management UI

**Change**: organization-member-management
**Date archived**: 2026-09-10
**Artifact store mode**: hybrid (openspec + Engram)

## Completeness & Final State

### Phase Timeline
- **Proposal**: 2026-09-10 19:29:35 (#487)
- **Delta Specs**: 2026-09-10 19:43:41 (#488)
- **Design**: 2026-09-10 19:45:47 (#489)
- **Tasks**: 2026-09-10 19:51:30 (#490)
- **Apply Progress**: 2026-09-10 20:21:02 (#491, amended 20:43:21)
- **Verify Report**: 2026-09-10 20:43:21 (#492)
- **Archive**: 2026-09-10 (this report, #493)

## Task Completion Validation

**Status**: All 27 tasks marked [x] complete.

| Phase | Goal | Tasks | Status |
|-------|------|-------|--------|
| 1 | Member client functions (lib/organizations.ts) | 1.1–1.2 | 2/2 |
| 2 | Self-removal repointing (state/organizations.ts) | 2.1–2.7 | 7/7 |
| 3 | Members hook (state/members.ts) | 3.1–3.3 | 3/3 |
| 4 | Presentational components (MembersList, MemberRow, AddMemberForm) | 4.1–4.6 | 6/6 |
| 5 | Container page (app/(app)/settings/members/page.tsx) | 5.1–5.4 | 4/4 |
| 6 | Topbar wiring (AppTopbar.tsx link) | 6.1–6.2 | 2/2 |
| 7 | Verification (build, lint, backend check) | 7.1–7.3 | 3/3 |

Task Completion Gate passes. No unchecked implementation tasks remain.

## Verification Summary

**Final Verdict**: PASS (per `verify-report.md`'s Post-verify amendment / Final Verdict sections)

### Original Issues (3 WARNING, 0 CRITICAL) — all fixed before archive
1. **WARNING 1 (Fixed)**: No single page-level integration test for a non-OWNER's successful self-leave. Resolved by adding "a non-OWNER successfully leaves the organization: repoints state and redirects" to `page.test.tsx`.
2. **WARNING 2 (Fixed)**: `apply-progress` lacked the structured TDD Cycle Evidence table. Resolved by appending it to Engram observation #491.
3. **WARNING 3 (Fixed)**: Safety-net baseline pass counts not reported. Resolved by appending them (lib/organizations.ts 2/2, state/organizations.ts 6/6, AppTopbar.tsx 2/2) to #491.

### Final Test Counts
- **Before amendment**: 146/146 passing (34 test files)
- **After amendment**: **147/147 passing** (34 test files)
- Build (typecheck): PASSED
- Lint: PASSED
- Backend changes: NONE (`git diff --stat -- backend/` and `git status --porcelain backend/` both empty)

### Requirements & Scenarios Coverage
| Metric | Count |
|--------|-------|
| Requirements (web-member-management) | 5/5 |
| Scenarios (web-member-management) | 12/12 |
| Requirements (web-organization-workspace, modified) | 1/1 |
| Scenarios (web-organization-workspace, added) | 2/2 |
| **Total Requirements** | **6/6** |
| **Total Scenarios** | **17/17** |

### Design Coherence (DD1–DD7 + Self-Removal Ordering)
All confirmed followed via direct source reading: DD1 (no try/catch in client functions), DD2 (`useMembers` local `useState`, no atom), DD3 (mutators await before writing state), DD4 (page reads atoms via `useAtomValue`), DD5 (single-slot `rowError`), DD6 (`canManage` derivation), DD7 (OWNER unreachable in add form; sole-owner-demote scenario stays reachable), and the self-removal ordering (DELETE → atom+storage batch → `router.replace`).

### Open Findings
- 0 CRITICAL, 0 BLOCKED issues.
- 2 informational SUGGESTIONS (non-blocking; one adopted into the WARNING 1 fix, the other — coverage tooling — out of scope for this change).

## Specs Merged

### `web-member-management` (NEW CAPABILITY)
`openspec/specs/web-member-management/spec.md` — 5 requirements, 12 scenarios. Scope: an OWNER can view, add (EDITOR/VIEWER only), re-role, and remove members; any member can leave; backend 409 `LastOwnerError` surfaces inline per row.

### `web-organization-workspace` (MODIFIED CAPABILITY)
`openspec/specs/web-organization-workspace/spec.md` — "Organization List and Active Selection" extended with two new self-removal-repointing scenarios (repoint to a remaining org, or fall back to no-organization state). Other requirements preserved unchanged.

## Implementation Summary

Frontend-only, Strict TDD, one approved `size:exception` single PR (~950–1050 lines forecast; 1425 code lines / 2096 total including openspec docs, measured at settle time).

**Modified** (5): `lib/organizations.ts`, `lib/__tests__/organizations.test.ts`, `state/organizations.ts`, `state/__tests__/organizations.test.ts`, `components/workspace/AppTopbar.tsx` (+ its test).

**Created** (11): `state/members.ts` (+ test), `components/workspace/MemberRow.tsx` (+ test), `components/workspace/MembersList.tsx` (+ test), `components/workspace/AddMemberForm.tsx` (+ test), `app/(app)/settings/members/page.tsx` (+ test), plus `tasks.md` fully checked.

**Backend**: untouched (0 changes).

## Recommendations

**Next**: None. Change is complete. All work units archived, all specs synced, SDD cycle closed.

**Per project convention**: every verify WARNING is fixed before archiving, never deferred as debt — applied here for all 3 warnings.
