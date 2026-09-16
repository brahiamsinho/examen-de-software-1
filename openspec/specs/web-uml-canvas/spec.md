# Web UML Canvas Specification

## Purpose

Let an org member open a UML document, view classes/relationships on a
Cytoscape canvas, and mutate it (add class, attribute, association) through
the command bus, with non-blocking validation feedback. Auth is inherited
from `(app)/layout.tsx`'s guard; not re-specified here.

## Requirements

### Requirement: Document Page Load

`app/(app)/documents/[docId]/page.tsx` MUST load the document at `docId`,
scoped to the organization in `activeOrgSlugAtom`. It MUST render a
not-found state, not a crash, on a backend 404 (including the cross-tenant
case, per `uml-document-persistence`'s `GET` 404 semantics).

#### Scenario: Successful load renders the document

- GIVEN an active organization and a document id belonging to it
- WHEN the document page loads
- THEN it displays the document's classes, attributes, and relationships

#### Scenario: Cross-tenant or missing document shows not-found

- GIVEN a document id that does not resolve under the active organization
- WHEN the page loads and the API returns 404
- THEN a not-found state renders instead of a crash or blank screen

### Requirement: Create-Document Entry Point

The dashboard MUST show a "New Diagram" entry point inside a header row
that also contains a "Mis Diagramas" heading, positioned above the document
list, and only when an active organization exists. Submitting a name MUST
call `POST /documents` and navigate to the new document's page on success.
(Previously: the entry point rendered standalone, with no header row, no
heading, and no document list to sit above.)

#### Scenario: Entry point hidden without an active organization

- GIVEN no active organization is selected
- WHEN the dashboard renders
- THEN no "New Diagram" entry point is shown

#### Scenario: Creating a document navigates to its page

- GIVEN an active organization exists
- WHEN the user submits a name through the entry point
- THEN `POST /documents` is called and the user is navigated to the new page

#### Scenario: Entry point renders in the header, above the list

- GIVEN an active organization exists
- WHEN the dashboard renders
- THEN the "New Diagram" entry point appears in the same header row as the
  "Mis Diagramas" heading, positioned above the document list
### Requirement: Diagram Rendering

The canvas MUST render each class as a node listing its attributes, each
relationship as an edge, and MUST apply `fcose` auto-layout on load.

#### Scenario: Classes and relationships render as nodes and edges

- GIVEN a document with two attributed classes and one relationship
- WHEN the canvas renders
- THEN both classes appear as nodes with attributes, linked by one edge

#### Scenario: Auto-layout runs on load

- GIVEN a document with no persisted positions
- WHEN the canvas mounts
- THEN `fcose` layout runs and every node has a computed position

### Requirement: Add Class Command

Submitting the add-class form MUST send an `AddClass` command, refetch the
document, and the canvas MUST reflect the new class node.

#### Scenario: New class appears after submission

- GIVEN an open document
- WHEN the user submits a class name through the add-class form
- THEN `AddClass` is submitted, the document refetched, and the class shown

### Requirement: Add Attribute Command

The add-attribute form MUST offer only the eight primitive types (`String`,
`Text`, `Integer`, `Long`, `Decimal`, `Boolean`, `Date`, `DateTime`) and MUST
NOT offer an enumeration-reference option. Submission MUST send an
`AddAttribute` command for the selected class, then refetch.

#### Scenario: Attribute is added to a class

- GIVEN a class exists on the canvas
- WHEN the user submits a primitive-typed attribute for that class
- THEN `AddAttribute` is submitted, refetched, and the class lists it

#### Scenario: Enumeration types are not offered

- GIVEN the add-attribute form is open
- WHEN the user views the type options
- THEN only the eight primitives are selectable; no enumeration option exists

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
### Requirement: Non-Blocking Validation Panel

The validation panel MUST render every violation from
`CommandResultOut.validation.violations` (severity, code, message, path) and
MUST NOT block further editing regardless of severity.

#### Scenario: Violations render without blocking edits

- GIVEN a command response with one or more violations
- WHEN the response is received
- THEN the panel lists each violation's fields, and all forms stay usable

### Requirement: Graceful Handling of Malformed Command Responses

If a command submission returns an unexpected shape (including a `422
invalid_command_payload` error), the UI MUST show an error state, not crash,
and MUST keep the previously loaded document on screen.

#### Scenario: Malformed response degrades gracefully

- GIVEN a response that does not match the `CommandResultOut` shape
- WHEN the UI processes it
- THEN an error message shows instead of a crash, and the loaded document
  stays visible and usable
### Requirement: Remove Class Command

`RemoveClassControl` MUST offer a class `<select>` and, before submission,
MUST show a confirmation step stating the exact number of relationships
that will cascade-remove, computed client-side as
`relationships.filter(r => r.source.class_id === id || r.target.class_id === id).length`
over `document.model.relationships`. The control MUST NOT submit
`RemoveClass` until the user confirms. On confirmation it MUST submit
`RemoveClass` for the selected class, then refetch the document.

#### Scenario: Confirmation states the exact cascade count

- GIVEN a class with two relationships referencing it as source or target
- WHEN the user selects that class in `RemoveClassControl`
- THEN the confirmation step states exactly 2 relationships will be removed

#### Scenario: Submission is blocked until confirmed

- GIVEN a class is selected and the confirmation step is showing
- WHEN the user has not yet confirmed
- THEN `RemoveClass` is not submitted

#### Scenario: Confirmed removal submits and refetches

- GIVEN a class is selected and the cascade count is shown
- WHEN the user confirms
- THEN `RemoveClass` is submitted for that class and the document is refetched

#### Scenario: Class with no relationships still requires confirmation

- GIVEN a class referenced by zero relationships
- WHEN the user selects that class
- THEN the confirmation step omits the cascade-count line (no relationship
  will be removed) but still requires explicit confirmation before
  `RemoveClass` is submitted

### Requirement: Remove Attribute Command

`RemoveAttributeControl` MUST offer a class `<select>` followed by an
attribute `<select>` scoped to the chosen class's attributes. Submission
MUST send `RemoveAttribute` for the selected class and attribute
immediately, with no confirmation step, then refetch the document.

#### Scenario: Selecting a class populates its attributes

- GIVEN a class with two attributes
- WHEN the user selects that class in `RemoveAttributeControl`
- THEN the attribute `<select>` lists exactly that class's two attributes

#### Scenario: Submission removes immediately without confirmation

- GIVEN a class and one of its attributes are selected
- WHEN the user submits
- THEN `RemoveAttribute` is submitted immediately and the document is
  refetched, with no confirmation step shown

### Requirement: Remove Relationship Command

`RemoveRelationshipControl` MUST offer a relationship `<select>` whose
option labels identify the relationship by its endpoint class names and
kind (`"{sourceName} → {targetName} ({kind})"`, falling back to the raw
class id when a name cannot be resolved), NOT by multiplicity alone —
multiplicity does not disambiguate two relationships between the same
class pair. Submission MUST send `RemoveRelationship` for the selected
relationship immediately, with no confirmation step, then refetch the
document.

#### Scenario: Relationship options are labelled by endpoint names and kind

- GIVEN a relationship of kind `association` from class `Cliente` to
  class `Pedido`
- WHEN `RemoveRelationshipControl` renders its options
- THEN the option label reads "Cliente → Pedido (association)"

#### Scenario: Two relationships between the same classes remain distinguishable

- GIVEN two distinct relationships both linking `Cliente` and `Pedido`
- WHEN `RemoveRelationshipControl` renders its options
- THEN each relationship still appears as its own selectable option

#### Scenario: Submission removes immediately without confirmation

- GIVEN a relationship is selected
- WHEN the user submits
- THEN `RemoveRelationship` is submitted immediately and the document is
  refetched, with no confirmation step shown

### Requirement: Stale Selection Reset After Refetch

Each of `RemoveClassControl`, `RemoveAttributeControl`, and
`RemoveRelationshipControl` MUST NOT crash or submit a stale id when the
document is refetched and the previously selected class, attribute, or
relationship no longer exists (including as a side effect of another
control's cascade removal). Each `<select>` MUST exclude ids absent from
the current document and MUST reset its selection to unset when its
previously selected id disappears.

#### Scenario: Selected relationship is cascade-removed by a class removal

- GIVEN a relationship is selected in `RemoveRelationshipControl`
- WHEN a `RemoveClass` submission elsewhere cascades that relationship away
  and the document refetches
- THEN `RemoveRelationshipControl` resets its selection and does not offer
  or submit the removed relationship id

#### Scenario: Selected class disappears after refetch

- GIVEN a class is selected in `RemoveAttributeControl`
- WHEN that class is removed elsewhere and the document refetches
- THEN `RemoveAttributeControl` resets its class and attribute selections
  without crashing
### Requirement: Dashboard Document List

`/dashboard` MUST fetch and render the active organization's documents via
`useDocuments(orgSlug)`, with each row navigable to `/documents/{id}`. When
the active organization has zero documents, the dashboard MUST render an
empty state instead of a blank region.

#### Scenario: Documents render as navigable rows

- GIVEN the active organization has two documents
- WHEN the dashboard renders
- THEN both documents appear as rows, and clicking a row navigates to that
  document's `/documents/{id}`

#### Scenario: Zero documents renders an empty state

- GIVEN the active organization has zero documents
- WHEN the dashboard renders
- THEN an empty-state message renders instead of a blank list region

#### Scenario: Switching organizations shows that organization's documents

- GIVEN the active organization changes from organization `A` to
  organization `B`
- WHEN the dashboard re-renders
- THEN it fetches and displays organization `B`'s documents, not
  organization `A`'s

