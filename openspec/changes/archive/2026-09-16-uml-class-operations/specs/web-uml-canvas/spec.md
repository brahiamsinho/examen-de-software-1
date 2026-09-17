# Delta for Web UML Canvas

## ADDED Requirements

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

## MODIFIED Requirements

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
