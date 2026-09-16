# Tasks: Real-time UML Collaboration

Strict TDD. Backend test command: `cd backend && pytest`. Frontend test
command: `cd frontend && npm test`. Full regression:
`cd backend && pytest ; cd frontend && npm test`.

## Review Workload Forecast

This session's review budget is **800 changed lines** (`additions +
deletions`), not the generic 400-line default.

| Field | Value |
|-------|-------|
| Estimated changed lines | ~850-900 (backend prod ~195 + backend tests ~270; frontend prod ~125 + frontend tests ~210; docs ~75) |
| 800-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 backend foundation → PR 2 backend realtime channel → PR 3 frontend realtime client |
| Delivery strategy | single-pr |
| Chain strategy | N/A — size:exception accepted |

Decision needed before apply: **Resolved** — user accepted `size:exception`
for a single PR (2026-09-14), matching this project's `uml-document-persistence`
precedent. Proceeding as one apply/commit despite the ~850-900 line estimate
exceeding the 800-line budget by a small margin.
Chained PRs recommended: No (user declined the chain option)
800-line budget risk: High (accepted)

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Redis channel layer + locked/atomic `submit_command` + `codec.document_out` promotion, no consumer yet | PR 1 | `cd backend && pytest apps/uml_documents/tests/test_services.py apps/uml_documents/tests/test_codec.py` | `docker compose up -d redis backend` + confirm `redis-cli ping` healthy | `git revert`; `select_for_update`/atomic hardening is independently safe to keep (design.md Migration/Rollout) |
| 2 | `DocumentConsumer` + routing + `asgi.py` wiring + `resolve_membership_for_user` extraction | PR 2 (base: PR 1) | `cd backend && pytest apps/uml_documents/tests/test_consumers.py apps/organizations/tests/test_permissions.py` | `docker compose up backend` + confirm startup banner reads `Starting ASGI/Daphne version …` | `git revert`; `asgi.py` router reverts to empty `URLRouter([])`, frontend socket fails to open, `useDocument` falls back to fetch-on-mount |
| 3 | Frontend WS client (`useDocument`) + canvas drag guard + docs | PR 3 (base: PR 2) | `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/state/__tests__/document.test.ts src/components/workspace/__tests__/DiagramCanvas.test.tsx` | `cd frontend && npm run dev` + manual: two browser tabs on one document, confirm live convergence with no reload | `git revert`; socket simply fails to connect, `useDocument` behaves exactly as pre-cycle |

## Phase 1: Redis Infrastructure & Channel Layers (DD8)

- [x] 1.1 Modify `docker-compose.yml` — add `redis:7-alpine` service with a
      `redis-cli ping` healthcheck; `backend.depends_on` gains
      `condition: service_healthy` on it.
- [x] 1.2 Modify `backend/requirements/base.txt` — add
      `channels-redis>=4.2,<5.0`.
- [x] 1.3 Modify `backend/env.example` — add `REDIS_HOST`/`REDIS_PORT`.
- [x] 1.4 Modify `backend/config/settings.py` — `REDIS_HOST`/`REDIS_PORT` env
      vars defaulting to `("redis", 6379)`; `CHANNEL_LAYERS` using
      `channels_redis.core.RedisChannelLayer`.
- [x] 1.5 Verify: `docker compose build && docker compose up -d redis backend`;
      confirm the `redis` healthcheck passes and `backend` starts without a
      `ConnectionError` from `CHANNEL_LAYERS`. **Confirmed by orchestrator**:
      `docker compose up -d` shows `redis-1 Healthy` before `backend-1
      Starting`/`Started` (the `depends_on: condition: service_healthy` gate
      worked); no `ConnectionError` in backend logs.

## Phase 2: Locked Command Submission & Broadcast Seam (DD1, DD2, DD6)

- [x] 2.1 RED: `backend/apps/uml_documents/tests/test_services.py` —
      `_get_row(for_update=True)` called outside a transaction raises
      `TransactionManagementError`; called inside `submit_command` it does
      not.
- [x] 2.2 RED: same file — `_get_row(for_update=True)` for org B's `doc_id`
      still raises `Http404`; the lock never bypasses `for_organization`
      tenant scoping.
- [x] 2.3 GREEN: modify `backend/apps/uml_documents/services.py` — `_get_row`
      gains `for_update: bool = False`, conditionally chaining
      `.select_for_update()` **after** `.for_organization(...)`;
      `submit_command` gains `@transaction.atomic` and calls `_get_row(...,
      for_update=True)`.
- [x] 2.4 Pin (write and confirm GREEN against current code, before moving
      it): `backend/apps/uml_documents/tests/test_codec.py` — asserts
      `DocumentOut.model_validate(codec.document_out(doc))` equals the
      current `GET .../documents/{doc_id}` response body byte-for-byte
      (DD6). This snapshot MUST pass against today's `api._document_out`
      before the promotion below.
- [x] 2.5 GREEN: modify `backend/apps/uml_documents/codec.py` — add
      `document_out(document) -> dict`, composed from the existing
      `_encode_model`/`_encode_layout`; modify
      `backend/apps/uml_documents/api.py` — `_document_out` delegates to
      `codec.document_out`. Re-run 2.4's pin test to confirm it is still
      green.
- [x] 2.6 RED: same `test_services.py` — using
      `django_capture_on_commit_callbacks` (**not** the default
      `pytest.mark.django_db`, which never fires `on_commit` callbacks), the
      broadcast fires exactly once, after commit, and not at all when
      `apply()` raises.
- [x] 2.7 GREEN: modify `services.py` — add module-level
      `broadcast_document(*, document)` (mirrors `users/services.py:73`
      style) sending `{"type": "document.update", "document":
      codec.document_out(document)}` to group `f"uml-doc-{document.id}"`;
      wire it via `transaction.on_commit(lambda: broadcast_document(...))`
      after `_save(...)`, closing over `result.document`.
- [x] 2.8 RED+GREEN: `test_services.py`, `transaction=True` — two concurrent
      `submit_command` calls on one document both persist; final `revision`
      is exactly N + 2; no lost update.

## Phase 3: Membership Extraction (DD4)

- [x] 3.1 RED: `backend/apps/organizations/tests/test_permissions.py` —
      `resolve_membership_for_user(user, org_slug)` and
      `resolve_membership(request, slug)` return the same `Membership` row
      and raise `Http404` identically for unknown-slug and non-member.
- [x] 3.2 GREEN: modify `backend/apps/organizations/permissions.py` —
      extract `resolve_membership_for_user(user, org_slug)`;
      `resolve_membership` becomes a one-line delegate; confirm all existing
      HTTP callers stay byte-identical.

## Phase 4: WebSocket Consumer & Routing (DD3, DD4, DD5, DD7, DD9, DD10)

- [x] 4.1 Create `backend/apps/uml_documents/routing.py` —
      `websocket_urlpatterns` for `ws/orgs/<org_slug>/documents/<doc_id>/`
      routed to `DocumentConsumer`.
- [x] 4.2 RED: `backend/apps/uml_documents/tests/test_consumers.py` (built
      on `WebsocketCommunicator`, wrapped with `asgiref.sync.async_to_sync`
      instead of a new `pytest-asyncio` dependency) — authenticated member
      of any role (`VIEWER`/`EDITOR`/`OWNER`) connects and joins the group;
      anonymous connection closes `4401`; non-member closes `4404`; member
      of org A against org B's `doc_id` closes `4404`.
- [x] 4.3 GREEN: create `backend/apps/uml_documents/consumers.py` —
      `DocumentConsumer(JsonWebsocketConsumer).connect()` calls
      `resolve_membership_for_user`, loads the row through
      `for_organization(membership.organization)`, `group_add(f"uml-doc-
      {doc_id}")`, accepts; close codes `4401`/`4404` on the miss cases
      (DD3/DD4).
- [x] 4.4 Modify `backend/config/asgi.py` — replace `URLRouter([])` with
      `OriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
      settings.CORS_ALLOWED_ORIGINS)` (DD9); update the docblock; imports
      stay after `get_asgi_application()` per the file's existing
      constraint.
- [x] 4.5 RED: extend `test_consumers.py` — a foreign `Origin` header is
      rejected at the handshake (DD9).
- [x] 4.6 Verify (DD10 acceptance readback — no code change, no Dockerfile
      or `entrypoint.sh` diff): `docker compose up backend`; confirm the
      startup banner reads `Starting ASGI/Daphne version … development
      server at http://0.0.0.0:8000/`. **Confirmed by orchestrator** —
      backend logs read exactly `Starting ASGI/Daphne version 4.2.3
      development server at http://0.0.0.0:8000/`, matching design.md DD10's
      prediction verbatim. `git diff --stat -- backend/Dockerfile
      backend/entrypoint.sh` is empty (see 8.4).
- [x] 4.7 RED: same test file — a `document_update` group message
      re-authorizes membership before relay; when membership was deleted
      after connect, the next broadcast closes the socket with `4403` and
      delivers no payload (DD5).
- [x] 4.8 GREEN: modify `consumers.py` — add `document_update(self, event)`
      handler that re-runs `resolve_membership_for_user`; on failure
      `self.close(4403)`; otherwise sends the event through `DocumentOut`
      (DD5/DD6/DD7) — the raw `codec.document_out(...)` payload still holds
      `UUID`/`datetime` values `json.dumps` rejects, so
      `DocumentOut.model_validate(...).model_dump(mode="json")` runs before
      `self.send_json(...)`.
- [x] 4.9 RED+GREEN: `test_consumers.py` end-to-end — client A's `POST
      .../commands` reaches client B's socket as `{"type":
      "document.update", "document": {…}}` with `revision` incremented
      exactly once, wiring Phase 2's `broadcast_document` to this consumer's
      group.

## Phase 5: Frontend WebSocket Client (DD11, DD13)

- [x] 5.1 Modify `frontend/src/lib/env.ts` — add `wsUrl`, derived from
      `apiUrl` via `.replace(/^http/, "ws")` (no new env var).
- [x] 5.2 RED: `frontend/src/lib/__tests__/uml_documents.test.ts` —
      `openDocumentSocket(orgSlug, docId, handlers)` builds the WS URL from
      `wsUrl` and wires `onmessage`/`onclose`/`onerror`.
- [x] 5.3 GREEN: modify `frontend/src/lib/uml_documents.ts` — add
      `openDocumentSocket(...)` as the sole place that builds a WS URL.
- [x] 5.4 RED: `frontend/src/state/__tests__/document.test.ts` —
      `mergeRemote`: an incoming `revision` lower than or equal to
      `prev.revision` returns the **same object identity**; a higher
      revision replaces it (DD11).
- [x] 5.5 RED: same file — socket `open` (including the very first open)
      triggers exactly one `getDocument()` call through the monotonic
      merge; close codes `4401`/`4403`/`4404` schedule no reconnect; any
      other close (e.g. `1006`) reconnects with capped backoff
      1s→2s→4s→8s→10s (DD13).
- [x] 5.6 RED: same file — unmount closes the socket and clears the pending
      reconnect timer.
- [x] 5.7 GREEN: modify `frontend/src/state/document.ts` — inside
      `useDocument`, add a second effect keyed `[orgSlug, docId]` that opens
      the socket via `openDocumentSocket`, applies `mergeRemote`, and
      implements the reconnect/backoff/refetch behavior from 5.4-5.6.

## Phase 6: Canvas Drag Guard (DD12)

- [x] 6.1 RED: `frontend/src/components/workspace/__tests__/
      DiagramCanvas.test.tsx` — a `revision` bump while `draggingRef` is set
      performs no `cy.json()` call; the `free` event flushes exactly one
      deferred sync.
- [x] 6.2 GREEN: modify
      `frontend/src/components/workspace/DiagramCanvas.tsx` — add
      `draggingRef`/`pendingUpdateRef`, `grab`/`free` handlers that stash
      the latest model and defer the sync effect until `free`.
- [x] 6.3 RED: existing `DocumentPage` test suite (`page.test.tsx`'s
      "removing the pending source class resets the click-click flow..."
      case) — a remote update does not clear `pendingSourceId`/
      `pendingTargetId`; removing the pinned class remotely collapses
      `effectiveSourceId` to `null` (already-correct behavior per
      `page.tsx:67-73`; confirms `page.tsx` needs **zero** diff from this
      cycle's own changes, since `useDocument` never receives a setter for
      either pending id, DD12). No new test needed — this existing case
      already covers it and passes unmodified.

## Phase 7: Documentation

- [x] 7.1 Append DD1-DD13 to `docs/ai/DECISIONS_LOG.md`, one entry per
      decision with rationale, matching the existing entry format.
- [x] 7.2 Update `docs/ai/CURRENT_STATE.md` — note live WebSocket
      convergence for one document, the Redis channel layer, and the
      command-submission locking hardening.

## Phase 8: Verification

- [x] 8.1 Run `cd backend && pytest`; confirm all new
      consumer/service/permissions/codec tests pass with zero regressions.
      **339/339 passed.**
- [x] 8.2 Run `cd frontend && npm test`; confirm all new socket/canvas tests
      pass with zero regressions. **293/293 passed** (52 files), via
      `npx vitest run`.
- [x] 8.3 Run `cd frontend && npm run lint` and `npm run build`; confirm
      clean. **Both clean**; `npx tsc --noEmit` also clean.
- [x] 8.4 Run `docker compose build`; confirm
      `git diff --stat -- backend/Dockerfile backend/entrypoint.sh` is empty
      (DD10). **Confirmed by orchestrator**: `docker compose build backend`
      succeeded (image rebuilt with `channels-redis`); `git diff --stat --
      backend/Dockerfile backend/entrypoint.sh` returns empty.
- [x] 8.5 Confirm `git diff --stat --
      "frontend/src/app/(app)/documents/[docId]/page.tsx"` is empty (DD12).
      **Confirmed by orchestrator**: `git diff --stat` on this file shows
      only 1 changed line, and it is the pre-existing `h-[44rem]` →
      `h-[calc(100vh-12rem)]` canvas-height tweak made before this SDD cycle
      started — not introduced by DD12's drag guard or any Phase 1-7 task.

## Phase 9: Verification Remediation (verify-report.md CRITICAL-1/2)

Both findings were confirmed test-coverage gaps, not implementation defects
(the underlying code was already correct by construction). Both tasks below
are additive test-only changes; zero production code was modified.

- [x] 9.1 RED+GREEN (CRITICAL-1): `backend/apps/uml_documents/tests/
      test_consumers.py` — add
      `test_submitters_own_socket_also_receives_the_broadcast_it_triggered`,
      connecting BOTH the submitter (editor) and the observer (viewer) via
      `WebsocketCommunicator` to the same document's group; the submitter's
      HTTP POST triggers the command; assert BOTH sockets receive
      `{"type": "document.update", ...}` with the incremented revision.
      Passed on first run (10/10 in `test_consumers.py`) — proves the
      spec's "Broadcast on Successful Command" requirement (submitter
      inclusion) at runtime, previously only true by construction.
- [x] 9.2 RED+GREEN (CRITICAL-2): `frontend/src/app/(app)/documents/[docId]/
      __tests__/page.test.tsx` — add "a remote update that keeps the pinned
      class present does not disrupt the pending relationship selection".
      Sets `pendingSourceId` via a node tap, rerenders `DocumentPage` with
      an updated `useDocument` mock (revision/metadata changed, pinned
      class `c1` still present), asserts the "select a target" affordance
      is still shown, then completes the gesture with a target tap. Passed
      on first run (11/11 in `page.test.tsx`) — proves the "pending
      relationship selection survives a remote update" scenario at
      runtime, previously untested.
