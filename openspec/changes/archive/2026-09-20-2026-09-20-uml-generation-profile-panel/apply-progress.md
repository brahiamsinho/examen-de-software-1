# Apply Progress: UML Generation Profile Panel

## Status

Applied in Strict TDD mode. OpenSpec store: `openspec`. Native status consumed: `gentle-ai.sdd-status` v2 for change `2026-09-20-uml-generation-profile-panel`, `nextRecommended: apply`, `applyState: ready`, `actionContext.mode: repo-local`, allowed edit root `C:\Users\brahi\OneDrive\Escritorio\Examen-1-Software`.

## Completed tasks and persisted checkbox updates

All implementation tasks 1-14 are completed and visibly checked in `openspec/changes/2026-09-20-uml-generation-profile-panel/tasks.md`.

## Files changed

- `frontend/src/lib/uml_documents.ts` — added `SetGenerationProfile` to `UmlCommandIn`; no REST implementation change.
- `frontend/src/lib/__tests__/uml_documents.test.ts` — added command forwarding coverage for `SetGenerationProfile`.
- `frontend/src/components/workspace/GenerationProfilePanel.tsx` — new presentational tri-state generation profile panel.
- `frontend/src/components/workspace/__tests__/GenerationProfilePanel.test.tsx` — new RTL coverage for target listing, selection, prefill, payloads, clear, success, and errors.
- `frontend/src/app/(app)/documents/[docId]/page.tsx` — mounted sidebar Card titled `Perfil de generación` after validation.
- `openspec/changes/2026-09-20-uml-generation-profile-panel/tasks.md` — checked tasks 1-14.
- `openspec/changes/2026-09-20-uml-generation-profile-panel/apply-progress.md` — this cumulative progress record.
- `docs/ai/CURRENT_STATE.md`, `docs/ai/HANDOFF_LATEST.md`, `docs/ai/NEXT_STEPS.md`, `docs/ai/DECISIONS_LOG.md`, and a session note were updated for project memory continuity.

## TDD Cycle Evidence

| Cycle | RED evidence | GREEN evidence | TRIANGULATE / REFACTOR evidence |
|---|---|---|---|
| Command type | Added `submitCommand forwards SetGenerationProfile verbatim as the JSON body`; focused run failed initially because the new panel component import did not yet exist while RED tests were present. | Added `SetGenerationProfile` union variant; focused command/panel test run later passed. | No REST helper changed; command is forwarded by the existing `submitCommand` path. |
| Panel structure | Added RTL tests for target options, class/attribute-only controls, empty disabled state, and selection replacement. | Created `GenerationProfilePanel.tsx` deriving targets from `classes` and rendering native `Select` tri-state controls. | Kept helpers local (`deriveTargets`, `isRecord`, payload mapping); no new dependencies or UI primitives. |
| Metadata prefill | Added tests for class profile, attribute profile, malformed metadata, and selection recomputation. | Implemented guarded metadata reads and `crud` full-array/empty-array mapping. | Malformed, partial, array, primitive, null, and missing metadata paths remain all unset. |
| Submission | Added tests for declared-only class/attribute payloads, `profile: null`, and `crud=true` full operation mapping without boolean `crud`. | Implemented declared-only payload builder and exact `SetGenerationProfile` dispatch. | Payload includes only visible declared controls and never sends raw boolean `crud`. |
| UX/errors | Added tests for success normalization, `ApiError.detail`, and generic unexpected error. | Implemented success/error handling while preserving rejected form values. | Refactored state to avoid lint-forbidden synchronous effect state updates. |
| Sidebar mount | No existing page-level sidebar test was identified; component coverage serves as the RED evidence for the integration boundary per task 11. | Mounted the `Perfil de generación` Card in `page.tsx` after `ValidationPanel` and before `Agregar`. | No backend, persistence, canvas, WebSocket, Flutter, or `defaultSort` files changed. |

## Test commands run

- `cd frontend && npm test -- --run src/lib/__tests__/uml_documents.test.ts src/components/workspace/__tests__/GenerationProfilePanel.test.tsx` — initial RED run failed as expected while the new component did not exist; existing lib tests passed.
- `cd frontend && npm test -- --run src/lib/__tests__/uml_documents.test.ts src/components/workspace/__tests__/GenerationProfilePanel.test.tsx` — passed, 2 files / 39 tests.
- `cd frontend && npm test` — passed, 55 files / 351 tests.
- `cd frontend && npm run lint` — first run failed on `react-hooks/set-state-in-effect`; refactored component state.
- `cd frontend && npm test -- --run src/components/workspace/__tests__/GenerationProfilePanel.test.tsx` — passed, 15 tests after refactor.
- `cd frontend && npm run lint` — passed.
- `cd frontend && npm test` — passed, 55 files / 351 tests.

## Deviations from design

- No page-level test was added because no existing page-level sidebar test was identified; task 11 explicitly allowed documenting component coverage as sufficient.
- Final authored frontend line count remains over the 400-line review budget because the approved scope includes focused RTL coverage; user accepted the size exception for 430-560 lines.

## Remaining tasks

None. There are no unchecked implementation task lines in `tasks.md`.

## Workload / PR boundary

Delivery proceeded as a single size-exception frontend slice per user instruction. Approximate new component + panel test size is 510 lines before small modified-file additions; this exceeded the nominal 400-line review budget because tests are the bulk of the change.

## Action context warnings

- `.pi/` remains untracked and must not be committed.
- No backend, persistence, canvas, WebSocket, Flutter/mobile, or `defaultSort` behavior was modified.
- No commit or push was performed.
