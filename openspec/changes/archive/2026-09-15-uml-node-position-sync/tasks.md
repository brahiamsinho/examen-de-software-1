# Tasks: Live UML Node Position Sync

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1150-1250 (backend ~650, frontend ~490, docs ~60) |
| 800-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend) → PR 2 (frontend + docs) |
| Delivery strategy | ask-on-risk (session default; not overridden) |
| Chain strategy | size:exception — user accepted a single PR despite exceeding the 800-line budget |

Decision needed before apply: Resolved
Chained PRs recommended: Yes (declined by user)
Chain strategy: size:exception, single PR
800-line budget risk: High (accepted)

Each PR is independently well under the 800-line budget (~650 and ~550
respectively); only the combined single-PR total is at risk. This mirrors
design.md's own two-slice suggestion (backend vs. frontend). Ask the user:
stacked-to-main (PR 2 merges after PR 1 lands) vs feature-branch-chain (PR 1
→ tracker, PR 2 → PR 1 branch) vs `size:exception` for one PR, as in the
prior two SDD cycles on this project.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Redis lock module + layout-persistence service + `receive_json`/`connect`/`disconnect` wiring | PR 1 | `pytest backend/apps/uml_documents/tests/test_locks.py backend/apps/uml_documents/tests/test_services.py backend/apps/uml_documents/tests/test_consumers.py` | Two `WebsocketCommunicator` sockets against test Redis + Postgres | `git revert` restores read-only socket; `layout` stays valid but unread; orphan Redis keys self-expire |
| 2 | Frontend layout seeding, lock UI, drag wiring, docs | PR 2 | `npm run test -- DiagramCanvas document uml_documents` | Two browser tabs on `documents/[docId]` dragging one class (manual) | `git revert` restores full-`fcose` seeding, drops claim/live/release sends; PR 1's backend stays functional standalone |

## Phase 1: Redis Node-Lock Module

- [x] 1.1 RED — `backend/apps/uml_documents/tests/test_locks.py`: claim-twice returns `(False, label)`; foreign-token release/refresh return `False` and leave the key; release-then-reclaim succeeds (locking: Claim Acquisition, TTL and Refresh)
- [x] 1.2 GREEN — Create `backend/apps/uml_documents/locks.py`: sync `redis.Redis` pool, `claim`/`refresh`/`release`/`snapshot`, registered Lua scripts (DD1-DD3, DD10)
- [x] 1.3 Promote `redis>=5.0,<6.0` in `backend/requirements/base.txt` (DD1)

## Phase 2: Layout Persistence Service

- [x] 2.1 RED — Add to `backend/apps/uml_documents/tests/test_services.py`: `save_layout_position` bumps revision by 1, model unchanged; absent-class-id writes nothing/no bump; stale entry pruned on next persist (persistence: Layout Persistence via Non-Command Path, Revision Bumps Only on Persisted Position Release, Absent Class Ids Are Pruned)
- [x] 2.2 GREEN — Add `save_layout_position` to `backend/apps/uml_documents/services.py` per design's Interfaces/Contracts (DD8)

## Phase 3: Consumer Wiring

- [x] 3.1 RED — Extend `backend/apps/uml_documents/tests/test_consumers.py` (`WebsocketCommunicator`, `django_capture_on_commit_callbacks`): second claim on held node rejected; VIEWER refused on `node.claim`; disconnect emits `node.unlocked` + no `document.update`; non-owner `node.position` neither persisted nor broadcast; fresh join receives `node.locks` snapshot; release broadcasts `document.update` exactly once, live frames broadcast zero (sync: Inbound Client Messages, Claim Outcome Delivery, Live Position Broadcast, Release Broadcast Carries Persisted State; locking: Release on Completion or Disconnect)
- [x] 3.2 GREEN — `receive_json` on `DocumentConsumer`: per-message `require_role(OWNER, EDITOR)`, handle `node.claim`/`node.position`/`node.release`, silent-drop malformed frames (DD6)
- [x] 3.3 GREEN — `connect()`: set `self.token`/`self.label`/`self.held`; send `node.locks` snapshot via `SCAN` (DD10)
- [x] 3.4 GREEN — `node_locked`/`node_unlocked`/`node_position` group handlers deriving `mine`, never forwarding `owner_token` (DD9)
- [x] 3.5 GREEN — `disconnect()`: release every id in `self.held` via Lua release, `group_send` `node.unlocked` each, guarded with `getattr(self, "held", set())` (DD7)

## Phase 4: Frontend Message Types & Layout Seeding

- [x] 4.1 RED — Vitest: `toElements(model, layout)` seeds `position` for persisted ids, omits it for unplaced ones (canvas: Diagram Rendering — Persisted positions are seeded)
- [x] 4.2 GREEN — `frontend/src/components/workspace/DiagramCanvas.tsx`: `toElements(model, layout)` signature, seed `laidOutClassIdsRef` from `layout.positions` (DD13)
- [x] 4.3 GREEN — `frontend/src/lib/uml_documents.ts`: lock/position message types, `DocumentSocketHandlers` (`onNodeLocked`/`onNodeUnlocked`/`onNodePosition`/`onNodeLocks`/`onClaimRejected`), send helpers

## Phase 5: Frontend State (`document.ts`)

- [x] 5.1 RED — Vitest: 50ms throttle emits at most one `node.position` per interval and always sends the final position on `free`
- [x] 5.2 GREEN — `frontend/src/state/document.ts`: `locks` state, `positionListenerRef`, `sendClaim`/`sendPosition`/`sendRelease`, throttle (DD4, DD11)

## Phase 6: Canvas & Page Wiring

- [x] 6.1 RED — RTL: foreign `node.locked` ungrabifies + renders owner affordance, `node.unlocked` restores `grabify()`; `node.claim_rejected` restores `grabStartPosRef` position; remote `node.position` moves node with zero re-render; empty `layout.positions` runs full first-layout `fcose` (canvas: Drag Emits Claim/Live/Release, Remote Live Position Frames, Foreign Lock Rendering, Claim Rejection Feedback)
- [x] 6.2 GREEN — `DiagramCanvas.tsx`: grab/drag/free handlers sending claim/throttled-position/release; `ungrabify()`/`.locked-remote` styling; `positionListenerRef` imperative apply (DD11-DD13)
- [x] 6.3 GREEN — `frontend/src/app/(app)/documents/[docId]/page.tsx`: pass `layout`/`locks`/handlers; render "X is moving Y" affordance (DD12)

## Phase 7: Cross-Cutting Verification & Docs

- [x] 7.1 Verify `RemoveClass` on a held node end-to-end: backend test (3.1) confirms no error/stranded lock; RTL test (6.1) confirms canvas drops local lock (locking: Lock Is Advisory; canvas: Local Node Removed While Held Drops the Local Lock)
- [x] 7.2 Append DD1-DD13 to `docs/ai/DECISIONS_LOG.md`
- [x] 7.3 Update `docs/ai/CURRENT_STATE.md`: socket is bidirectional; `layout` is live; `with_layout` has a production caller

## Remediation

- [x] R.1 Close CRITICAL finding from `verify-report.md` (uml-node-locking, "Claim TTL and Refresh" / "An abandoned claim expires via TTL" was untested at runtime): added `test_claim_sets_a_ttl_close_to_lock_ttl_ms` (asserts `PTTL` is in `(0, LOCK_TTL_MS]` right after `claim()`) and `test_abandoned_claim_expires_via_ttl_and_becomes_claimable_again` (patches `locks.LOCK_TTL_MS` to 50ms for the test only, sleeps past it, asserts the key becomes claimable again) to `backend/apps/uml_documents/tests/test_locks.py`. Test-only change; `locks.py` untouched.
