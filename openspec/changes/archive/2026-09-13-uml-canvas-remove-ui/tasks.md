# Tasks: UML Canvas Remove UI

Strict TDD. Frontend-only; `backend/` stays untouched.

Test command: `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/components/workspace/__tests__/RemoveClassControl.test.tsx src/components/workspace/__tests__/RemoveAttributeControl.test.tsx src/components/workspace/__tests__/RemoveRelationshipControl.test.tsx "src/app/(app)/documents/[docId]/__tests__/page.test.tsx"`
Full regression: `cd frontend && npm test`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~600-750 (3 controls ~250, 3 test suites ~260, `uml_documents.ts`+test ~30, `page.tsx` ~25, docs ~65) |
| 800-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR — estimate fits the session's 800-line budget |
| Delivery strategy | single-pr |
| Chain strategy | pending (not needed) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
800-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Remove-class/attribute/relationship UI, end to end | PR 1 | `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/components/workspace/__tests__/Remove*.test.tsx "src/app/(app)/documents/[docId]/__tests__/page.test.tsx"` | `cd frontend && npm run dev` + manual open-document -> remove-attribute -> remove-relationship -> remove-class round trip | `git revert`, or delete the 3 new components/tests and drop their JSX plus the 3 union members (proposal §Rollback Plan) |

## Phase 1: Command Union (`lib/uml_documents.ts`)

- [x] 1.1 RED: extend `frontend/src/lib/__tests__/uml_documents.test.ts` — `submitCommand` forwards each of `RemoveClass`/`RemoveAttribute`/`RemoveRelationship` verbatim as the JSON body (DD1 field names).
- [x] 1.2 GREEN: modify `frontend/src/lib/uml_documents.ts` — add the 3 `UmlCommandIn` members; replace the stale "only three commands" comment (DD1).

## Phase 2: Remove Class (`RemoveClassControl.tsx`)

- [x] 2.1 RED: create `frontend/src/components/workspace/__tests__/RemoveClassControl.test.tsx` — cascade count from source-or-target filter; no submit until confirmed; `Confirmar` submits `RemoveClass` once; zero-relationship class still requires confirmation; `Cancelar` returns to select with zero calls; stale-selection `rerender` collapses to `""` and disables submit [Remove Class Command — all scenarios; Stale Selection Reset].
- [x] 2.2 GREEN: create `frontend/src/components/workspace/RemoveClassControl.tsx` — select + confirm branch (DD2/DD3/DD4/DD5).

## Phase 3: Remove Attribute (`RemoveAttributeControl.tsx`)

- [x] 3.1 RED: create `frontend/src/components/workspace/__tests__/RemoveAttributeControl.test.tsx` — attribute select scoped to chosen class; changing class clears attribute; immediate submit with no confirmation; class disappearing after refetch resets both selects without crashing [Remove Attribute Command; Stale Selection Reset].
- [x] 3.2 GREEN: create `frontend/src/components/workspace/RemoveAttributeControl.tsx` (DD2/DD3).

## Phase 4: Remove Relationship (`RemoveRelationshipControl.tsx`)

> **Resolved spec/design conflict:** the spec originally said option labels were built via `formatMultiplicity` (mirroring the canvas edge label). That was a genuine spec defect — multiplicity alone cannot disambiguate two relationships between the same class pair, which design DD6 correctly identified. `spec.md`'s Remove Relationship Command requirement was corrected to the endpoint-name-plus-kind format DD6 always specified; no product decision was needed since there was no real tradeoff.

- [x] 4.1 RED: create `frontend/src/components/workspace/__tests__/RemoveRelationshipControl.test.tsx` — option label is `name(source) → name(target) (kind)` (DD6); a dangling relationship still lists using its raw `class_id` fallback; immediate submit with no confirmation; selected relationship cascade-removed elsewhere resets selection on refetch [Remove Relationship Command; Stale Selection Reset].
- [x] 4.2 GREEN: create `frontend/src/components/workspace/RemoveRelationshipControl.tsx` (DD2/DD6).

## Phase 5: Container Wiring (`page.tsx`)

- [x] 5.1 RED: extend `frontend/src/app/(app)/documents/[docId]/__tests__/page.test.tsx` — renders the 3 controls under an "Eliminar" heading, in class/attribute/relationship order, after the existing `Add*` block (DD7).
- [x] 5.2 GREEN: modify `frontend/src/app/(app)/documents/[docId]/page.tsx` — render `RemoveClassControl`/`RemoveAttributeControl`/`RemoveRelationshipControl` wired to `submitCommand` (DD7).

## Phase 6: Documentation (`config.yaml` `rules.design`/`rules.apply`)

- [x] 6.1 Append DD1–DD8 to `docs/ai/DECISIONS_LOG.md`, one entry per decision with rationale, following the existing entry format.
- [x] 6.2 Update `docs/ai/CURRENT_STATE.md` — note the UML canvas now supports removal (6 of 7 command shapes wired; only `RenameClass` remains).

## Phase 7: Verification

- [x] 7.1 Run `cd frontend && npm test`; confirm all 4 modified/added requirements' scenarios pass with zero regressions.
- [x] 7.2 Run `cd frontend && npm run lint`; confirm zero new warnings.
- [x] 7.3 Confirm `backend/` has zero diff: `git diff --stat -- backend` returns empty.

## Phase 8: Post-Verify Remediation (verify-report.md WARNING 3)

- [x] 8.1 RED/GREEN: `state/document.ts` `useDocument` — added a shared
  `isSubmitting` boolean, set `true` before `submitCommand`'s POST starts and
  cleared in a `finally` (success or rejection path), so every
  command-submitting control can share one cross-control lock instead of
  relying only on its own local `submitting` state. Without this, two
  commands fired from two different controls in close succession could apply
  both server-side while their two `getDocument` refetches resolved in
  either order, leaving the render transiently reflecting only one command's
  effect. Regression tests in `document.test.ts` (pending → resolved and
  pending → rejected). [WARNING 3]
- [x] 8.2 GREEN: `documents/[docId]/page.tsx` — destructures `isSubmitting`
  from `useDocument` and passes it as `disabled` to all 6
  command-submitting controls (`AddClassForm`, `AddAttributeForm`,
  `AddRelationshipControl`, `RemoveClassControl`, `RemoveAttributeControl`,
  `RemoveRelationshipControl`). Regression test in `page.test.tsx` asserts
  all 6 submit buttons render disabled when `isSubmitting: true`. [WARNING 3]
- [x] 8.3 GREEN: each of the 6 controls above gained an optional
  `disabled?: boolean` prop, defaulted to `false` and OR'd into its existing
  submit-button `disabled` condition, preserving each control's own
  `submitting`/selection-gating logic. [WARNING 3]
- [x] 8.4 Verification: `cd frontend && npm test` (235/235 passed),
  `cd frontend && npm run lint` (zero warnings), and
  `cd frontend && npm run build` (TypeScript + build succeed). Confirmed
  `git diff --stat -- backend` is empty.

## Deferred (out of scope this cycle)

- `AddAttributeForm`'s `useState(classes[0]?.id ?? "")` shares DD2's staleness bug; not touched here (design Open Questions).
- `useCommandSubmit` extraction for the now 6 duplicated error/submitting blocks (DD8); logged as tech debt.
