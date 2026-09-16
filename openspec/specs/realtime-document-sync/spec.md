# Realtime Document Sync Specification

## Purpose

Converge one `UmlDocument`'s state live across every client connected to it,
by fanning out the server-applied result of each successful command over a
per-document WebSocket group. The server remains the sole command executor;
this channel is read-only fan-out, mirroring the existing
`GET .../documents/{doc_id}` "server-document-is-truth" pattern.

## Requirements

### Requirement: WS Connection Lifecycle and Authorization

A client MUST connect to a WebSocket group scoped to exactly one
`UmlDocument`. The connection handshake MUST resolve the caller's
organization membership using the same check as
`resolve_membership(request, org_slug)`, and MUST reject the connection
before joining any group when the caller is not a member of the document's
organization. Because reading a document's live state requires no specific
role today (`GET .../documents/{doc_id}` admits `VIEWER`, `EDITOR`, and
`OWNER` alike), any member of the document's organization, regardless of
role, MUST be admitted to the group once membership is confirmed.

#### Scenario: A member connects and joins the document's group

- GIVEN an authenticated user with any role (`VIEWER`, `EDITOR`, or `OWNER`)
  on the document's organization
- WHEN they open a WebSocket connection scoped to that document
- THEN the connection is accepted and the client joins the document's group

#### Scenario: A non-member's connection is rejected

- GIVEN an authenticated user with no membership in the document's
  organization
- WHEN they attempt to open a WebSocket connection scoped to that document
- THEN the connection is rejected before joining any group
- AND the rejected client receives no document state or broadcasts

### Requirement: Broadcast on Successful Command

After a command is applied through the existing command-submission path and
its resulting `ProjectDocument` is persisted, the server MUST broadcast the
persisted document state to every client currently connected to that
document's group, including the client that submitted the command. There
MUST be exactly one broadcast code path for all group members; the
submitter MUST NOT be excluded or receive a differently shaped message.

#### Scenario: Two connected clients both receive the update

- GIVEN two clients, A and B, both connected to the same document's group
- WHEN client A submits a command that is applied and persisted
  successfully
- THEN both client A and client B receive the resulting document state over
  the WebSocket connection with no manual reload
- AND the state both clients receive reflects the new persisted revision

#### Scenario: A rejected or failed command produces no broadcast

- GIVEN a client connected to a document's group
- WHEN a command submission to that document fails validation and is not
  persisted
- THEN no broadcast is sent to the group for that submission

### Requirement: Broadcast Timing Relative to the Transaction

The broadcast for a successful command MUST fire only after the database
transaction that persisted the resulting document has committed. No
connected client may ever receive, over this channel, a document state that
the submitting request's own transaction later rolled back.

#### Scenario: Broadcast never precedes commit

- GIVEN a command submission that persists a new document state inside a
  database transaction
- WHEN that transaction is later rolled back for any reason before it
  commits
- THEN no broadcast for that submission is ever sent to the document's group

#### Scenario: Broadcast follows a committed transaction

- GIVEN a command submission whose transaction commits successfully
- WHEN the commit completes
- THEN the broadcast carrying the resulting document state is sent to the
  document's group only after that commit
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
