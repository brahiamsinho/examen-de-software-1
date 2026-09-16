# Design: Live UML Node Position Sync

## Technical Approach

Two independent lock domains, deliberately never merged. **Ephemeral node
claims** live in Redis (`SET NX PX` + owner token, Lua compare-and-delete),
are advisory, never touch Postgres, and never bump `revision`. **The durable
write** is a new `services.save_layout_position` sibling that takes exactly
the same `@transaction.atomic` + `_get_row(for_update=True)` Postgres row
lock `submit_command` already takes (`services.py:119-135`), calls the
already-built-but-uncalled `ProjectDocument.with_layout` (`documents.py:54`),
and broadcasts via `transaction.on_commit(broadcast_document)`. It fires once
per release, never per drag frame.

`DocumentConsumer` gains its first `receive_json`. Everything else from the
prior cycle — the `uml-doc-{doc_id}` group, `document.update`, the monotonic
merge, the reconnect/backoff — is untouched.

## Decision Drivers

- `_get_row(for_update=True)` and `@transaction.atomic` already exist and are
  already the documented per-command lock (`services.py:59-75`, DD1 prior).
- `DocumentConsumer` is a **sync** `JsonWebsocketConsumer`; it already calls
  sync ORM (`services.get_document`) and `async_to_sync(group_send)` directly.
- Prior-cycle DD4 authorizes `connect()` with **membership only, no
  `require_role`** — correct for a read subscription, insufficient now that
  the socket writes.
- `cy.json({elements})` preserves existing positions; the only position-moving
  call is `cy.layout(...).run()`, gated on `newClassIds.length > 0`
  (`DiagramCanvas.tsx:337-364`).
- `DiagramCanvas` already routes volatile callbacks through refs
  (`onNodeTapRef`, `syncModelRef`) to keep mount-bound handlers fresh.
- `channels-redis>=4.2` already pulls `redis-py`, which ships a **sync**
  client alongside its asyncio one.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | New module `backend/apps/uml_documents/locks.py` using a **sync `redis.Redis`** client from a module-level lazy connection pool, built from the existing `settings.REDIS_HOST`/`REDIS_PORT` | Reach into `get_channel_layer()`'s private connection; `django-redis`/Django cache; an in-process dict | The channel layer's pool is private API and asyncio-only. A dict is per-process and fails silently under multi-worker `daphne` — the exact failure DD8 of the prior cycle rejected `InMemoryChannelLayer` for. Reusing `REDIS_HOST`/`REDIS_PORT` means one Redis coordinate, no new env var (`config.yaml`: never hardcode hosts). `redis` is promoted to an explicit line in `requirements/base.txt` because it becomes a direct import, not a transitive one |
| DD2 | Key `uml-lock:{doc_id}:{class_id}`; value `f"{token}\|{label}"` where `token = uuid4().hex` is per-**connection** and `label` is `user.full_name or user.email`. Claim is `SET key value NX PX 10000` | Key per user; value = `channel_name`; JSON value | Per-document prefix scopes the keyspace to one diagram, so a `SCAN MATCH uml-lock:{doc_id}:*` snapshot is bounded by that diagram's node count. `NX` is what makes near-simultaneous claims resolve to exactly one winner **server-side**, per proposal §Risks. A per-connection `uuid4` token (not `channel_name`) keeps a routable server address out of a value that gets compared and split. `\|` with `split("\|", 1)` is byte-deterministic to rebuild, which a re-serialized JSON value is not — and exact-value rebuild is what compare-and-delete depends on |
| DD3 | Release and refresh are **Lua scripts** registered once via `client.register_script(...)`: release = `if GET==ARGV[1] then DEL end`, refresh = `if GET==ARGV[1] then PEXPIRE ARGV[2] end` | `GET` then `DEL`; `DEL` unconditionally; `redis-py`'s `Lock` | Plain GET-then-DEL races: the key can expire and be re-claimed by another user between the two calls, so the loser deletes the winner's lock. Lua is atomic on a single-threaded server. `redis-py`'s `Lock` helper is thread-owned, not connection-owned, and gives no per-node fan-out hook. **The refresh script doubles as authorization**: a live-position frame is broadcast only when refresh returns `1`, so "only the owner may move this node" and "holding it keeps it alive" are one round trip |
| DD4 | TTL **10 000 ms**, refreshed by every live-position frame; client throttle **50 ms** (20 Hz) | 2s TTL; 30s TTL; 16ms/60Hz; refresh on a timer | 20 Hz reads as continuous motion (well above the ~12 Hz fusion threshold) and cuts a 60 Hz `mousemove` stream to a third of the `group_send` publishes proposal §Risks flags as flooding. TTL is 200× the refresh cadence, so a GC pause or a slow frame can never drop a live lock; an abandoned lock still frees within 10 s — human-tolerable, and only the backstop, since `disconnect()` (DD7) is the fast path. A separate refresh timer would be a second scheduler for data the drag stream already carries |
| DD5 | **Two lock domains, explicitly disjoint.** Redis node claim = ephemeral, advisory, cross-connection, per *class id*. Postgres `select_for_update()` = per *document row*, per *write*, held only inside one `@transaction.atomic`. Neither consults the other | One lock; a Postgres advisory lock for claims; skipping the row lock on layout writes | A claim outlives a request and must be visible to every worker, which a transaction-scoped row lock cannot be; the row lock serializes concurrent writers to one JSON blob, which a TTL key cannot do. Making the claim advisory is what keeps `submit_command` **byte-identical** (proposal §Out of Scope) — a held claim never blocks or delays a domain command |
| DD6 | `receive_json` re-resolves membership **and** calls `require_role(membership, Role.OWNER, Role.EDITOR)` on every inbound message, mirroring `submit_command_view` (`api.py:74-75`). A `VIEWER` still connects and still receives everything | Authorize once at `connect()`; add the role gate to `connect()` | Prior DD4 dropped the role gate because the socket was read-only; it is not anymore, and a `VIEWER` who can only `GET` must not be able to move a node. Gating `connect()` instead would regress prior DD4 and cut a `VIEWER` off from live updates entirely. Per-message re-resolution is the same "check at the moment data would change" argument prior DD5 makes for the relay direction |
| DD7 | `disconnect()` iterates `self.held` (a per-connection `set[str]` of class ids), runs the DD3 release script for each, and `group_send`s one `node.unlocked` per released id. **No durable write on disconnect** | Persist the last live position on disconnect; rely on TTL alone | The last frame of an interrupted drag is not a position the user chose to commit; persisting it would bump `revision` from a dropped connection. `self.held` means the loop releases only this connection's locks — never another's, even on a shared node id. Guarded with `getattr(self, "held", set())` so a `4401`/`4404` close, which never reached `accept()`, is a no-op |
| DD8 | `services.save_layout_position(*, organization, doc_id, class_id, position, now) -> ProjectDocument`, `@transaction.atomic`, prunes layout entries whose class id is absent from `document.model.classes`, and **returns early without a write** when `class_id` itself is gone | Persist unpruned; a `MoveClass` `UmlCommand` variant; a raw `UPDATE` on `data` | Copies `submit_command`'s shape line-for-line (`for_update=True` → mutate → `_save` → `on_commit(broadcast_document)`), so the two write paths cannot drift. The union stays closed at 7 variants (proposal §Out of Scope) because a position is visual-only state `ProjectDocument` deliberately splits from `model` (`documents.py` docstring). Pruning on every persist is self-healing and needs no migration; the early return is the `RemoveClass`-mid-drag case, and it bumps no `revision` because nothing changed |
| DD9 | Live frames carry `owner_token` in the **group event only**; each consumer's handler strips it and emits `"mine": event["owner_token"] == self.token` to its own client. `node.locked` with `mine: true` **is** the claim-accepted ack | A separate `node.claim_accepted` frame; broadcasting the token; a per-recipient `group_send` | A group handler runs once per connection, so it can personalize a fan-out payload for free — no token ever reaches a browser. Reusing `node.locked` as the ack means every client, owner included, learns the lock in one ordered frame instead of two that can interleave. `mine` is also exactly what the owner needs to ignore the echo of its own position frames |
| DD10 | On `connect()`, after `accept()`, send one `node.locks` snapshot built from `SCAN MATCH uml-lock:{doc_id}:*` (never `KEYS`) | No snapshot; a Redis hash of locks; a per-document lock set | A joiner that skipped the snapshot would happily grab a node someone is already holding and only learn on the rejection — correct but jarring. `SCAN` is cursor-based and non-blocking; `KEYS` blocks the whole server. A hash gives no per-field TTL, so an abandoned entry would leak forever — the exact failure TTL exists to prevent |
| DD11 | Lock state goes through `useDocument`'s React state (one `setState` per claim/release). **Live positions bypass React entirely** via a stable `positionListenerRef` that `DiagramCanvas` writes its imperative apply-handler into on mount | `useState` for positions; a Jotai atom; a `requestAnimationFrame` buffer | A `setState` at 20 Hz per dragger re-renders `DocumentPage` and its whole sidebar for data only Cytoscape consumes. The ref-as-latest-handler idiom is already this file's convention (`onNodeTapRef`, `syncModelRef`, DD9/DD12 prior). Lock changes are genuinely low-frequency and genuinely belong in render, so they stay in state |
| DD12 | Foreign-held nodes are `ungrabify()`d by a `locks`-keyed effect (and `grabify()`d on unlock) plus a `.locked-remote` dashed-amber style; the owner label renders in a text affordance under the canvas in `page.tsx`. Claim is **optimistic**: the drag starts locally, and `node.claim_rejected` snaps the node back to the position stashed in `grabStartPosRef` | Await the ack before allowing the drag; regenerate the SVG box with a name badge; cancel inside the `grab` handler | `ungrabify()` means no `grab` event fires at all — prevention, not cancellation. Blocking the drag on a round trip would make every local drag feel laggy for a conflict that is rare. Rendering the owner name into `classBoxSvgDataUri` would rebuild and re-upload every node's background image on every lock change; a DOM text line costs nothing and is trivially assertable in RTL |
| DD13 | `toElements(model, layout)` seeds `position` from `layout.positions[c.id]`; the first sync seeds `laidOutClassIdsRef` from `Object.keys(layout.positions)` instead of the empty set | A separate post-sync `cy.nodes().positions()` pass; always run fcose then restore | Feeding `laidOutClassIdsRef` from the persisted layout makes persisted classes flow into the **existing** `fixedNodeConstraint` branch and only unplaced classes into `newClassIds` — so "new class since the last layout save" needs no new branch, it *is* the current new-class path. An empty `layout` leaves `previouslyLaidOut.size === 0`, which is today's `isFirstLayout` full-fcose behavior verbatim, so rollback and legacy documents are identical to today |

## Message Contract

`receive_json(self, content, **kwargs)` — inbound, client→server:

```json
{"type": "node.claim",    "class_id": "c1"}
{"type": "node.position", "class_id": "c1", "x": 120.5, "y": -40.0}
{"type": "node.release",  "class_id": "c1", "x": 120.5, "y": -40.0}
```

`node.release` accepts `"x": null, "y": null` (or omitted) — that releases the
lock and skips the durable write (DD8's `RemoveClass` path). An unknown
`type`, a missing `class_id`, or a non-numeric `x`/`y` is **dropped
silently**; the socket is never closed on a malformed frame, matching
`api.py`'s "a bad client payload never surfaces as a 500" stance.

Outbound. Group events (`group_send` `type` → handler by Channels'
dot-to-underscore rule) are `node.locked` → `node_locked`, `node.unlocked` →
`node_unlocked`, `node.position` → `node_position`. Each handler re-derives
`mine` per connection (DD9) and never forwards `owner_token`:

```json
{"type": "node.locked",         "class_id": "c1", "owner_label": "Ana", "mine": false}
{"type": "node.position",       "class_id": "c1", "x": 120.5, "y": -40.0, "mine": false}
{"type": "node.unlocked",       "class_id": "c1"}
{"type": "node.claim_rejected", "class_id": "c1", "owner_label": "Ana"}
{"type": "node.locks",          "locks": [{"class_id": "c1", "owner_label": "Ana", "mine": false}]}
```

`node.claim_rejected` and `node.locks` are **direct** `send_json` to one
socket, never `group_send`, so their names need no handler. `document.update`
is unchanged and still carries the full `DocumentOut`.

Sync/async compatibility: `DocumentConsumer` stays a sync
`JsonWebsocketConsumer`, so `receive_json` runs in Channels' thread pool —
blocking sync ORM (`save_layout_position`) and the blocking `redis.Redis`
client are both safe there, and `async_to_sync(self.channel_layer.group_send)`
is the idiom this file already uses at lines 47/53. `channels_redis` is
untouched.

## Sequence Diagram (`config.yaml` `rules.design`)

```mermaid
sequenceDiagram
    autonumber
    participant A as Client A (dragger)
    participant B as Client B (observer)
    participant CA as DocumentConsumer A
    participant CB as DocumentConsumer B
    participant L as Redis lock keys
    participant G as Redis channel layer
    participant PG as Postgres

    Note over A: cy "grab" on node c1 → optimistic local drag
    A->>CA: {"type":"node.claim","class_id":"c1"}
    CA->>CA: resolve_membership_for_user + require_role(OWNER, EDITOR)
    CA->>L: SET uml-lock:{doc}:c1 "{token}|Ana" NX PX 10000
    L-->>CA: OK
    CA->>CA: self.held.add("c1")
    CA->>G: group_send node.locked (owner_token, owner_label)
    G->>CB: node_locked → {"class_id":"c1","owner_label":"Ana","mine":false}
    G->>CA: node_locked → {"class_id":"c1","owner_label":"Ana","mine":true}
    Note over B: ungrabify("c1") + .locked-remote style (DD12)

    loop every 50 ms while held (DD4)
        A->>CA: {"type":"node.position","class_id":"c1","x":…,"y":…}
        CA->>L: EVAL refresh (GET==token ? PEXPIRE 10000 : 0)
        L-->>CA: 1
        CA->>G: group_send node.position
        G->>CB: node_position (mine:false) → positionListenerRef → cy position (no re-render, DD11)
    end

    Note over A: cy "free" on c1
    A->>CA: {"type":"node.release","class_id":"c1","x":…,"y":…}
    CA->>PG: save_layout_position — atomic + SELECT … FOR UPDATE
    PG-->>CA: row
    CA->>CA: prune absent ids → with_layout(...) → revision + 1
    CA->>PG: _save(row, updated); on_commit(broadcast_document)
    CA->>L: EVAL release (GET==token ? DEL : 0)
    CA->>G: group_send node.unlocked
    G->>CB: node_unlocked → grabify("c1")
    PG-->>G: COMMIT → group_send document.update
    G->>CB: document.update → monotonic merge → canvas seeds from layout (DD13)
    G->>CA: document.update → merge is a no-op past its own revision

    Note over CA: on disconnect — release every id in self.held,<br/>group_send node.unlocked each; NO durable write (DD7).<br/>TTL 10s is the backstop if the process dies outright.
```

## Interfaces / Contracts

```python
# services.py — new sibling, mirroring submit_command's shape exactly (DD8)
@transaction.atomic
def save_layout_position(
    *, organization: Organization, doc_id: UUID, class_id: str,
    position: Position, now: datetime.datetime,
) -> ProjectDocument:
    row = _get_row(organization=organization, doc_id=doc_id, for_update=True)
    document = _to_project_document(row)
    live = {c.id for c in document.model.classes}
    target = ElementId(class_id)
    if target not in live:                       # RemoveClass mid-drag (DD8)
        return document                          # no write, no revision bump
    positions = {cid: p for cid, p in document.layout.positions.items() if cid in live}
    positions[target] = position                 # prunes orphans on every persist
    updated = document.with_layout(DiagramLayout(positions=positions), now=now)
    _save(row, updated)
    transaction.on_commit(lambda: broadcast_document(document=updated))
    return updated
```

```python
# locks.py — new module (DD1/DD2/DD3)
LOCK_TTL_MS = 10_000

def key(doc_id, class_id) -> str: ...            # f"uml-lock:{doc_id}:{class_id}"
def claim(*, doc_id, class_id, token, label) -> tuple[bool, str | None]:
    """SET NX PX. Returns (True, None) or (False, current_owner_label)."""
def refresh(*, doc_id, class_id, token) -> bool: """Lua: owner-only PEXPIRE — also the per-frame authz check."""
def release(*, doc_id, class_id, token) -> bool: """Lua: owner-only DEL (compare-and-delete)."""
def snapshot(*, doc_id) -> list[tuple[str, str, str]]:  """SCAN MATCH — (class_id, token, label)."""
```

```lua
-- release                                    -- refresh
if redis.call('GET', KEYS[1]) == ARGV[1]      if redis.call('GET', KEYS[1]) == ARGV[1]
  then return redis.call('DEL', KEYS[1])        then return redis.call('PEXPIRE', KEYS[1], ARGV[2])
  else return 0 end                             else return 0 end
```

```ts
// DiagramCanvas.tsx — new props (DD11/DD12/DD13)
type LockState = { ownerLabel: string; mine: boolean };
layout: DiagramLayout;
locks: Record<string, LockState>;
positionListenerRef: RefObject<((classId: string, x: number, y: number) => void) | null>;
onClaim: (classId: string) => void;
onLivePosition: (classId: string, x: number, y: number) => void;   // throttled 50 ms
onRelease: (classId: string, x: number, y: number) => void;

// toElements gains layout (DD13): node data unchanged, `position` seeded when known.
export function toElements(model: UmlModel, layout: DiagramLayout): ElementDefinition[]
```

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/uml_documents/locks.py` | Create | Redis claim/refresh/release/snapshot + registered Lua scripts (DD1/DD2/DD3/DD10) |
| `backend/apps/uml_documents/consumers.py` | Modify | `self.token`/`self.label`/`self.held` in `connect()`; `node.locks` snapshot; `receive_json` (DD6); `node_locked`/`node_unlocked`/`node_position` handlers (DD9); lock release in `disconnect()` (DD7) |
| `backend/apps/uml_documents/services.py` | Modify | `save_layout_position` (DD8) |
| `backend/apps/uml_modeling/documents.py` | **None** | Zero diff — `with_layout` gains its first caller, unchanged |
| `backend/apps/uml_commands/`, `backend/config/settings.py`, `asgi.py`, `routing.py` | **None** | Zero diff — closed union, channel layer, routing, and origin policy all reused as-is |
| `backend/requirements/base.txt` | Modify | Promote `redis>=5.0,<6.0` to a direct dependency (DD1) |
| `frontend/src/lib/uml_documents.ts` | Modify | Lock/position message types; `DocumentSocketHandlers` gains `onNodeLocked`/`onNodeUnlocked`/`onNodePosition`/`onNodeLocks`/`onClaimRejected`; `openDocumentSocket` returns send helpers |
| `frontend/src/state/document.ts` | Modify | `locks` state, `positionListenerRef`, `sendClaim`/`sendPosition`/`sendRelease`, 50 ms throttle (DD4/DD11) |
| `frontend/src/components/workspace/DiagramCanvas.tsx` | Modify | `toElements(model, layout)`, layout seeding (DD13), grab/drag/free wiring, `ungrabify`/`.locked-remote` (DD12) |
| `frontend/src/app/(app)/documents/[docId]/page.tsx` | Modify | Pass `layout`/`locks`/handlers; render the "Ana está moviendo X" affordance (DD12) |
| `docs/ai/DECISIONS_LOG.md` | Modify | Append DD1-DD13 (`config.yaml` `rules.design` dual documentation) |
| `docs/ai/CURRENT_STATE.md` | Modify | Socket is bidirectional; `layout` is live; `with_layout` has a production caller |

## Testing Strategy

| Layer | Case |
|---|---|
| Unit (pytest) | `claim` twice on one key → second returns `(False, first_label)`; `release` with a foreign token returns `False` and leaves the key; `release` then re-`claim` succeeds; `refresh` with a foreign token returns `False` |
| Unit | `save_layout_position` bumps `revision` by exactly 1 and leaves `model` identical |
| Unit | `save_layout_position` for a removed `class_id` writes nothing and does not bump `revision`; a stale entry for another removed class is pruned on the next successful persist (DD8) |
| Integration (`django_capture_on_commit_callbacks`) | A release broadcasts `document.update` exactly once, after commit; a live-position frame broadcasts **zero** `document.update` |
| Integration (`WebsocketCommunicator`) | Two sockets, one node: the second `node.claim` receives `node.claim_rejected`; the first receives `node.locked` with `mine: true` |
| Integration | A `VIEWER` connects and receives broadcasts, but `node.claim` is refused by DD6's `require_role` |
| Integration | Closing the holder's socket emits `node.unlocked` to the survivor and leaves the key deleted; no `document.update` fires (DD7) |
| Integration | A `node.position` from a non-owner is neither persisted nor broadcast (DD3 refresh-as-authz) |
| Integration | A fresh socket joining a document with a held lock receives `node.locks` naming it (DD10) |
| Unit (Vitest) | The 50 ms throttle emits at most one `node.position` per interval and **always** emits the final position on `free` |
| Unit (Vitest) | `toElements(model, layout)` seeds `position` for persisted ids and omits it for unplaced ones (DD13) |
| Component (RTL) | A foreign `node.locked` ungrabifies that node and renders the owner affordance; `node.unlocked` restores grabbing (DD12) |
| Component (RTL) | `node.claim_rejected` restores `grabStartPosRef`'s position; a remote `node.position` moves the node with **zero** re-render (DD11) |
| Component (RTL) | A document whose `layout.positions` is empty runs the full first-layout fcose path exactly as today (DD13 fallback) |
| E2E | Deferred — no Cypress harness (`config.yaml` `testing.e2e`) |

## Threat Matrix

N/A — no shell command, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary is introduced. The real new
adversarial surface is the **first inbound WS message path**, covered
explicitly rather than by an inapplicable matrix: per-message role gate
(DD6), owner-token authorization on every live frame (DD3), silent drop of
malformed frames, no token ever reaching a browser (DD9), and per-document
key prefixing so one tenant's `class_id` cannot address another's lock (DD2,
on top of the org-scoped `_get_row` the write path still takes).

## Migration / Rollout

No database migration — `UmlDocument` is untouched and `layout` already
round-trips through `codec`. Redis is already deployed and healthchecked from
the prior cycle; lock keys are a new, self-expiring keyspace alongside the
channel layer. Rollback is `git revert`: with `receive_json` gone the socket
is read-only again, persisted `layout` values stay valid but unread, and
DD13's seeding collapses to today's full-fcose path. Orphan lock keys expire
on their own TTL.

## Open Questions

- [ ] DD4's 50 ms / 10 s pair is reasoned, not measured. Worth one pass during
      apply with two browsers on a diagram of ~20 classes.
- [ ] DD12 shows the owner label under the canvas rather than on the node. If
      that reads as too disconnected in practice, the follow-up is a Cytoscape
      overlay layer, not an SVG regeneration.
