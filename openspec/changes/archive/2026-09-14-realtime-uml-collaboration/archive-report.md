# Archive Report: Real-time UML Collaboration

**Change**: 2026-09-14-realtime-uml-collaboration  
**Date Archived**: 2026-09-14  
**Archive Location**: `openspec/changes/archive/2026-09-14-realtime-uml-collaboration/`

## Executive Summary

Successfully archived the real-time UML collaboration change after implementation, verification, and spec synchronization. All 43 implementation tasks completed. Verification returned PASS WITH WARNINGS (0 CRITICAL issues). Change is fully closed and ready for production deployment.

## Artifacts Integrated

### Source of Truth Specifications (Merged)

| Spec Domain | Action | Details |
|---|---|---|
| `realtime-document-sync` | Created | New capability: WebSocket connection lifecycle, per-document group membership, broadcast synchronization. Full spec copied from delta. |
| `uml-document-persistence` | Updated | MODIFIED: Command submission now serialized under row lock; broadcast emitted after commit via `transaction.on_commit`. Merged into existing spec via `gentle-ai sdd-archive-compose`. |
| `web-uml-canvas` | Updated | MODIFIED: Added remote update convergence without disrupting local gestures (pending relationship selection, active node drag). Merged into existing spec via `gentle-ai sdd-archive-compose`. |

### Design Decisions Finalized

All 13 architecture decisions (DD1–DD13) from `design.md` are implemented and verified:

- **DD1**: Atomic `submit_command` with conditional `select_for_update()` on `_get_row` (preserves tenant scoping)
- **DD2**: Broadcast via `transaction.on_commit` after `_save` (matches `users/services.py` pattern)
- **DD3**: Sync `DocumentConsumer` routed to `ws/orgs/<org_slug>/documents/<doc_id>/`
- **DD4**: Membership-only WS auth (no role gate, mirrors read-endpoint `GET /api/orgs/{slug}/documents/{docId}`)
- **DD5**: Re-authorization on broadcast relay; terminal close code `4403` on revoked membership
- **DD6**: Broadcast payload is existing `DocumentOut` (byte-identical to GET response); `codec.document_out()` promoted
- **DD7**: Envelope type `"document.update"` routes through Channels' type dispatch
- **DD8**: Redis channel layer via discrete `REDIS_HOST`/`REDIS_PORT` env vars, mirroring `DATABASES` pattern; healthcheck on `redis` service
- **DD9**: `OriginValidator` outermost, reusing `CORS_ALLOWED_ORIGINS`; no CSRF equivalent (socket is read-only)
- **DD10**: Dev server: `manage.py runserver` already serves WebSocket (Daphne in `INSTALLED_APPS` before `django.contrib.staticfiles`); no Dockerfile diff
- **DD11**: WS client inside `useDocument`, monotonic-revision merge returns `prev` by identity for zero re-renders on equal revision
- **DD12**: No guard for `pendingSourceId`/`pendingTargetId` (unreachable from `useDocument`); drag guard via `draggingRef`/`pendingUpdateRef`, deferred sync on `free`
- **DD13**: Terminal close codes `4401`/`4403`/`4404` (no reconnect); capped backoff on other closes (1s→2s→4s→8s→10s)

## Test Verification

**Verification Result**: PASS WITH WARNINGS

- **Backend Tests**: 340/340 passed (339 prior + 1 remediation)
- **Frontend Tests**: 294/294 passed (293 prior + 1 remediation)
- **Linting**: Clean (`npm run lint`, exit 0)
- **Type Checking**: Clean (`npx tsc --noEmit`, exit 0)
- **Build**: Clean (`npm run build`, exit 0)

### Spec Coverage

All 6 requirements and 15 scenarios across 3 spec deltas are COMPLIANT:

**realtime-document-sync** (3 requirements, 6 scenarios)
- WS Connection Lifecycle and Authorization ✅
- Broadcast on Successful Command ✅
- Broadcast Timing Relative to the Transaction ✅

**uml-document-persistence** (1 requirement, 4 scenarios)
- Command Submission (including new concurrent-lock scenario) ✅

**web-uml-canvas** (2 requirements, 5 scenarios)
- Diagram Rendering (including remote-update scenario) ✅
- Remote Update Does Not Disrupt an In-Progress Local Gesture ✅ (new)

### Remediation Closure (Phase 9)

Per `tasks.md` Phase 9, two test-coverage gaps from the prior verify-report were closed by additive test-only changes (zero production-code diff):

- **9.1 (CRITICAL-1)**: `test_submitters_own_socket_also_receives_the_broadcast_it_triggered` — connects both submitter and observer to the same document group; confirms broadcast includes the submitter (now runtime-proven, previously true by construction)
- **9.2 (CRITICAL-2)**: `page.test.tsx` "a remote update that keeps the pinned class present does not disrupt the pending relationship selection" — simulates WS update mid-gesture, proves gesture completion still works

Both new tests passed on first execution; no regressions detected in full suites.

## Task Completion

All 43 implementation tasks marked complete ([x]) in `tasks.md`:

- **Phase 1** (Redis & Channel Layers): 5 tasks ✅
- **Phase 2** (Locked Submission & Broadcast Seam): 8 tasks ✅
- **Phase 3** (Membership Extraction): 2 tasks ✅
- **Phase 4** (WebSocket Consumer & Routing): 9 tasks ✅
- **Phase 5** (Frontend WebSocket Client): 7 tasks ✅
- **Phase 6** (Canvas Drag Guard): 3 tasks ✅
- **Phase 7** (Documentation): 2 tasks ✅
- **Phase 8** (Verification): 5 tasks ✅
- **Phase 9** (Verification Remediation): 2 tasks ✅

No unchecked implementation tasks remain. Task Completion Gate: **PASS**.

## Risk Assessment

**Warnings from verify-report (non-blocking)**:

1. **TDD Evidence Format**: Tasks 9.1/9.2 documented inline in `tasks.md` as RED:/GREEN: annotations rather than a formal per-task TDD Cycle Evidence table. Unchanged from prior pass; remediation phase documents consistently with the rest of the change. This is a process/documentation preference, not a correctness defect.

2. **Boot Banner & Healthcheck Evidence**: Tasks 4.6/1.5 boot-banner and Redis healthcheck evidence were "confirmed by orchestrator" from a prior session; this pass independently confirmed the currently-running redis-1 container is Healthy and `docker compose exec backend pytest` executes successfully against it. Strong but not identical to a fresh banner read this session. Unchanged from prior pass; no impact on correctness.

No new issues introduced. No defects or regressions detected in code or tests.

## Merged Specs Verification

Mechanical `diff -r` readback after each composition and copy operation confirmed byte-identity:

```
✅ uml-document-persistence/spec.md — composed via gentle-ai sdd-archive-compose (0 exit)
✅ web-uml-canvas/spec.md — composed via gentle-ai sdd-archive-compose (0 exit)
✅ realtime-document-sync/spec.md — copied mechanically (0 exit, empty diff)
```

All deltas applied cleanly with no conflicts or truncations.

## Archive Contents

The change is archived at `openspec/changes/archive/2026-09-14-realtime-uml-collaboration/`:

- ✅ `proposal.md` — intent, scope, approach, risks, rollback plan
- ✅ `design.md` — technical approach, 13 architecture decisions, sequence diagram, interfaces, testing strategy
- ✅ `tasks.md` — 43 tasks across 9 phases, all complete
- ✅ `verify-report.md` — PASS WITH WARNINGS, 0 CRITICAL, 6/6 requirements COMPLIANT, 15/15 scenarios COMPLIANT
- ✅ `exploration.md` — research and candidate selection
- ✅ `specs/` — 3 delta specs (all merged into main `openspec/specs/`)

The source change folder `openspec/changes/2026-09-14-realtime-uml-collaboration/` no longer exists (successfully moved to archive).

## Rollback Plan Validation

Per proposal §Rollback Plan, the change is independently revertable via `git revert`:

- Backend degrades to fetch-on-mount behavior once `asgi.py` router is emptied
- Frontend WS client reconnection attempts fail, falling back to existing `useDocument` behavior
- The `atomic`/`select_for_update` hardening (DD1) is independently revertable and safe to retain
- Redis is purely additive; removing the `CHANNEL_LAYERS` config disables broadcast

## Completion Status

- **SDD Cycle**: COMPLETE
- **Archive Operation**: COMPLETE
- **Spec Synchronization**: COMPLETE
- **Source Change Folder**: REMOVED (archived)
- **Delivery Readiness**: READY

## Key Learnings

1. Remediation tests for coverage gaps on already-correct code succeed on first execution, confirming construction correctness
2. Mechanical archive operations (gentle-ai sdd-archive-compose, cp -R, git mv/mv, diff -r) are the only safe spec-merge path — model Read/Write cannot preserve byte-identity
3. Discrete Redis host/port env vars matching DATABASES pattern improves consistency with existing project conventions
4. Terminal close codes (4401/4403/4404) prevent reconnect loops for auth failures, while allowing recovery for transient network issues
