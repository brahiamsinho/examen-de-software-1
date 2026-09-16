# Exploration: Real-time multi-user collaboration on the UML canvas (WebSocket)

## Current State

- **Command flow (backend)**: HTTP POST `/api/orgs/{slug}/documents/{docId}/commands` → `resolve_membership` + `require_role(OWNER, EDITOR)` → `services.submit_command()` (`backend/apps/uml_documents/services.py:91-98`) loads the `UmlDocument` row (no `select_for_update`) → `dispatcher.apply()` returns a new `ProjectDocument` with `revision + 1` → `_save()` writes it back. **No optimistic concurrency check exists today** — `apply()` takes no expected-revision parameter, there's no row lock and no revision-match `WHERE` clause. Two concurrent POSTs can each read the same starting revision and both `.save()` sequentially (lost-update race). This predates real-time collaboration but becomes far more likely the moment 2 users edit concurrently.
- **Auth**: django-ninja `django_auth` (session cookie), CSRF echoed as a header for unsafe HTTP requests. A WS handshake carries the session cookie naturally, but there's no clean way to attach a CSRF header to a browser `new WebSocket(...)` call — Channels' `OriginValidator` is the documented substitute, not CSRF echoing.
- **Channels/ASGI — already partially scaffolded, not wired**: `channels>=4.1` and `daphne>=4.1` are already in `backend/requirements/base.txt` and both are already registered in `INSTALLED_APPS` (`daphne` before `staticfiles`, `channels` after). `backend/config/asgi.py` already wraps `ProtocolTypeRouter({"http": ..., "websocket": URLRouter([])})` — an intentional **empty** placeholder with a docblock stating it awaits future realtime work. `ASGI_APPLICATION` is already set in settings.
- **Dev vs prod serving gap**: prod `Dockerfile` CMD is `daphne -b 0.0.0.0 -p 8000 config.asgi:application` (true ASGI). Dev `Dockerfile`/`entrypoint.sh` CMD is `python manage.py runserver 0.0.0.0:8000`. Channels is documented to auto-patch `runserver` for ASGI/WS support once `channels` is in `INSTALLED_APPS` (it already is, in the right order) — but this was **not empirically verified** in this pass and needs a real WS-client spike against the dev stack before assuming zero Dockerfile change is required.
- **Channel layer — missing entirely**: no `CHANNEL_LAYERS` setting in `backend/config/settings.py`, no Redis service in `docker-compose.yml` (only `db`, `mailpit`, `backend`, `frontend`). Without one, `get_channel_layer()` returns `None` and group-broadcast is unusable. An in-memory layer only works within a single process — it silently breaks the moment there is more than one backend worker/process, which prod's `daphne` deployment could run.
- **Frontend (`frontend/src/state/document.ts`, `useDocument`)**: no polling today — fetches once on mount, and after a local `submitCommand()` does an explicit `getDocument()` refetch. Zero mechanism today for one client to learn about another client's changes. No WebSocket client code exists anywhere in `frontend/src/` (grepped, none found).
- **Frontend canvas (`DiagramCanvas.tsx`)**: the incremental-update fix from commit `84248e8` keys its update effect on the `revision` prop (not `model` identity), diffing via `cy.json({elements: toElements(model)})` and only re-laying-out genuinely new class ids via `fixedNodeConstraint`. This is revision-driven, so a remote-origin update that bumps `revision` would likely flow through the same path structurally — but the parent container (`documents/[docId]/page.tsx`) owns local in-progress gesture state (`pendingSourceId`/`pendingTargetId` for the click-click relationship flow) and Cytoscape owns its own drag state; whether a remote-triggered update mid-gesture is disruptive was **not verified** in this pass.

## Affected Areas

- `backend/apps/uml_documents/services.py`, `backend/apps/uml_documents/api.py` — the pre-existing lost-update race in command submission (relevant to the conflict-handling fork below).
- `backend/config/asgi.py`, `backend/config/settings.py` — wire the empty `"websocket"` router to a real consumer; add `CHANNEL_LAYERS`.
- `backend/requirements/base.txt` — already has `channels`/`daphne`; would add `channels-redis` only if the Redis fork is chosen.
- `backend/Dockerfile` (dev target), `backend/entrypoint.sh`, `docker-compose.yml` — possible dev ASGI-serving change; optional new Redis service.
- A new consumer needs its own org-membership/role check equivalent to `resolve_membership`/`require_role`, including re-validation for long-lived connections if membership changes mid-connection.
- `frontend/src/state/document.ts`, `frontend/src/lib/uml_documents.ts` — new WS client and live-update state wiring.
- `frontend/src/components/workspace/DiagramCanvas.tsx`, `frontend/src/app/(app)/documents/[docId]/page.tsx` — remote-update rendering vs. local in-progress gesture state.

## Approaches

1. **Command-broadcast (thin server, replay on every client)**: server dispatches, broadcasts the raw `UmlCommand`, every client replays it locally. Requires a JS/TS reimplementation of the Python dispatcher's pure handlers (duplication, drift risk); server remains sole validator, so replay logic must match exactly. Effort: High.
2. **Result-broadcast (server as sole executor)**: server applies via the existing `dispatcher.apply()` unchanged, broadcasts the resulting document state; clients never re-run business logic. Reuses 100% of existing backend logic; thin, low-risk client; consistent with `useDocument`'s current "GET is the single source of truth" pattern. Larger messages if broadcasting the full document rather than a diff. Effort: Medium.

## Recommendation

Approach 2 (result-broadcast) — it reuses the dispatcher untouched and mirrors the existing GET-is-truth pattern in `useDocument`. This is exploration only; the forks below are for the user to decide before `sdd-propose`.

## Risks

- Pre-existing lost-update race in `submit_command`/`_save` (no locking/revision check) predates this feature but is directly relevant to the conflict-handling fork.
- Dev-server WS capability under `runserver` is unverified — needs an empirical spike before assuming no Dockerfile change is required.
- WS handshake auth: CSRF doesn't apply the same way to WS; Origin validation needs explicit design.
- Remote update vs. local in-progress gesture (click-click relationship draw) interaction in `DiagramCanvas` is unverified.
- Channel-layer choice affects correctness under any multi-worker deployment (prod already runs `daphne`, which can be scaled to multiple workers).

## Open Questions (for the user, before proposal)

1. **Sync granularity**: command-replay (Approach 1) vs. result-broadcast (Approach 2, recommended)?
2. **Conflict handling**: should the server serialize command application per-document under a lock (each command still applies incrementally, so no explicit "merge conflict" UI is needed — this also fixes the pre-existing lost-update race as a side effect), or should clients see an explicit reject/retry flow on stale revisions?
3. **Presence**: is "who else is viewing/editing this document" in scope for this cycle, or purely diagram-state sync with no presence indicators?
4. **Channel layer**: in-memory (zero new infra, but silently incorrect the moment there's more than one backend worker/process) vs. Redis (`channels-redis`, new `docker-compose.yml` service, correct under any deployment topology)?

## Scope Decisions (confirmed by user)

1. **Sync granularity**: result-broadcast (Approach 2). The server applies each command via the existing `dispatcher.apply()` unchanged and broadcasts the resulting document; no command-replay logic is reimplemented on the client.
2. **Conflict handling**: server-serialized command application under a per-document lock. Each command still applies incrementally against the latest revision; no explicit reject/retry UI. This also fixes the pre-existing lost-update race in `submit_command`/`_save` as a side effect.
3. **Presence**: out of scope for this cycle. Only diagram-state sync in real time; no "who is viewing/editing" indicators.
4. **Channel layer**: Redis (`channels-redis`), with a new Redis service added to `docker-compose.yml`. Correct under any deployment topology, including prod's `daphne` server scaled to multiple workers.

## Ready for Proposal

Yes — all 4 open questions resolved above.
