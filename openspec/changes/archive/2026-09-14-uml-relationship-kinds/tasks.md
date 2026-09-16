# Tasks: UML Relationship Kinds

Strict TDD. Frontend-only; `backend/` stays at zero diff (verified at
`schemas.py:59`).

Test command: `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/components/workspace/__tests__/AddRelationshipControl.test.tsx src/components/workspace/__tests__/DiagramCanvas.test.tsx`
Full regression: `cd frontend && npm test`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~300-420 (type widen ~10, Control ~50, Control tests ~130, Canvas ~40, Canvas tests ~100, docs ~50) |
| 800-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR — well under the session's 800-line budget |
| Delivery strategy | single-pr |
| Chain strategy | pending (not needed) |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
800-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Kind selection + per-kind UML 2.5 edge notation, end to end | PR 1 | `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/components/workspace/__tests__/AddRelationshipControl.test.tsx src/components/workspace/__tests__/DiagramCanvas.test.tsx` | `cd frontend && npm run dev` + manual: add one relationship of each kind, confirm terminator/diamond notation and a self-loop generalization | `git revert`; reverting restores the narrow `"association"` literal, which fails compilation at any leftover call site (proposal §Rollback Plan) |

## Phase 1: Command Type (`lib/uml_documents.ts`)

- [x] 1.1 Modify `frontend/src/lib/uml_documents.ts` — widen `AddRelationship.relationship.kind` from the `"association"` literal to `RelationshipKind` (line ~126). Type-only change, exercised by Phase 2/3 tests. (No adjacent comment needed — none existed on this field before or after.)

## Phase 2: Add Relationship Control (`AddRelationshipControl.tsx`)

- [x] 2.1 RED: in `frontend/src/components/workspace/__tests__/AddRelationshipControl.test.tsx`, rename the existing `kind: "association"` case at line ~110 to document it as the *default*-kind case (title/docblock only, no assertion change).
- [x] 2.2 RED: add — kind `<Select>` renders all 4 `RelationshipKind` options and defaults to `association`.
- [x] 2.3 RED: add — parametrized over all 4 kinds: choosing kind X and confirming calls `onSubmit` with `relationship.kind: X`.
- [x] 2.4 RED: add — selecting `generalization` renders neither `Multiplicidad origen` nor `Multiplicidad destino`.
- [x] 2.5 RED: add — `generalization` after choosing `0..*` on a multiplicity, then switching to `generalization`, still submits `"1"`/`"1"` (DD5, forced literal).
- [x] 2.6 RED: add — `generalization` then back to `association` still shows the earlier `0..*` selection (no reset on kind change, DD5).
- [x] 2.7 GREEN: modify `frontend/src/components/workspace/AddRelationshipControl.tsx` — add `useState<RelationshipKind>("association")` and a `Tipo de relación` `<Select>` (`Asociación`/`Agregación`/`Composición`/`Generalización`) rendered only in the both-ids-set confirm branch, above the multiplicity grid (DD4); conditionally hide both multiplicity `<Select>`s when kind is `generalization`; `handleSubmit` derives the payload — sends `"1"`/`"1"` for generalization regardless of hidden state, otherwise the selected multiplicities (DD5). No prop change to `AddRelationshipControlProps`.

## Phase 3: Diagram Canvas (`DiagramCanvas.tsx`)

- [x] 3.1 RED: in `frontend/src/components/workspace/__tests__/DiagramCanvas.test.tsx`, extend the `toMatchObject` assertion at line ~65 with `kind: "association"` to pin propagation.
- [x] 3.2 RED: add — parametrized `toElements` case: `edge.data.kind` equals each of the 4 `RelationshipKind` values.
- [x] 3.3 RED: add — self-referencing `generalization` relationship: `edge.classes === "self-loop"` **and** `edge.data.kind === "generalization"` (DD3 composition guard).
- [x] 3.4 RED: add — the generic `edge` `STYLE` entry declares **no** `target-arrow-shape` key (association stays plain, DD2).
- [x] 3.5 RED: add — each of the 3 kind selectors (`generalization`, `aggregation`, `composition`) declares exactly its terminator shape + fill, and **no** kind selector declares any `loop-*`/`control-point-step-size`/`text-margin-y` key (DD3).
- [x] 3.6 RED: add — the `edge.self-loop` `STYLE` entry still carries its four prior-cycle properties unchanged (regression guard).
- [x] 3.7 GREEN: modify `frontend/src/components/workspace/DiagramCanvas.tsx` — `toElements()` copies `r.kind` into edge `data` (`classes` expression stays byte-identical); delete `"target-arrow-shape": "triangle"` from the generic `edge` selector and add `"source-arrow-color": EDGE_LINE` beside the existing `target-arrow-color` (DD2); append 3 kind rules to the end of `STYLE`, after `edge.self-loop` — `generalization` (hollow triangle, `arrow-scale: 1.6`), `aggregation` (hollow diamond on `source`), `composition` (filled diamond on `source`) (DD1/DD3); export `STYLE` (DD6).

## Phase 3b: Verify-Report Fix — Multiplicity Label on Generalization (CRITICAL)

- [x] 3.8 Found by `sdd-verify`: `toElements()`'s edge `label` was built
      unconditionally from `formatMultiplicity()` on both endpoints, with no
      `kind` branch, so a generalization edge rendered `"1 → 1"` on the
      canvas — contradicting the spec's "no multiplicity labels at either
      end" for generalization and the UML 2.5 notation researched in
      `exploration.md`. Fixed: `label` is now `""` when
      `r.kind === "generalization"`, unchanged for the other 3 kinds. Added
      a regression test (`DiagramCanvas.test.tsx`, "omits the multiplicity
      label for a generalization edge"). Re-ran `npm test`
      (279/279), `npm run lint` (clean), `npm run build` (clean).

## Phase 4: Documentation (`config.yaml` `rules.design`)

- [x] 4.1 Append DD1–DD6 to `docs/ai/DECISIONS_LOG.md`, one entry per decision with rationale, following the existing entry format.
- [x] 4.2 Update `docs/ai/CURRENT_STATE.md` — note the canvas now supports all 4 UML 2.5 relationship kinds with per-kind notation, not just association.

## Phase 5: Verification

- [x] 5.1 Run `cd frontend && npm test`; confirm all Add Relationship Command scenarios pass with zero regressions, including the untouched self-loop and `RemoveRelationshipControl` suites. — 279/279 passed (278 + the 3.8 regression test).
- [x] 5.2 Run `cd frontend && npm run lint`; confirm zero new warnings. — zero output, zero warnings.
- [x] 5.3 Run `cd frontend && npm run build`; confirm TypeScript and build succeed. — compiled + typechecked successfully.
- [x] 5.4 Confirm `backend/` has zero diff: `git diff --stat -- backend` returns empty. — confirmed empty.
