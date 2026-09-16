# Delta for Web UML Canvas

## MODIFIED Requirements

### Requirement: Diagram Rendering

The canvas MUST render each class as a node listing its attributes, each
relationship as an edge, and MUST apply `fcose` auto-layout on load. The
canvas MUST also converge to a remote-origin document update — one received
over the document's WebSocket connection rather than triggered by this
client's own command submission — using the same revision-keyed incremental
update path already used for locally-triggered updates: only genuinely new
elements are laid out, and existing node/edge positions are preserved.

(Previously: this requirement covered only initial load and did not address
updates originating from another client.)

#### Scenario: Classes and relationships render as nodes and edges

- GIVEN a document with two attributed classes and one relationship
- WHEN the canvas renders
- THEN both classes appear as nodes with attributes, linked by one edge

#### Scenario: Auto-layout runs on load

- GIVEN a document with no persisted positions
- WHEN the canvas mounts
- THEN `fcose` layout runs and every node has a computed position

#### Scenario: A remote-origin update renders without a full re-layout

- GIVEN an open document at revision N with existing classes already
  positioned on the canvas
- WHEN a remote-origin update carrying revision N + 1 arrives over the
  document's WebSocket connection
- THEN the canvas reflects the new state at revision N + 1
- AND previously existing nodes keep their current positions, with layout
  applied only to elements newly present in the update

## ADDED Requirements

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
