# Delta for Web UML Canvas

## MODIFIED Requirements

### Requirement: Add Relationship Command

Adding a relationship MUST use click-click: clicking a source class node,
then a target class node, then confirming. `AddRelationshipControl` MUST
render a kind `<Select>` offering the four `RelationshipKind` values
(`association`, `aggregation`, `composition`, `generalization`). Confirming
MUST submit one `AddRelationship` command carrying the selected `kind`,
`source`, and `target`, followed by a refetch.

For `kind: "generalization"`, the control MUST NOT render the source or
target multiplicity `<Select>`s at all (UML 2.5 defines no multiplicity on
generalization). For `kind: "aggregation"` or `kind: "composition"`, the
first-clicked class (submitted as `source`) is the "whole" end; this is a UI
convention only and MUST NOT be enforced by client-side validation.

The canvas MUST render each relationship's edge using UML 2.5 notation keyed
off `relationship.kind`: `generalization` renders a hollow (unfilled)
triangle at the target (parent) end and no multiplicity labels at either
end; `aggregation` renders a hollow (unfilled) diamond at the source (whole)
end; `composition` renders a filled (solid) diamond at the source (whole)
end; `association` renders a plain line with no terminator at either end,
exactly as today. Self-referencing relationships (source equals target), of
any kind, MUST continue to use the existing self-loop geometry
(`edge.self-loop`), which per-kind terminator styling MUST NOT regress.

(Previously: click-click submitted one `AddRelationship` command hardcoded
to kind `association`, with no kind selection, unconditional multiplicity
selects, and a single unconditional triangle-head edge style applied to
every relationship regardless of kind.)

#### Scenario: Click-click creates an association with a plain line

- GIVEN two class nodes are visible and kind `association` is selected
- WHEN the user clicks source, then target, then confirms
- THEN an `association` `AddRelationship` is submitted and, after refetch,
  the new edge renders as a plain line with no terminator at either end

#### Scenario: Selecting aggregation submits the whole/part command

- GIVEN two class nodes A and B are visible and kind `aggregation` is
  selected
- WHEN the user clicks A, then B, then confirms
- THEN an `aggregation` `AddRelationship` is submitted with `source: A` and
  `target: B`, and the rendered edge shows a hollow diamond at A's end

#### Scenario: Selecting composition submits the whole/part command

- GIVEN two class nodes A and B are visible and kind `composition` is
  selected
- WHEN the user clicks A, then B, then confirms
- THEN a `composition` `AddRelationship` is submitted with `source: A` and
  `target: B`, and the rendered edge shows a filled diamond at A's end

#### Scenario: Selecting generalization hides multiplicity selects

- GIVEN two class nodes are visible and both have been clicked
- WHEN the user selects kind `generalization`
- THEN no source or target multiplicity `<Select>` renders, and confirming
  submits a `generalization` `AddRelationship` (the backend's
  `RelationshipEndIn.multiplicity` is a required string, so the command
  still carries a placeholder value on the wire; no multiplicity label
  renders on the canvas for this edge, per the next scenario)

#### Scenario: Generalization renders a hollow triangle at the parent end

- GIVEN a `generalization` relationship from child class A to parent class B
- WHEN the canvas renders the edge
- THEN a hollow triangle appears at B's (target) end and no multiplicity
  label renders at either end

#### Scenario: Self-loop geometry is unaffected by kind styling

- GIVEN a relationship whose source and target are the same class, of any
  of the four kinds
- WHEN the canvas renders the edge
- THEN it uses the existing self-loop geometry, and the kind's terminator
  (triangle, hollow diamond, filled diamond, or plain line) applies without
  breaking that loop shape
