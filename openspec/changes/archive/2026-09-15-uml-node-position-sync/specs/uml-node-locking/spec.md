# UML Node Locking Specification

## Purpose

Let exactly one connected client hold exclusive drag rights over a single
class node at a time, arbitrated server-side via a Redis-backed claim with a
TTL, so no node stays permanently unclaimable and no domain command is ever
blocked by a stale or held claim.

## Requirements

### Requirement: Claim Acquisition and Server-Side Arbitration

The server MUST arbitrate every `claim_node` request using a single atomic
Redis operation (e.g. `SET NX PX`) keyed by class id, storing an owner token
identifying the requesting connection. When two claims for the same node
arrive near-simultaneously, the server MUST resolve them to exactly one
owner; the losing request MUST receive an explicit rejection. Client-side
arrival order MUST NOT determine the outcome.

#### Scenario: A claim on an unheld node succeeds

- GIVEN a class node with no active lock
- WHEN a client sends `claim_node` for that class
- THEN the atomic Redis claim succeeds and that connection becomes the owner

#### Scenario: Simultaneous claims resolve to exactly one owner

- GIVEN a class node with no active lock
- WHEN two clients send `claim_node` for the same class at nearly the same
  time
- THEN exactly one claim succeeds server-side and the other is explicitly
  rejected, regardless of which message the server processed first

### Requirement: Claim TTL and Refresh

Every claim MUST carry a bounded TTL. While the owner is actively holding
the node, subsequent activity on that claim (e.g. `position_update`) MUST
refresh the TTL. A claim that is not refreshed and not explicitly released
within its TTL window MUST expire automatically and become claimable again.

#### Scenario: An abandoned claim expires via TTL

- GIVEN a claim on a class node whose owning connection stops sending any
  activity for that node
- WHEN the claim's TTL elapses without a refresh or release
- THEN the lock expires and the node becomes claimable by any client

### Requirement: Release on Completion or Disconnect

A claim MUST be releasable only by its owning token, either via an explicit
`release_node` message or via `DocumentConsumer.disconnect()`, which MUST
release every claim held by that connection as the fast path; TTL expiry
remains the backstop for unclean drops.

#### Scenario: Explicit release frees the node immediately

- GIVEN a client holds a claim on a class node
- WHEN that client sends `release_node`
- THEN the lock is removed immediately and the node becomes claimable

#### Scenario: Disconnect releases every lock the connection held

- GIVEN a client holds claims on one or more class nodes
- WHEN that client's connection disconnects
- THEN `DocumentConsumer.disconnect()` releases all of that connection's
  locks without waiting for TTL expiry

### Requirement: Lock Is Advisory and Never Blocks Domain Commands

A held node lock MUST NOT block, reject, or delay any `UmlCommand`,
including `RemoveClass` targeting the locked class. When `RemoveClass`
removes a class whose id has a persisted or in-flight layout entry, that
entry MUST be pruned or ignored rather than causing an error, and the
holding client MUST drop its local lock state for the now-absent node (see
`web-uml-canvas`).

#### Scenario: RemoveClass succeeds on a held node

- GIVEN a class node is currently locked by client A
- WHEN any client submits `RemoveClass` for that class
- THEN the command applies normally and does not error or wait on the lock

#### Scenario: A removed node's lock is not stranded

- GIVEN a class node is currently locked by client A
- WHEN `RemoveClass` removes that class
- THEN the lock is not left claimable-forever nor causes any later claim or
  release for that class id to error; it is simply inert
