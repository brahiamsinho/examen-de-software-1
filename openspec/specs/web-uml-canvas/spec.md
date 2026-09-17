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
relationship as an edge. Below the attributes compartment, the canvas MUST
render an operations compartment listing the class's operations in UML
notation (`{visibility symbol} {name}({parameters}): {returnType}`, e.g.
`+ crearUsuario(): Usuario`), with a divider separating it from the
attributes compartment; an operation with no return type MUST render
without a return-type suffix, distinctly from one with a return type (e.g.
`+ eliminar()` vs `+ crearUsuario(): Usuario`). A class with zero operations
MUST render exactly as it does today: no operations compartment and no
second divider are added, and node dimensions are computed identically to
the attribute-only case. On load, the canvas MUST seed each node's initial
position from the document's persisted `layout.positions` when an entry
exists for that class id, and MUST run `fcose` auto-layout only for
elements lacking a persisted position (an empty `layout.positions` behaves
as before: full `fcose` auto-layout). The canvas MUST also converge to a
remote-origin document update — one received over the document's WebSocket
connection rather than triggered by this client's own command submission —
using the same revision-keyed incremental update path already used for
locally-triggered updates: only genuinely new elements are laid out, and
existing node/edge positions are preserved.

(Previously: the canvas rendered only an attributes compartment with one
divider; classes with operations had no rendering support at all, and node
layout math accounted only for `attributeLines`.)

#### Scenario: Classes and relationships render as nodes and edges

- GIVEN a document with two attributed classes and one relationship
- WHEN the canvas renders
- THEN both classes appear as nodes with attributes, linked by one edge

#### Scenario: Auto-layout runs on load

- GIVEN a document with no persisted positions
- WHEN the canvas mounts
- THEN `fcose` layout runs and every node has a computed position

#### Scenario: Persisted positions are seeded instead of recomputed

- GIVEN a document with a non-empty `layout.positions` covering every class
- WHEN the canvas mounts, whether on reload or as a fresh joiner
- THEN each node is placed at its persisted position and `fcose` does not
  recompute positions for those classes

#### Scenario: A remote-origin update renders without a full re-layout

- GIVEN an open document at revision N with existing classes already
  positioned on the canvas
- WHEN a remote-origin update carrying revision N + 1 arrives over the
  document's WebSocket connection
- THEN the canvas reflects the new state at revision N + 1
- AND previously existing nodes keep their current positions, with layout
  applied only to elements newly present in the update

#### Scenario: Operations render below attributes in UML notation

- GIVEN a class with one attribute and one operation `crearUsuario` with
  return type `Usuario` and public visibility
- WHEN the canvas renders that class's node
- THEN the operations compartment appears below the attributes compartment,
  separated by a divider, showing `+ crearUsuario(): Usuario`

#### Scenario: An operation with no return type renders distinctly

- GIVEN a class with two operations, one with return type `Usuario` and one
  with no return type
- WHEN the canvas renders that class's node
- THEN the no-return-type operation renders without a `: {returnType}`
  suffix, visibly distinct from the operation that has one

#### Scenario: A class with zero operations renders exactly as before

- GIVEN a class with attributes but zero operations
- WHEN the canvas renders that class's node
- THEN no operations compartment or second divider is rendered, and the
  node's dimensions match the attribute-only rendering produced before this
  change

#### Scenario: Operations round-trip through save and reload

- GIVEN a class with an operation was saved
- WHEN the document is reloaded
- THEN the operation still appears in the class's operations compartment
  with the same name, return type, and visibility
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

### Requirement: Remote Update Does Not Disrupt an In-Progress Local Gesture

A remote-origin document update MUST NOT disrupt a local gesture already in
progress on the canvas when it arrives. This includes the click-click
relationship flow while a source class has been selected and a target is
not yet confirmed (`pendingSourceId`/`pendingTargetId`), and an active node
drag. The gesture in progress MUST remain usable to completion after the
remote update is applied.

#### Scenario: A pending relationship selection survives a remote update

- GIVEN a user has clicked a source class node in the click-click
  relationship flow and has not yet clicked a target or confirmed
- WHEN a remote-origin update arrives and is applied to the canvas
- THEN the pending source selection is still in effect afterward
- AND the user can still click a target class and confirm to submit the
  relationship

#### Scenario: An active node drag is not interrupted by a remote update

- GIVEN a user is mid-drag on a class node on the canvas
- WHEN a remote-origin update arrives and is applied to the canvas
- THEN the drag continues uninterrupted
- AND the dragged node's in-progress position is not reset or overridden by
  the update
### Requirement: Drag Emits Claim, Live Position, and Release

On grab of a class node, the canvas MUST send `claim_node` before treating
the gesture as an active hold; while dragging, it MUST send throttled
`position_update` messages, not one per mousemove; on drag end (`free`), it
MUST send exactly one `release_node` message carrying the final position.

#### Scenario: Grabbing a node sends a claim before drag proceeds

- GIVEN a class node is unheld
- WHEN the user grabs it
- THEN `claim_node` is sent before the drag is treated as an active hold

#### Scenario: Dragging sends throttled live updates, not one per mousemove

- GIVEN the local user holds a claim and is dragging a node
- WHEN the pointer moves continuously during the drag
- THEN `position_update` messages are sent at a throttled rate, not once
  per pointer-move event

#### Scenario: Releasing sends one release message with the final position

- GIVEN the local user is dragging a held node
- WHEN the drag ends
- THEN exactly one `release_node` message is sent carrying the final
  position

### Requirement: Remote Live Position Frames Move the Node

When the canvas receives a position frame for a node it does not hold, it
MUST update that node's position on the canvas immediately, without waiting
for a full document refetch.

#### Scenario: A remote live position frame moves the node in real time

- GIVEN client B is viewing a document while client A holds and drags a
  class node
- WHEN B's canvas receives a position frame for that class
- THEN B's canvas moves that node to the received coordinates immediately

### Requirement: Foreign Lock Rendering and Local Grab Prevention

When the canvas receives a lock-acquired frame for a node held by another
connection, it MUST render an affordance identifying that the node is
locked and by whom, and MUST prevent the local user from initiating a drag
on that node — or, if initiated, reject it — until the corresponding
lock-released frame arrives.

#### Scenario: A foreign-held node shows who holds it

- GIVEN client B receives a lock-acquired frame naming client A as owner of
  a class node
- WHEN B views that node
- THEN B's canvas shows that the node is locked and identifies A as holder

#### Scenario: Local grab on a foreign-held node is prevented or rejected

- GIVEN a class node is locked by another client
- WHEN the local user attempts to grab that node
- THEN the drag is prevented or immediately rejected, and no local
  `claim_node` is sent as a successful hold

### Requirement: Claim Rejection Feedback

When a `claim_node` sent by this client is rejected, the canvas MUST
surface feedback to the local user that the claim failed and MUST NOT treat
the gesture as an active hold.

#### Scenario: A lost claim race shows rejection feedback and no hold begins

- GIVEN two clients grab the same unheld node at nearly the same time and
  the local client loses arbitration
- WHEN the rejection is received
- THEN the local user sees feedback that the claim failed and the drag is
  not treated as an active hold

### Requirement: Local Node Removed While Held Drops the Local Lock

If the node currently held by this client's lock is removed (by
`RemoveClass` from any client), the canvas MUST drop its local claim/lock
state for that node without error, consistent with the lock being
advisory.

#### Scenario: A held node removed mid-drag drops the local lock

- GIVEN the local user holds and is dragging a class node
- WHEN that class is removed by a `RemoveClass` command from any client
- THEN the canvas drops its local lock state for that node without
  crashing or leaving a stale hold
### Requirement: Add Operation Command

The add-operation form MUST offer a class select, a name input, an optional
return-type select drawn from the eight primitive types (reusing the
attribute form's `PRIMITIVE_TYPES`, with an explicit "no return type"
option), and a visibility select. It MUST NOT render any parameter input —
v1 submits `parameters: ()`. Submission MUST send an `AddOperation` command
for the selected class, then refetch the document.

#### Scenario: Operation with a return type is added

- GIVEN a class exists on the canvas
- WHEN the user submits a name, a primitive return type, and a visibility
  through the add-operation form
- THEN `AddOperation` is submitted for that class with the given name,
  return type, and visibility, the document is refetched, and the class
  shows the new operation

#### Scenario: Operation with no return type is added

- GIVEN a class exists on the canvas
- WHEN the user submits a name and visibility, leaving return type unset
- THEN `AddOperation` is submitted with `return_type: null`, the document is
  refetched, and the class shows the new operation rendered as void-like

#### Scenario: No parameter input is offered

- GIVEN the add-operation form is open
- WHEN the user views the form fields
- THEN no parameter input exists and submission always sends an empty
  `parameters` tuple

### Requirement: Remove Operation Command

`RemoveOperationControl` MUST offer a class `<select>` followed by an
operation `<select>` scoped to the chosen class's operations. Submission
MUST send `RemoveOperation` for the selected class and operation
immediately, with no confirmation step, then refetch the document.

#### Scenario: Selecting a class populates its operations

- GIVEN a class with two operations
- WHEN the user selects that class in `RemoveOperationControl`
- THEN the operation `<select>` lists exactly that class's two operations

#### Scenario: Submission removes immediately without confirmation

- GIVEN a class and one of its operations are selected
- WHEN the user submits
- THEN `RemoveOperation` is submitted immediately and the document is
  refetched, with no confirmation step shown

#### Scenario: Removal persists and broadcasts live

- GIVEN client A removes an operation from a class
- WHEN the removal is applied and broadcast
- THEN the operation no longer appears in the diagram for client A after
  refetch, and a second connected client B sees the same class without that
  operation once the update arrives

