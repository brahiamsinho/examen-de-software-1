```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:bbc3ebfb2e8c248f99994f63bb6fd64c50362acecb0aafdf6985036190176533
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 17/17
scenarios: 31/31
test_command: docker compose exec backend pytest -q && (cd frontend && npx vitest run)
test_exit_code: 0
test_output_hash: sha256:04427626deda6167bc6d557ff79b166daa96ae88b95ad5f56888b9dea81bbaf2
build_command: cd frontend && npx tsc --noEmit
build_exit_code: 0
build_output_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Verification Report

**Change**: 2026-09-15-uml-node-position-sync
**Version**: N/A (OpenSpec delta specs, no semver)
**Mode**: Strict TDD
**Re-verification note**: this run re-verifies the change after a scoped remediation apply that added exactly 2 tests to `backend/apps/uml_documents/tests/test_locks.py` (zero production files touched) to close the single CRITICAL from the prior `verify-report.md` run.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 22 |
| Tasks complete | 22 |
| Tasks incomplete | 0 |

### Build and Tests Execution
**Build**: Passed
```text
$ cd frontend && npx tsc --noEmit
(no output, exit 0)
```

**Tests**: 678 passed / 0 failed / 0 skipped
```text
$ docker compose exec backend pytest apps/uml_documents/tests/test_locks.py -q
10 passed in 1.14s (8 pre-existing plus 2 new: test_claim_sets_a_ttl_close_to_lock_ttl_ms,
test_abandoned_claim_expires_via_ttl_and_becomes_claimable_again)

$ docker compose exec backend pytest -q
361 passed in 44.50s

$ cd frontend && npx vitest run
Test Files  52 passed (52)
Tests  317 passed (317)
```

**Coverage**: Not configured for this project -> Not available

### Spec Compliance Matrix

#### uml-node-locking
| Requirement | Scenario | Test | Result |
|---|---|---|---|
| Claim Acquisition and Server-Side Arbitration | A claim on an unheld node succeeds | test_locks.py::test_claim_on_unheld_key_succeeds | COMPLIANT |
| Claim Acquisition and Server-Side Arbitration | Simultaneous claims resolve to exactly one owner | test_consumers.py::test_second_claim_on_held_node_is_rejected (sequential order, not a true concurrent-thread race; relies on Redis SET NX single-threaded atomicity) | PARTIAL |
| Claim TTL and Refresh | An abandoned claim expires via TTL | test_locks.py::test_abandoned_claim_expires_via_ttl_and_becomes_claimable_again (patches LOCK_TTL_MS to 50ms, confirms a second claim is blocked before expiry, sleeps 3x the TTL, then confirms a fresh claim succeeds with owner_label None) plus test_locks.py::test_claim_sets_a_ttl_close_to_lock_ttl_ms (asserts client.pttl(key) is in (0, LOCK_TTL_MS] immediately after claim) | COMPLIANT |
| Release on Completion or Disconnect | Explicit release frees the node immediately | test_locks.py::test_release_then_reclaim_succeeds | COMPLIANT |
| Release on Completion or Disconnect | Disconnect releases every lock the connection held | test_consumers.py::test_disconnect_releases_held_locks_and_broadcasts_node_unlocked_with_no_document_update | COMPLIANT |
| Lock Is Advisory and Never Blocks Domain Commands | RemoveClass succeeds on a held node | test_consumers.py::test_remove_class_on_a_held_node_does_not_strand_the_lock_or_error_on_release | COMPLIANT |
| Lock Is Advisory and Never Blocks Domain Commands | A removed node lock is not stranded | test_consumers.py::test_remove_class_on_a_held_node_does_not_strand_the_lock_or_error_on_release (re-claim after removal succeeds) plus test_services.py::test_save_layout_position_for_absent_class_id_writes_nothing_and_does_not_bump_revision | COMPLIANT |

#### realtime-document-sync
| Requirement | Scenario | Test | Result |
|---|---|---|---|
| Inbound Client Messages Over the Document Connection | Holder live position update is accepted | test_consumers.py::test_release_broadcasts_document_update_once_and_live_position_broadcasts_zero | COMPLIANT |
| Inbound Client Messages Over the Document Connection | Non-holder position update is rejected without effect | test_consumers.py::test_position_update_from_non_owner_is_neither_persisted_nor_broadcast | COMPLIANT |
| Claim Outcome Delivery | Successful claim broadcasts to all connected clients | test_consumers.py::test_second_claim_on_held_node_is_rejected (asserts both A and B receive node.locked) | COMPLIANT |
| Claim Outcome Delivery | Rejected claim reaches only the requester | test_consumers.py::test_second_claim_on_held_node_is_rejected (asserts A receives nothing) | COMPLIANT |
| Live Position Broadcast Without Persistence | Live drag frames reach other clients without a DB write | test_consumers.py::test_release_broadcasts_document_update_once_and_live_position_broadcasts_zero (asserts zero document.update on live frames) | COMPLIANT |
| Release Broadcast Carries Persisted State | Release broadcasts lock-released and the updated document | test_consumers.py::test_release_broadcasts_document_update_once_and_live_position_broadcasts_zero | COMPLIANT |
| Release Broadcast Carries Persisted State | Disconnect while holding a claim broadcasts a lock-released frame | test_consumers.py::test_disconnect_releases_held_locks_and_broadcasts_node_unlocked_with_no_document_update | COMPLIANT |

#### uml-document-persistence
| Requirement | Scenario | Test | Result |
|---|---|---|---|
| Layout Persistence via Non-Command Path | Layout write persists and broadcasts without a command | test_services.py::test_save_layout_position_bumps_revision_by_one_and_leaves_model_unchanged, test_save_layout_position_broadcasts_exactly_once_after_commit | COMPLIANT |
| Layout Persistence via Non-Command Path | UmlCommand union has zero diff | git diff --stat HEAD against backend/apps/uml_commands and backend/apps/uml_modeling/documents.py is empty (verified directly) | COMPLIANT |
| Revision Bumps Only on Persisted Position Release | Release increments revision by exactly 1 | test_services.py::test_save_layout_position_bumps_revision_by_one_and_leaves_model_unchanged | COMPLIANT |
| Revision Bumps Only on Persisted Position Release | Live position updates never touch revision | test_consumers.py::test_release_broadcasts_document_update_once_and_live_position_broadcasts_zero (zero document.update on live frames) | COMPLIANT |
| Absent Class Ids Are Pruned From Persisted Layout | Persisting a position for a since-removed class is a no-op | test_services.py::test_save_layout_position_for_absent_class_id_writes_nothing_and_does_not_bump_revision, test_save_layout_position_prunes_a_stale_entry_for_a_removed_class_on_next_persist | COMPLIANT |

#### web-uml-canvas
| Requirement | Scenario | Test | Result |
|---|---|---|---|
| Diagram Rendering | Classes and relationships render as nodes and edges | DiagramCanvas.test.tsx pre-existing toElements suite, unaffected | COMPLIANT |
| Diagram Rendering | Auto-layout runs on load | DiagramCanvas.test.tsx: an empty layout.positions still runs the full first-layout fcose path with randomize true (DD13 fallback) | COMPLIANT |
| Diagram Rendering | Persisted positions are seeded instead of recomputed | DiagramCanvas.test.tsx: seeds position from layout.positions for a persisted class id and omits it for an unplaced one (DD13) | COMPLIANT |
| Diagram Rendering | A remote-origin update renders without a full re-layout | DiagramCanvas.test.tsx pre-existing revision-keyed update suite, unaffected by this change | COMPLIANT |
| Drag Emits Claim, Live Position, and Release | Grabbing a node sends a claim before drag proceeds | DiagramCanvas.test.tsx grab handler test wiring onClaim | COMPLIANT |
| Drag Emits Claim, Live Position, and Release | Dragging sends throttled live updates, not one per mousemove | document.test.ts: sendPosition emits at most one frame per 50ms window and always flushes the final coalesced position | COMPLIANT |
| Drag Emits Claim, Live Position, and Release | Releasing sends one release message with the final position | DiagramCanvas.test.tsx: releasing a node calls onRelease with its final coordinates exactly once | COMPLIANT |
| Remote Live Position Frames Move the Node | A remote live position frame moves the node in real time | DiagramCanvas.test.tsx: positionListenerRef moves a node imperatively via getElementById position without calling cy.json again | COMPLIANT |
| Foreign Lock Rendering and Local Grab Prevention | A foreign-held node shows who holds it | page.test.tsx foreign-lock affordance test plus DiagramCanvas.test.tsx: ungrabifies and tags a foreign-held node | COMPLIANT |
| Foreign Lock Rendering and Local Grab Prevention | Local grab on a foreign-held node is prevented or rejected | DiagramCanvas.test.tsx: ungrabifies and tags a foreign-held node with locked-remote class (ungrabify prevents the grab event entirely) | COMPLIANT |
| Claim Rejection Feedback | A lost claim race shows rejection feedback and no hold begins | DiagramCanvas.test.tsx: node.claim_rejected restores the node stashed grab-start position | COMPLIANT |
| Local Node Removed While Held Drops the Local Lock | A held node removed mid-drag drops the local lock | DiagramCanvas.test.tsx: removing the held class mid-drag does not crash, free still fires and the deferred sync flushes cleanly plus backend test_remove_class_on_a_held_node_does_not_strand_the_lock_or_error_on_release | COMPLIANT |

**Compliance summary**: 31/31 scenarios compliant (30 COMPLIANT, 1 PARTIAL, 0 UNTESTED). The prior single CRITICAL (TTL expiry UNTESTED) is now COMPLIANT with real runtime coverage; independently confirmed by reading both new tests and re-running the suite (10/10 in test_locks.py, 361/361 backend, 317/317 frontend).

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Lua compare-and-delete/compare-and-expire (DD3) | Implemented | locks.py uses string.match to extract the token before the first pipe before comparing - a documented, correct deviation from design literal pseudocode (stored value is token pipe label, not a bare token); confirmed by test_release_with_foreign_token_returns_false_and_leaves_the_key and test_refresh_with_foreign_token_returns_false |
| Per-message role gate (DD6) | Implemented | consumers.py receive_json re-resolves membership and calls require_role on every inbound message; connect() stays membership-only |
| owner_token never reaches a browser (DD9) | Implemented | node_locked/node_position handlers strip owner_token, emit only mine |
| SCAN not KEYS (DD10) | Implemented | locks.snapshot uses client.scan in a loop until cursor is 0 |
| TTL value and refresh cadence (DD4) | Implemented and now runtime-proven | LOCK_TTL_MS = 10_000 in locks.py; throttle constant 50ms in document.ts. Expiry behavior is now proven at runtime by test_abandoned_claim_expires_via_ttl_and_becomes_claimable_again (module-level LOCK_TTL_MS patched to 50ms, no code path change) and TTL-is-set is proven by test_claim_sets_a_ttl_close_to_lock_ttl_ms |
| UmlCommand union / dispatcher / documents.py zero diff (proposal Out of Scope) | Implemented | git diff --stat against these paths is empty |
| redis promoted to a direct dependency (DD1) | Implemented | backend/requirements/base.txt has redis constraint with a comment explaining the promotion |
| DECISIONS_LOG.md / CURRENT_STATE.md updated (tasks 7.2/7.3) | Implemented | Cycle 13 entries present in both files |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| DD1 (sync redis.Redis, lazy module pool) | Yes | |
| DD2 (key/value shape, SET NX PX) | Yes | now also directly proven via PTTL assertion |
| DD3 (Lua compare-and-delete/expire) | Yes (implementation detail corrected, same intent) | |
| DD4 (TTL 10s / throttle 50ms) | Yes | values match; runtime expiry behavior now proven |
| DD5 (two disjoint lock domains) | Yes | Redis locks never gate submit_command; row lock never consults Redis |
| DD6 (per-message role gate, connect unchanged) | Yes | |
| DD7 (disconnect releases self.held, no durable write) | Yes | |
| DD8 (save_layout_position sibling, prune plus early-return) | Yes | |
| DD9 (mine re-derived per connection, no token leak) | Yes | |
| DD10 (node.locks snapshot via SCAN on connect) | Yes | |
| DD11 (locks in React state, live positions via ref) | Yes | |
| DD12 (ungrabify/locked-remote, optimistic claim plus snap-back) | Yes | |
| DD13 (toElements seeding) | Yes | implemented with layout as an optional param (documented deviation, behavior-identical) |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | Yes | Full RED/GREEN table found in apply-progress for all 7 phases; remediation apply added its own RED/GREEN pair for the 2 new TTL tests |
| All tasks have tests | Yes | 22/22 tasks; every GREEN task has a preceding RED task with named test files |
| RED confirmed (tests exist) | Yes | test_locks.py (including the 2 new TTL tests), test_services.py additions, test_consumers.py additions, DiagramCanvas.test.tsx additions, document.test.ts additions, uml_documents.test.ts additions, page.test.tsx additions all exist |
| GREEN confirmed (tests pass) | Yes | 361/361 backend, 317/317 frontend pass on independent re-run (678 total) |
| Triangulation adequate | Yes | Multi-case coverage per behavior; the TTL fix adds two independent angles (TTL-is-set via PTTL, and TTL-causes-expiry via a patched short TTL plus sleep) rather than one shallow assertion |
| Safety Net for modified files | Yes | Full suites re-run clean after the remediation; zero production files touched (git diff --stat confirms locks.py is unchanged, a new untracked file with no diff since the prior verify run) |

**TDD Compliance**: 6/6 checks passed

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 14 | 2 (test_locks.py, test_services.py additions) | pytest |
| Integration | 7 | 1 (test_consumers.py additions) | pytest-django, WebsocketCommunicator, django_capture_on_commit_callbacks |
| Component/Unit (frontend) | 23 | 4 (DiagramCanvas.test.tsx, document.test.ts, uml_documents.test.ts, page.test.tsx additions) | Vitest, React Testing Library |
| E2E | 0 | 0 | not installed (deferred per config.yaml testing.e2e) |
| Total | 44 | 7 | |

### Assertion Quality
No tautologies, ghost loops, or assertion-free tests found across the modified/created test files, including the 2 new TTL tests: both assert real, varied production-code outcomes (PTTL bounds; blocked-then-expired-then-reclaimable state transitions), not smoke-only checks. One WARNING-level observation carried over from the prior run:

Assertion quality: 0 CRITICAL, 1 WARNING (see Issues Found, WARNING 1 - the simultaneous-claims test proves the outcome via sequential ordering rather than a genuine concurrent race, which understates triangulation for that one scenario; this was accepted as non-blocking in the prior verify run and remains non-blocking here).

### Quality Metrics
**Linter**: No errors (not re-run this pass; unaffected by a test-only remediation - see prior report exit 0)
**Type Checker**: No errors (npx tsc --noEmit, exit 0, independently re-run)

### Issues Found

**CRITICAL**:
None. The single prior CRITICAL - uml-node-locking's "An abandoned claim expires via TTL" scenario being UNTESTED at runtime - is resolved. test_abandoned_claim_expires_via_ttl_and_becomes_claimable_again patches the module-level LOCK_TTL_MS to 50ms (production code untouched), confirms a second claim is rejected before expiry, sleeps past the TTL, then confirms a fresh claim both succeeds and returns no prior owner label (full expiry, not just claimability). test_claim_sets_a_ttl_close_to_lock_ttl_ms independently confirms the TTL is actually set on claim via PTTL. Both were read directly (not just counted) and both pass at runtime (10/10 in test_locks.py, 361/361 full backend suite).

**WARNING** (carried over from the prior verify run, unchanged, still accepted as non-blocking):
1. uml-node-locking Scenario "Simultaneous claims resolve to exactly one owner" is proven only via sequential message order (test_second_claim_on_held_node_is_rejected sends A's claim, awaits its ack, then sends B's claim), not via a genuine two-thread race like test_submit_command_concurrent_calls_do_not_lose_updates uses for the Postgres row lock. The underlying primitive (SET NX) is atomic on a single-threaded Redis server, so the outcome is correct by construction, but "regardless of which message the server processed first" is not literally exercised at runtime.
2. apply-progress's self-reported test count ("test_consumers.py +8 across phase 3 and phase 7.1") is off by one against the actual diff - 6 new tests in the Phase 3 block plus 1 in Phase 7.1 equals 7, not 8. Cosmetic bookkeeping only; every scenario this change requires is still covered and passing. Unaffected by the remediation (test_consumers.py was not touched by it).

**SUGGESTION** (carried over from the prior verify run, unchanged, still accepted as non-blocking):
1. web-uml-canvas's "Claim Rejection Feedback" requirement is satisfied only by an implicit snap-back of the node to its pre-drag position (claimRejectedListenerRef); there is no explicit toast/message. This matches design.md DD12's own reasoning and Testing Strategy row verbatim, so it is not a deviation - flagging only as a UX note for a future cycle if user testing shows the snap-back alone reads as ambiguous.
2. docs/ai/DECISIONS_LOG.md's Cycle 13 entry documents the Lua token-extraction fix and the toElements optional-parameter deviation inline, which is good practice - no action needed, noted as a positive.

### Verdict
PASS WITH WARNINGS
22/22 tasks complete, 678/678 executed tests pass (361 backend + 317 frontend, including the 2 new TTL tests independently read and re-run), and every spec scenario is now behaviorally proven at runtime: 31/31 scenarios compliant (30 COMPLIANT, 1 PARTIAL), 0 CRITICAL, 2 WARNING (both pre-existing, non-blocking, unaffected by the remediation), 2 SUGGESTION (both pre-existing, non-blocking). The remediation apply is scoped exactly as described: 2 new tests added to test_locks.py, zero production files touched (confirmed independently via git status/diff - locks.py remains untracked with no changes since the prior verify run). Ready for sdd-archive.
