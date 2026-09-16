# Proposal: UML Relationship Kinds

## Intent

The canvas can only draw associations. `AddRelationshipControl` hardcodes
`kind: "association"` and the `AddRelationship` command type narrows `kind`
to that single literal, so aggregation, composition, and generalization are
unreachable from the UI even though the backend, domain model, and
validation already accept all four UML 2.5 kinds end-to-end. Every edge also
renders with the same triangle head, so kind would be invisible even if it
were submitted. This cycle closes the gap with an empty `backend/` diff.

## Scope

### In Scope

- Widen the `AddRelationship` command's `kind` to the existing
  `RelationshipKind` union at both hardcode sites (`uml_documents.ts:126`,
  `AddRelationshipControl.tsx:93`) — they must change together.
- Add a kind `<Select>` to `AddRelationshipControl` and submit the chosen
  kind.
- Hide the source/target multiplicity `<Select>`s entirely when kind is
  `generalization` (confirmed decision; UML 2.5 has no multiplicity there).
- Propagate `relationship.kind` into Cytoscape edge `data` in `toElements()`.
- Per-kind edge styling: hollow triangle (generalization), hollow diamond
  (aggregation), filled diamond (composition), plain line (association).
- `web-uml-canvas` delta for the "Add Relationship Command" requirement.

### Out of Scope

- Any backend, schema, or validation change — all four kinds already work.
- `openspec/specs/uml-domain-model/spec.md` — already states the 4-kind enum.
- `RemoveRelationshipControl` — already kind-agnostic.
- Editing the kind of an existing relationship; role names; navigability;
  qualified or n-ary associations.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-uml-canvas`: the Add Relationship Command requirement gains kind
  selection, the generalization multiplicity exception, and per-kind edge
  notation.

## Approach

Exploration's Approach 1. Both confirmed decisions are fixed inputs:
first click (`source`) is the "whole" for aggregation/composition, and
generalization multiplicity selects are not rendered. Diamond markers use
`source-arrow-shape: diamond` with `source-arrow-fill` hollow/filled,
keyed off the new `kind` data field; the current blanket `target-arrow-shape:
"triangle"` on the generic `edge` selector must be scoped per kind.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/src/lib/uml_documents.ts` | Modified | `kind` widened to `RelationshipKind` |
| `frontend/src/components/workspace/AddRelationshipControl.tsx` | Modified | Kind select; conditional multiplicities |
| `frontend/src/components/workspace/DiagramCanvas.tsx` | Modified | `kind` in edge data; per-kind `STYLE` |
| `.../__tests__/{AddRelationshipControl,DiagramCanvas}.test.tsx` | Modified | Updated + new per-kind cases |
| `backend/` | None | Already wired |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Only one hardcode site changed → TS silently keeps `"association"` | Med | Spec/tasks pin both sites as one unit |
| Scoping the generic `edge` selector regresses association or `edge.self-loop` geometry | Med | Flag for sdd-design: keep `edge.self-loop` untouched; assert plain association has no terminator |
| Existing tests assert `kind: "association"` — edits, not additions, under Strict TDD | High | Tasks sequence RED updates before implementation |

## Rollback Plan

Three edited frontend files plus tests; `git revert`. Reverting restores the
narrow literal, which fails compilation at any leftover call site — a loud,
not silent, rollback signal.

## Dependencies

None new.

## Success Criteria

- [ ] A user can pick any of the four kinds and the submitted command carries it.
- [ ] Generalization shows no multiplicity selects.
- [ ] Each kind renders its UML 2.5 terminator; association stays a plain line.
- [ ] Aggregation/composition diamonds sit at the first-clicked (`source`) end.
- [ ] Self-loop geometry is unchanged; `backend/` diff is empty.
