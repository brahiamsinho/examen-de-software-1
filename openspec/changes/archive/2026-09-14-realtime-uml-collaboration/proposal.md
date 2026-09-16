# Proposal: Real-time UML Collaboration

## Intent

Two members of the same organization editing one UML document cannot see
each other's work. `useDocument` fetches once on mount and refetches only
after its own `submitCommand()`, so a second editor's changes are invisible
until a manual reload. Channels/daphne are already installed, in
`INSTALLED_APPS`, and `config/asgi.py` already routes `"websocket"` to an
empty `URLRouter([])` placeholder — the scaffolding exists and is unused.
This cycle makes one document's state converge live across connected
clients.

## Scope

### In Scope

- A Channels consumer joined to a per-document group, enforcing the same
  org-membership/role gate as `resolve_membership` + `require_role`, with
  re-validation appropriate to a long-lived connection.
- `CHANNEL_LAYERS` → Redis; new Redis service in `docker-compose.yml`;
  `channels-redis` in `backend/requirements/base.txt`.
- Serialize command application per document under a row lock, then
  broadcast the resulting `ProjectDocument` to the group **including the
  submitter** (one code path; the submitter's own refetch becomes
  redundant, not wrong).
- Frontend WS client (in/beside `frontend/src/state/document.ts`) that
  connects on document mount, merges broadcasts into the same state
  `DiagramCanvas` already renders, and reuses the revision-keyed
  incremental-update path from `84248e8`.
- Remote updates must not disrupt an in-progress click-click relationship
  gesture (`pendingSourceId`/`pendingTargetId`) or a Cytoscape drag.

### Out of Scope

- Presence / "who is viewing" indicators.
- Cross-document or cross-org collaboration.
- Offline queues or replay beyond reconnect-and-refetch.
- Any change to the HTTP command endpoint's request/response shape.

## Capabilities

### New Capabilities

- `realtime-document-sync`: WS connection lifecycle, per-document group
  membership, handshake authorization, and the broadcast message contract.

### Modified Capabilities

- `uml-document-persistence`: Command Submission becomes serialized under a
  per-document lock and emits a broadcast after a successful save.
- `web-uml-canvas`: canvas state converges from remote updates without
  disturbing local in-progress gestures.

## Approach

Exploration's Approach 2 (result-broadcast). `dispatcher.apply()` is
untouched; the server stays sole executor and clients never replay
commands. HTTP POST remains the only write transport; the WS channel is
read-only fan-out. This mirrors `useDocument`'s existing
"server-document-is-truth" pattern.

**Locking rationale for sdd-design**: `submit_command` has **no**
transaction today. `select_for_update()` therefore cannot be added "inside
the existing transaction" — it must be paired with a new `atomic` scope, or
it raises `TransactionManagementError`. The project's established pattern is
the `@transaction.atomic` decorator (`apps/users/services.py:40`,
`apps/organizations/services.py:68`), so decorating `submit_command` and
chaining `.select_for_update()` onto the existing
`UmlDocument.objects.for_organization(...)` queryset in `_get_row` (tenant
scoping must be preserved) is the concrete starting point.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/uml_documents/consumers.py` | New | Per-document WS consumer + auth |
| `backend/config/asgi.py` | Modified | Fill the empty `websocket` router |
| `backend/config/settings.py` | Modified | `CHANNEL_LAYERS` (Redis, env-driven) |
| `backend/apps/uml_documents/services.py` | Modified | `atomic` + `select_for_update` + broadcast |
| `docker-compose.yml`, `backend/requirements/base.txt` | Modified | Redis service; `channels-redis` |
| `frontend/src/state/document.ts` | Modified | WS client + live merge |
| `frontend/src/components/workspace/DiagramCanvas.tsx`, `app/(app)/documents/[docId]/page.tsx` | Modified | Remote update vs. local gesture |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `runserver` may not serve WS in the dev stack | Med | **Spike first**: real WS client against dev before any other task; fall back to `daphne` in the dev Dockerfile |
| WS handshake auth — CSRF header echoing does not apply | High | **Spike**: session cookie + Channels `OriginValidator`; settle before the consumer is written |
| Remote update interrupts an in-progress gesture | Med | Guard the merge while `pendingSourceId` is set / a drag is active; explicit test |
| `select_for_update()` without `atomic` raises at runtime | High | Decorate `submit_command` with `@transaction.atomic` in the same unit |
| Broadcast fired before commit → clients read stale rows | Med | Emit via `transaction.on_commit`, matching `users/services.py:73` |

## Rollback Plan

`git revert`. Backend degrades to today's behavior once `asgi.py`'s router
is empty again; the frontend WS client fails to connect and `useDocument`
falls back to fetch-on-mount. The `atomic`/`select_for_update` hardening is
independently revertable and safe to keep. Redis is additive — removing the
compose service only disables broadcast.

## Dependencies

- New Redis service (`docker-compose.yml`) and `channels-redis`.
- Both spikes above resolved before consumer implementation starts.

## Success Criteria

- [ ] Two clients on one document: A's command appears in B's canvas with no reload.
- [ ] A non-member / insufficient-role WS handshake is rejected.
- [ ] Concurrent commands both persist; no lost update; revision increments once each.
- [ ] A remote update mid-gesture does not cancel the pending relationship or drag.
- [ ] The HTTP command endpoint's request/response shape is unchanged.
