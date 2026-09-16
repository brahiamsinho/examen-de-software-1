# Exploration: Live node-position (drag/layout) sync for the UML diagram

## Current State

- **Position persistence is confirmed dead end-to-end — this is new-feature territory, not a bug fix.** `UmlDocument.layout` (`DiagramLayout{positions: Record<id,{x,y}>}`) round-trips correctly through `codec.to_json`/`from_json` and `_save` in `backend/apps/uml_documents/services.py`, but nothing ever writes a non-empty value. `create_document` seeds an empty `DiagramLayout()`; `test_api.py:31` asserts `body["layout"] == {"positions": {}}`. The closed `UmlCommand` union (7 variants: AddClass, RemoveClass, RenameClass, AddAttribute, RemoveAttribute, AddRelationship, RemoveRelationship) has no layout-touching member.
- **A ready, already-tested extension point exists but has zero callers**: `ProjectDocument.with_layout(layout, *, now)` (`backend/apps/uml_modeling/documents.py:54`) is a fully built, revision-bumping sibling of `with_model` — grep across `backend/` shows its only caller is its own unit test.
- **Frontend never reads or writes positions at all**: `DiagramCanvasProps` has no `layout` prop; `toElements(model)` only consumes `model`. Positions are always freshly computed by `cy.layout({name: "fcose", ...}).run()`, pinning already-placed nodes via `fixedNodeConstraint` and laying out only newly-added classes. The `grab`/`free` handlers added by the just-archived `realtime-uml-collaboration` cycle (DD12) only toggle a `draggingRef` and flush a deferred re-sync — they never read `e.target.position()` or call any API.
- **The just-built realtime infra is partially reusable**: `broadcast_document` (`services.py`) is generic — it takes any `ProjectDocument` and group-sends `codec.document_out(document)` over Redis to `uml-doc-{id}`, usable by any write path. But `DocumentConsumer` (`consumers.py`) is strictly **read-only** today — no `receive_json` override exists, so nothing can currently flow client→server over this socket. A live-drag design needs new inbound plumbing regardless of which write path is chosen.

## Affected Areas

- `backend/apps/uml_documents/services.py` — a new sibling to `submit_command`, or a new `UmlCommand` variant routed through it.
- `backend/apps/uml_modeling/documents.py` — `with_layout`, unused today, the natural revision-bumping primitive for a durable write.
- `backend/apps/uml_commands/commands.py` — the closed union, only touched if position updates go through the full command/dispatcher path.
- `backend/apps/uml_documents/consumers.py` — read-only today; needs `receive_json` if positions travel inbound over the existing WS connection.
- `frontend/src/components/workspace/DiagramCanvas.tsx` — no drag-end/position handler exists at all today.
- `frontend/src/state/document.ts` — `useDocument`'s socket effect / `mergeRemote` is the natural spot to fold in position broadcasts.

## Approaches

1. **New `UmlCommand` variant (e.g. `MoveClass`) through the full `submit_command` pipeline.** Reuses the locked/atomic/revision-bump/broadcast machinery verbatim; zero new infra. Every drag-end write takes the same per-document `select_for_update()` lock as domain edits and bumps `revision` the same way a domain command does.
2. **A new sibling service function calling `ProjectDocument.with_layout()` directly**, bypassing the `UmlCommand` union/dispatcher but keeping the same lock, atomicity, and broadcast guarantees. Reuses an already-tested domain primitive; no union change; still contends for the same lock and still bumps `revision`.
3. **A lock-bypassing ephemeral broadcast** — direct `group_send`, no DB write at all, needs `DocumentConsumer.receive_json` (new inbound path, since the socket is read-only today). Lightest weight, supports a live/continuous cadence without hammering the lock, but never durable — a fresh load or a new joiner always sees whatever `fcose` computes fresh, never the last-dragged arrangement.

## Recommendation

Not decided here — this is exploration only. All current-state facts needed to resolve the forks below were confirmed by direct code inspection.

## Risks

- Broadcasting every drag frame (a live/continuous cadence) could flood the Redis channel layer and every connected client's socket on a diagram with many nodes/simultaneous draggers — needs throttling either way if chosen.
- A lock-bypassing broadcast (Approach 3) could race a concurrent `RemoveClass` deleting the very node being dragged — no defined behavior today for a position update referencing a since-deleted class id.
- Folding position writes into `UmlDocument.revision` (Approaches 1/2) means `revision` churn now also reflects drag activity, not only domain-model changes — `with_layout` already supports this, but nothing exercises it today, so there's no precedent for how that interacts with any revision-based logic elsewhere.
- No per-node "claim"/locking mechanism exists anywhere in this codebase today; an explicit-claim conflict model would require new UI and new WS message types, not just a backend change.

## Open Questions (for the user, before proposal)

1. **Cadence**: broadcast live/continuous (every drag frame, Figma/Miro-style, needs throttling) vs. only-on-release (final position once the drag ends)?
2. **Persistence**: durably save the final position to `UmlDocument.layout` (survives reload, a new joiner sees the latest arrangement) vs. purely ephemeral (never saved — resets to auto-layout on next full load)?
3. **Conflict resolution when two users drag the same class at once**: last-write-wins (whoever's message arrives last/most-recently wins — no user-facing conflict, matches the existing monotonic-revision merge pattern already built) vs. an explicit per-node claim/lock (first grabber locks the node for others until released — requires new UI feedback and new message types, no precedent in this codebase)?

## Scope Decisions (confirmed by user)

1. **Cadence**: live/continuous. Position updates broadcast while a class is being dragged, not only on release. Requires new client→server inbound plumbing on `DocumentConsumer` (a `receive_json` override — the socket is read-only today) and throttling on the client to avoid flooding the Redis channel layer on every mousemove.
2. **Persistence**: durable. The final position is saved to `UmlDocument.layout` so a reload or a new joiner sees the last-dragged arrangement, not a fresh auto-layout.
3. **Conflict resolution**: explicit per-node lock. The first user to grab a class claims it; other users cannot move that same node until it's released (drag ends or the claiming connection disconnects). This needs: a claim/release message protocol over the WS, UI feedback showing a node is locked and by whom, and explicit handling for a claim that's never released because its owner's connection drops (a lock must not become permanently stuck) — `sdd-propose`/`sdd-design` must define the concrete mechanism (e.g. a Redis-backed lock with a TTL, or releasing on `DocumentConsumer.disconnect()`, or both).

**Consequence for the write path (Approaches 1-3 above)**: live cadence + a lock claim/release protocol both require genuine client→server WS traffic, which none of the 3 original approaches assumed only for the *final* durable write — `sdd-design` must design the claim/release messages as a distinct concern from the durable position write itself (claims are ephemeral/in-memory-or-Redis-only; the final position on release is what's durably persisted, likely via Approach 2's `with_layout` sibling function under the existing per-document lock).

## Ready for Proposal

Yes — all 3 open questions resolved above.
