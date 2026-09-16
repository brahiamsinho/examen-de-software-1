# Proposal: Live UML Node Position Sync

## Intent

Class positions are dead end-to-end: `UmlDocument.layout` is always empty,
`ProjectDocument.with_layout()` has no production caller, and
`DiagramCanvas` recomputes every position with `fcose` on load. Dragging a
class is therefore invisible to collaborators and lost on reload. The prior
cycle delivered live domain-model convergence but left the socket read-only,
so the *visual* half of the diagram never converges. This cycle makes node
positions live, durable, and safely arbitrated between simultaneous draggers.

## Scope

### In Scope

- Inbound WS plumbing: a `receive_json` override on `DocumentConsumer`
  (client→server for the first time) accepting three high-level message
  kinds — claim a node, live position while held, release with final
  position. Exact JSON contract is `sdd-design`'s job.
- Per-node claim lock in Redis, shared across daphne workers, with a TTL so
  an abandoned claim self-expires. Server is the sole arbiter; a losing
  claim gets an explicit rejection.
- `DocumentConsumer.disconnect()` proactively releases that connection's
  locks; the TTL remains the safety net for unclean drops.
- Durable write on release: a new service sibling calling `with_layout()`
  under the same `@transaction.atomic` + `select_for_update()` used by
  domain commands, then `broadcast_document`.
- Canvas seeds node positions from persisted `layout` instead of always
  auto-laying out.
- Frontend: claim on `grab`, throttled live sends while dragging, release
  with final position on `free`; a "locked by X" affordance; local grabs on
  a foreign-held node are prevented or gracefully rejected.
- Named edge cases: `RemoveClass` on a held node mid-drag; near-simultaneous
  claims on one node; a locked-out user's feedback.

### Out of Scope

- Presence beyond per-node lock ownership (no "who is viewing" list).
- Edge/relationship dragging, waypoints, or repositioning.
- Any change to the closed 7-variant `UmlCommand` union.
- Any change to how domain commands are locked, dispatched, or broadcast.

## Capabilities

### New Capabilities

- `uml-node-locking`: claim/release protocol, Redis TTL lock, server-side
  arbitration of concurrent claims, release-on-disconnect.

### Modified Capabilities

- `realtime-document-sync`: the socket accepts inbound client messages;
  position and lock-state frames join the broadcast contract.
- `uml-document-persistence`: `layout` becomes writable via a non-command
  service path; `revision` bumps on a position release.
- `web-uml-canvas`: drag emits claim/live/release, renders foreign locks,
  and seeds positions from persisted layout.

## Approach

Exploration's **Approach 2** for the durable write — a sibling service
function on `with_layout()`, not a new `UmlCommand` variant. Rationale: a
position is visual-only state (`project-document` spec keeps `UmlModel` and
`DiagramLayout` independently modifiable), so it does not belong in a closed
union of semantic mutations, and `with_layout` is already built and tested.
Claims and live frames are a *separate, ephemeral* concern: Redis-only, no
DB write, no `revision` bump — only the release write touches Postgres.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/uml_documents/consumers.py` | Modified | `receive_json`; release on `disconnect` |
| `backend/apps/uml_documents/` (new lock module) | New | Redis claim: owner token, TTL, refresh |
| `backend/apps/uml_documents/services.py` | Modified | Layout-write sibling + broadcast |
| `backend/apps/uml_modeling/documents.py` | Modified | `with_layout` gains its first caller |
| `frontend/src/state/document.ts` | Modified | Outbound sends; lock-state merge |
| `frontend/src/components/workspace/DiagramCanvas.tsx` | Modified | grab/drag/free wiring, lock affordance, seed from layout |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **No precedent for Redis app-level locking here** (`select_for_update` is a Postgres row lock, not a cross-connection per-node claim) | High | Atomic `SET NX PX` with an owner token; only the owner may release; bounded TTL with refresh while held |
| Live frames flood the channel layer | High | Client-side throttle; live frames are broadcast-only, never DB writes |
| Lock stuck after an unclean drop | Med | `disconnect()` release as fast path, TTL as backstop |
| `RemoveClass` deletes a held node mid-drag | Med | Lock is advisory and never blocks domain commands; layout entries for absent class ids are ignored/pruned; client drops the lock when the node disappears |
| Two claims race for one node | Med | Server is sole arbiter (atomic Redis claim); loser receives an explicit rejection, never client-side first-wins |
| Drag activity churns `revision` | Low | Only the on-release write bumps it |

## Rollback Plan

`git revert`. Removing `receive_json` restores today's read-only socket;
the canvas falls back to `fcose` auto-layout. Persisted `layout` values
remain valid but unread — no migration and no data loss. Orphan Redis lock
keys expire on their own TTL.

## Dependencies

- Redis + `channels-redis` (already present from `2026-09-14-realtime-uml-collaboration`).
- That cycle's `DocumentConsumer`, `uml-doc-{id}` group, and
  `broadcast_document` must remain intact.

## Success Criteria

- [ ] A drags a class; B sees it move live, with no reload.
- [ ] B cannot drag a node A is holding, and sees who holds it.
- [ ] Reload and a fresh joiner both show the last-dragged arrangement.
- [ ] A killed connection's lock is released (disconnect) or expires (TTL);
      no node stays permanently unclaimable.
- [ ] Simultaneous claims resolve to exactly one owner, decided server-side.
- [ ] `RemoveClass` on a held node does not error or strand a lock.
- [ ] The `UmlCommand` union and the domain-command pipeline are unchanged.
