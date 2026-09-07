# Archive Report: Server-Enforced Protected Routes

**Change**: ssr-protected-routes  
**Date**: 2026-09-06  
**Status**: ARCHIVED  
**Verdict**: PASS (two documentation warnings resolved pre-archive)

---

## Executive Summary

Server-enforced route protection is complete, verified, and ready for production. The change adds a server-side session validity check to prevent unauthenticated requests from receiving protected-route markup, hardening the existing client-side `SessionGuard` without backend changes or new migrations. All 288 tests pass (102 frontend + 186 backend), all 19 implementation tasks complete, and the sole spec requirement's 6 scenarios are compliant. Two documentation findings (DV6 and DV7) discovered during verification were corrected in-place in `proposal.md` and `design.md` before archive.

---

## Artifacts Read

All required SDD artifacts read from the change folder (hybrid mode):

1. **proposal.md** — Intent, scope, decisions D1–D8, dependencies, success criteria
2. **specs/web-session/spec.md** — Delta spec: MODIFIED `Session State and Route Protection` requirement (3 new scenarios added)
3. **design.md** — Technical approach, DD1–DD8 architecture decisions, file changes, testing strategy, threat matrix, deviations DV1–DV7
4. **tasks.md** — 19 tasks across 8 phases: foundation config, core logic, wiring, documentation, verification
5. **verify-report.md** — Independent verification: 102/102 frontend tests, 186/186 backend tests, 6/6 spec scenarios compliant, PASS verdict (warnings resolved)

---

## Spec Merge Summary

**Domain**: `web-session`  
**Action**: MODIFIED requirement

**Change applied to** `openspec/specs/web-session/spec.md`:

- **Requirement**: `Session State and Route Protection`
  - **Original**: 3 scenarios (Anonymous access redirected, Backend outage, Open-redirect guarded)
  - **Added**: 3 new scenarios (Anonymous server-side, Invalid cookie rejected server-side, Backend unreachable falls through)
  - **Total**: 6 scenarios (3 pre-existing preserved verbatim, 3 new)
  - **Delta details**:
    - Added server-side session validity check requirement (not merely cookie presence)
    - Non-caching constraint on validity checks (per-request, per-user)
    - Previous behavior note documenting the shift from client-only to server-validated

All other requirements in the main spec remain untouched.

---

## Archive Contents

```
openspec/changes/archive/2026-09-06-ssr-protected-routes/
├── proposal.md                  (18.2 KB)
├── design.md                    (21.9 KB)
├── tasks.md                     (8.1 KB)
├── verify-report.md             (18.4 KB)
├── exploration.md               (7.5 KB — provided for context)
├── specs/
│   └── web-session/
│       └── spec.md              (delta spec, now merged into main)
└── archive-report.md            (this file)
```

**Key files preserved**:
- All tasks marked complete (19/19 ✓)
- No unchecked implementation tasks
- Proposal and design include corrections for DV6 and DV7

---

## Final State Authority

This archive report describes the change state **at close**, not at intermediate snapshots. Facts ranked per the archive protocol:

1. **Native review authority**: Not applicable (no review gate discovered).
2. **Persisted tasks artifact**: All 19 tasks checked complete in `tasks.md` at 2026-09-06 23:07.
3. **Explicit final-state facts in launch prompt**: 
   - Verdict is PASS (not PASS WITH WARNINGS); both warnings resolved by orchestrator edits to proposal.md and design.md
   - Test count: 288/288 (102 frontend + 186 backend)
4. **verify-report snapshot**: Issued 2026-09-06 with full test run independent of apply-progress claims.

---

## Implementation Summary

### Test Results (Final)

| Layer | Count | Status | Tools |
|-------|-------|--------|-------|
| Frontend (new + baseline) | 102 | ✓ PASS | Vitest + jsdom |
| Backend (unchanged) | 186 | ✓ PASS | pytest |
| **Total** | **288** | **PASS** | |

Frontend tests: 29 files, all passing. New tests (15) distributed across:
- `frontend/src/lib/__tests__/env.test.ts` (2 cases) — `internalApiUrl` override/fallback
- `frontend/src/lib/__tests__/server-session.test.ts` (13 cases) — `getServerUser()` and `requireUser()` logic

Backend: No new migrations, no model changes, 186/186 existing tests remain green.

### Files Modified (8 frontend, 1 backend config, 1 openspec spec)

| File | Action | Notes |
|------|--------|-------|
| `frontend/src/lib/server-session.ts` | **Create** | `getServerUser()` + `requireUser()` (DD1) |
| `frontend/src/lib/__tests__/server-session.test.ts` | **Create** | 13 unit test cases (DD7) |
| `frontend/src/lib/__tests__/env.test.ts` | **Create** | 2 config override/fallback cases (DV3) |
| `frontend/src/lib/env.ts` | Modify | `readInternalApiUrl()` + export (DD5) |
| `frontend/src/app/(app)/layout.tsx` | Modify | `async` + `await requireUser("/dashboard")` + docblock (DD6/DV4) |
| `frontend/src/app/(gate)/layout.tsx` | Modify | `async` + `await requireUser("/select-organization")` (DD6) |
| `docker-compose.yml` | Modify | `INTERNAL_API_URL: http://backend:8000` env var |
| `frontend/env.local.example` | Modify | Document `INTERNAL_API_URL` + cross-domain precondition |
| `backend/env.example` | Modify | Document `ALLOWED_HOSTS` addition (`,backend`) — config only, not app code (DV6) |
| `openspec/specs/web-session/spec.md` | Modify | Merged delta: +3 scenarios (spec merge above) |

**Untouched per design**:
- `frontend/src/components/auth/SessionGuard.tsx` and its test — zero-line diff confirmed (D4/N8)
- Backend app code (`apps/users/*`, models, migrations, endpoints) — zero changes (N2)
- `frontend/src/app/(app)/dashboard/page.tsx`, `(gate)/select-organization/page.tsx` — client-side org fetch unchanged (N1/D5)

---

## Deviations Summary (Documented in Design & Proposal)

**DV6 — ALLOWED_HOSTS in `backend/env.example`**:  
Discovered during mandatory manual verification (proposal D6): the frontend container's server-side fetch to `http://backend:8000` was rejected `400` by Django's `CommonMiddleware` until `backend` was added to `ALLOWED_HOSTS`. This is framework-level HTTP Host-header validation config, not application code — no model, schema, endpoint, or migration changed. N2's actual intent (application behavior unchanged) is satisfied. Verified independently: `git status` shows no new file under `migrations/`, `git diff --stat -- backend/` shows only `backend/env.example` (6 lines changed). Proposal Success Criteria corrected to state the diff is limited to config-only, with explicit justification.

**DV7 — DD8 Step 3 verification check and design.md's "nothing has flushed" claim**:  
Independently reproduced at both apply and verify phases: Next.js 16.3.3 always streams a small inert `<html id="__next_error__">` redirect shell, even with no `<Suspense>` boundaries. The response body was read in full and confirmed zero real dashboard/org/user data — only Next's internal scaffolding. The underlying spec scenario ("no protected markup") holds; only the literal grep-based proxy for that property (`rg -c "<html"`) was incorrect. Corrected in design.md's Technical Approach note, DD8 Step 3 rewritten to check for absence of real content markers (`dashboard-page`, `organization`, `AppTopbar`, `SessionGuard`, `Acme`), and a new DV7 row in Deviations table documents the finding. Both DV6 and DV7 are genuinely novel findings discovered only during manual verification.

---

## Verification Status

### Spec Compliance

**Requirement**: Session State and Route Protection  
**Scenarios**: 6/6 compliant

| Scenario | Test Evidence | Status |
|----------|---------------|--------|
| Anonymous access redirected with next | SessionGuard.test.tsx (pre-existing) | ✓ COMPLIANT |
| Backend outage does not log out | server-session.test.ts cases 8/9/13 | ✓ COMPLIANT |
| Open-redirect guarded | server-session.test.ts case 12 | ✓ COMPLIANT |
| Anonymous server-side request never receives protected markup | server-session.test.ts cases 1-11 + manual DD8 steps 1-3 | ✓ COMPLIANT (see DV7) |
| Invalid/expired cookie rejected server-side | server-session.test.ts cases 6/7 + manual step 4 | ✓ COMPLIANT |
| Backend unreachable falls through to client | server-session.test.ts cases 8/9/13 + manual step 8 | ✓ COMPLIANT |

### TDD Compliance

- [x] All RED cases exist and fail before implementation (15 new test cases defined at task start)
- [x] All GREEN implementations pass (102/102 frontend tests, including 15 new + 87 baseline)
- [x] Triangulation adequate (13 distinct branches in server-session.test.ts, 2 env config branches)
- [x] No tautologies or ghost loops (all assertions target real behavior, not implementation details)
- [x] Safety net for modified files (pre-existing 87 baseline tests remain green)

### Manual Verification (DD8 Checklist)

All 8 manual steps executed with `docker compose up -d --build` and `seed_demo`:

| Step | Check | Result | Status |
|------|-------|--------|--------|
| 1 | `curl` no cookie → `307` | 307 returned | ✓ PASS |
| 2 | Location header correct | `/login?next=%2Fdashboard` | ✓ PASS |
| 3 | No protected content in body | Verified clean of dashboard/org/user markers | ✓ PASS (see DV7) |
| 4 | Invalid cookie → `307` | 307 with fake cookie | ✓ PASS |
| 5 | `/select-organization` same | 307, `next=%2Fselect-organization` | ✓ PASS |
| 6 | Valid session → `200` | Rendered dashboard | ✓ PASS |
| 7 | Picker unchanged (D5) | 200, client-side redirect stays | ✓ PASS |
| 8 | Backend outage → no redirect | Rendered via SessionGuard error | ✓ PASS |

---

## Task Completion

**Phase 1 (Config Foundation)**: 2/2 ✓  
- [x] 1.1 RED: env.test.ts (2 cases)
- [x] 1.2 GREEN: internalApiUrl implementation

**Phase 2 (Core Logic — getServerUser)**: 2/2 ✓  
- [x] 2.1 RED: server-session.test.ts cases 1-9
- [x] 2.2 GREEN: getServerUser implementation

**Phase 3 (Core Logic — requireUser)**: 3/3 ✓  
- [x] 3.1 RED: server-session.test.ts cases 10-13
- [x] 3.2 GREEN: requireUser implementation
- [x] 3.3 REFACTOR: docblock and import verification

**Phase 4 (Layout Wiring)**: 2/2 ✓  
- [x] 4.1 Modify `(app)/layout.tsx`
- [x] 4.2 Modify `(gate)/layout.tsx`

**Phase 5 (Config)**: 2/2 ✓  
- [x] 5.1 docker-compose.yml: INTERNAL_API_URL
- [x] 5.2 env.local.example: documentation

**Phase 6 (Manual Verification)**: 1/1 ✓  
- [x] 6.1 DD8 checklist executed

**Phase 7 (Documentation)**: 3/3 ✓  
- [x] 7.1 CURRENT_STATE.md updated
- [x] 7.2 DECISIONS_LOG.md updated (D1-D8, DV1-DV7)
- [x] 7.3 README.md and ARCHITECTURE.md updated

**Phase 8 (Final Verification)**: 4/4 ✓  
- [x] 8.1 Full test suite: 102/102 frontend, 186/186 backend green
- [x] 8.2 SessionGuard.tsx zero-line diff confirmed
- [x] 8.3 Backend diff limited to config (env.example), no app code/migrations
- [x] 8.4 Proposal Success Criteria checklist walked

**Total: 19/19 tasks complete**

---

## Rollback Plan (Preserved)

Per proposal: cheap and partial-revert-safe, because **no backend, model, migration, or existing frontend module changes**.

1. `git revert` the change commits: both layouts return to synchronous, `server-session.ts` disappears.
2. Partial rollback: reverting only layouts leaves helper unused but harmless.
3. `INTERNAL_API_URL` is additive with fallback; leaving it set is inert.
4. `web-session` delta reverts with the same commits.

---

## Resolved Issues

**Issue DV6 (Proposal wording)**:  
✓ RESOLVED in `proposal.md` Success Criteria line about `backend/` diff — rewritten to state the diff is limited to `backend/env.example` (config only) and explain why (framework-level Host validation, inherent to D2).

**Issue DV7 (Design.md technical claim)**:  
✓ RESOLVED in `design.md` Technical Approach section (new correction note), DD8 Step 3 (rewritten to check real content markers instead of literal `<html>`), and Deviations table (new DV7 row documenting the finding and its resolution).

---

## No Open Warnings

The two warnings found during verification have been fully resolved:
- DV6 was resolved by correcting proposal.md Success Criteria wording with explicit documentation
- DV7 was resolved by correcting design.md's technical claim and DD8's verification check

No blockers, no CRITICAL findings, no open WARNINGs remain.

---

## Risks & Mitigations

| Risk | Mitigation | Status |
|------|-----------|--------|
| Cross-domain deploy breaks gate | Documented in env.local.example, README, ARCHITECTURE.md as deployment precondition (tech debt #2) | ✓ MITIGATED |
| Server fetch `ECONNREFUSED` in container | `INTERNAL_API_URL` env var with fallback (D2, DV6) | ✓ MITIGATED |
| Layout wiring untested (automated) | DD8 manual checklist (D6, proposal D6) | ✓ MITIGATED |
| Outage mistaken for logout | Non-`401` failures throw; caught and render (D2, DD8 step 8) | ✓ MITIGATED |
| `SessionGuard` read as dead code | D4 clearly states two-layer rationale in design doc | ✓ MITIGATED |

---

## Dependencies & Delivery

- **No new package dependency** — `next/headers`, `next/navigation`, `React.cache` all included with Next 16.3.3
- **New runtime requirement** — Backend must be reachable from the Next.js server at `INTERNAL_API_URL`
- **Builds on**: Archived `frontend-auth-integration` (DD3 session validity deferral) and `tenant-aware-registration-login`
- **No migrations, no model changes** — Zero schema/migration files in the archive

---

## Key Learnings

1. Server-side session validity checks prevent unauthenticated markup leakage; client-side guards remain essential for mid-session expiry and loading states.
2. Layout wiring in Next.js async Server Components has no reliable automated test interface; manual curl verification is the honest proxy for this class of work.
3. Docker Compose internal service names (like `backend`) must be explicitly listed in Django's `ALLOWED_HOSTS` to satisfy Host-header validation, even though they are not internet-resolvable.
4. Next.js `redirect()` always streams a small error scaffold (inert shell + stack trace in dev mode); protection success is measured by absence of real protected content, not literal absence of HTML tags.
5. Framework-level config (Host validation, env vars) changes are properly separable from application behavior changes; clarifying that distinction in Success Criteria prevents false contradiction between letter and intent.

---

**Archive created**: 2026-09-06 at 23:08 UTC  
**Verified by**: sdd-archive executor  
**Ready for deployment**
