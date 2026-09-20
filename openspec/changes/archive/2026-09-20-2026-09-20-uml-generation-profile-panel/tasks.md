# Tasks: UML Generation Profile Panel

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 430-560 additions/deletions |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: command type + REST forwarding test → PR 2: GenerationProfilePanel component + component tests → PR 3: sidebar Card mount + focused integration check |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

The change is frontend-only, but the new panel plus RTL coverage is likely to exceed the 400-line review budget. Under `ask-on-risk`, pause before apply to choose chained PRs or explicitly accept a size exception.

## Implementation Tasks

- [x] 1. RED — Add the command-forwarding failing test in `frontend/src/lib/__tests__/uml_documents.test.ts` for `submitCommand forwards SetGenerationProfile verbatim as the JSON body`, using `{ type: "SetGenerationProfile", element_id: "c1", profile: { readOnly: true } }`, then run `cd frontend && npm test -- --runInBand` or the closest supported Vitest command and confirm the failure is caused by the missing `UmlCommandIn` variant/type acceptance.

- [x] 2. GREEN — Extend `UmlCommandIn` in `frontend/src/lib/uml_documents.ts` with `{ type: "SetGenerationProfile"; element_id: string; profile: Record<string, unknown> | null }` without changing `submitCommand`, backend URLs, persistence behavior, or any other command shape; rerun `cd frontend && npm test -- --runInBand` or `cd frontend && npm test` and confirm the lib test passes.

- [x] 3. RED — Create `frontend/src/components/workspace/__tests__/GenerationProfilePanel.test.tsx` with failing RTL tests for rendering class and attribute target options, class-only controls (`auditable`, `readOnly`, `crud`), attribute-only controls (`searchable`, `sortable`, `readOnly`), no-target empty/disabled state, and element selection state changes that replace visible controls when switching targets.

- [x] 4. GREEN — Create `frontend/src/components/workspace/GenerationProfilePanel.tsx` as a presentational component that derives class/attribute targets from `classes`, uses the existing `frontend/src/components/ui/select.tsx` tri-state selects with `unset | true | false`, disables submit when there is no valid selected target, and passes the tests from task 3.

- [x] 5. TRIANGULATE — Add failing tests in `GenerationProfilePanel.test.tsx` for safe prefill from `generationMetadata[elementId].profile`: class profile `{ auditable: true, readOnly: false, crud: ["create", "read", "update", "delete"] }`, attribute profile `{ searchable: true, sortable: false, readOnly: true }`, selection changes recomputing from the newly selected element, and malformed/missing/null/array/primitive metadata pre-filling as all unset without crashing.

- [x] 6. GREEN — Implement guarded metadata readers in `GenerationProfilePanel.tsx` so only non-null object `profile` values are consumed, boolean controls map only real booleans, `crud` maps full CRUD arrays to true and empty arrays to false, and all malformed or partial values remain unset; rerun the focused component tests.

- [x] 7. TRIANGULATE — Add failing submit tests in `GenerationProfilePanel.test.tsx` for declared-only class payloads, declared-only attribute payloads, all-unset `profile: null` clear behavior, `crud=true` mapping to `["create", "read", "update", "delete"]`, and a guard that no raw boolean `crud` is sent.

- [x] 8. GREEN — Implement submit payload construction in `GenerationProfilePanel.tsx` so it resolves the current selected target from the derived target list, dispatches exactly one `SetGenerationProfile` through `onSubmit`, includes only declared controls, sends `profile: null` when all visible controls are unset, and respects the backend CRUD vocabulary.

- [x] 9. TRIANGULATE — Add failing tests in `GenerationProfilePanel.test.tsx` for success and error UX: successful submit keeps the selected element selected and normalizes visible controls to the submitted values; rejected submit with `new ApiError({ status: 422, code: "invalid_command_payload", detail: "..." })` displays the backend detail; non-`ApiError` rejection displays `Ocurrió un error inesperado. Intenta de nuevo.` while keeping the form mounted.

- [x] 10. GREEN — Implement submit success/error state handling in `GenerationProfilePanel.tsx` using `ApiError` from `frontend/src/lib/api.ts`, preserving current form values on rejection and clearing old errors on success; rerun `cd frontend && npm test`.

- [x] 11. RED — Add a focused failing sidebar mount assertion to an existing page-level test if one already covers `frontend/src/app/(app)/documents/[docId]/page.tsx`; otherwise document that component coverage is sufficient and use the existing component tests as the RED evidence for the sidebar integration boundary.

- [x] 12. GREEN — Modify `frontend/src/app/(app)/documents/[docId]/page.tsx` to import `GenerationProfilePanel` and add one `Card` titled `Perfil de generación` after `ValidationPanel` and before the `Agregar` group, passing `classes={document.model.classes}`, `generationMetadata={document.model.generation_metadata}`, `onSubmit={submitCommand}`, and `disabled={isSubmitting}`.

- [x] 13. REFACTOR — Review `GenerationProfilePanel.tsx` for small reusable helpers only where they reduce duplication (`isRecord`, target derivation, tri-state-to-payload mapping), keep helper scope local unless shared usage emerges, ensure labels remain Spanish and accessible through `<Label htmlFor=...>`, and avoid adding new dependencies or custom UI primitives.

- [x] 14. REFACTOR — Run final checks with `cd frontend && npm test` and `cd frontend && npm run lint`; if line count remains over 400 changed lines, keep the work split according to the forecast or pause for explicit `size:exception` acceptance before a single PR.
