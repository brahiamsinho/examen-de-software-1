# Delta for Realtime Document Sync

## ADDED Requirements

### Requirement: Inbound Client Messages Over the Document Connection

The system MUST accept three client→server message kinds over the same
per-document WebSocket connection previously used only for read-only
broadcast: `claim_node` (targeting a class id), `position_update` (targeting
a class id the sender currently holds, carrying in-flight coordinates), and
`release_node` (targeting a class id the sender currently holds, carrying a
final position). A `position_update` or `release_node` referencing a class
id the sender does not currently hold MUST be rejected without effect.

#### Scenario: Holder's live position update is accepted

- GIVEN a client holds the claim on a class node
- WHEN that client sends `position_update` for that class
- THEN the update is accepted and processed

#### Scenario: Non-holder's position update is rejected without effect

- GIVEN a client does not hold the claim on a class node
- WHEN that client sends `position_update` for that class
- THEN the message is rejected and no broadcast or state change occurs

### Requirement: Claim Outcome Delivery

A successful `claim_node` MUST broadcast a lock-acquired frame (class id
plus owner identity) to every client in the document's group, including the
claimant. A rejected `claim_node` MUST be delivered only to the requesting
connection as an explicit rejection, never broadcast to the group.

#### Scenario: Successful claim broadcasts to all connected clients

- GIVEN two clients, A and B, connected to the same document's group
- WHEN client A's `claim_node` succeeds
- THEN both A and B receive a lock-acquired frame naming A as owner

#### Scenario: Rejected claim reaches only the requester

- GIVEN client B already holds a claim on a class node
- WHEN client A sends `claim_node` for that same class and loses arbitration
- THEN only client A receives the rejection; no lock-acquired frame is
  broadcast to the group for A

### Requirement: Live Position Broadcast Without Persistence

Each accepted `position_update` MUST be broadcast to the document's group
as a position frame carrying the in-flight coordinates. This broadcast MUST
NOT trigger any database write and MUST NOT be gated by the per-document
row lock used for command and layout-release persistence.

#### Scenario: Live drag frames reach other clients without a DB write

- GIVEN client A holds a claim and is dragging a node
- WHEN A sends a `position_update`
- THEN client B receives a position frame reflecting the in-flight
  coordinates, and no database write occurs for that message

### Requirement: Release Broadcast Carries Persisted State

An accepted `release_node` MUST release the claim, broadcast a
lock-released frame, and broadcast the resulting persisted document (per
`uml-document-persistence`'s layout write) to every client in the group,
including the releasing client, mirroring the existing "Broadcast on
Successful Command" all-clients contract.

#### Scenario: Release broadcasts lock-released and the updated document

- GIVEN client A holds a claim and has dragged a node to a new position
- WHEN A sends `release_node` with the final position
- THEN every connected client receives a lock-released frame and the
  updated document reflecting the new persisted revision

#### Scenario: Disconnect while holding a claim broadcasts a lock-released frame

- GIVEN client A holds a claim on a class node
- WHEN A's connection disconnects without sending `release_node`
- THEN a lock-released frame for that class is broadcast to the remaining
  connected clients
