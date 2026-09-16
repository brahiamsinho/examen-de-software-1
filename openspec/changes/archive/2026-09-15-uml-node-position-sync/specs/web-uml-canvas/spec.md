# Delta for Web UML Canvas

## MODIFIED Requirements

### Requirement: Diagram Rendering

The canvas MUST render each class as a node listing its attributes, each
relationship as an edge. On load, the canvas MUST seed each node's initial
position from the document's persisted `layout.positions` when an entry
exists for that class id, and MUST run `fcose` auto-layout only for
elements lacking a persisted position (an empty `layout.positions` behaves
as before: full `fcose` auto-layout). The canvas MUST also converge to a
remote-origin document update — one received over the document's WebSocket
connection rather than triggered by this client's own command submission —
using the same revision-keyed incremental update path already used for
locally-triggered updates: only genuinely new elements are laid out, and
existing node/edge positions are preserved.

(Previously: the canvas always ran `fcose` auto-layout for every node on
load regardless of any persisted layout, since `layout` was never read.)

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

## ADDED Requirements

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
