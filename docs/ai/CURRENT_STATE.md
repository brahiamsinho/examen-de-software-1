# Current State

This is the "real state document" required by `product-04-next-django.md`
section 1 — kept independent of the frozen spec, updated as work actually
lands. Be honest here even when it's unflattering: this file should never
claim more progress than actually exists.

## Where the project actually is

**As of 2026-09-19** (`main` at `0aa211a`, 20 archived SDD cycles, backend
631 tests, no open change): the UML modeling core (canonical model,
validation engine, command bus, persistence, canvas with locking), multi-
tenant identity/auth, realtime collaboration, the UML → RelationalModel
mapper, and three slices of the Spring Boot generator all exist and are
archived. The generator emits Java **source text only** for one table at a
time (`domain/`, `persistence/`, `application/`, `api/`, `errors/`).

What does **not** exist: compilation of any generated Java (§37 item 13),
inheritance generation, filtering/search, the generated `config/` layer,
OpenAPI, Postman, the Domain Manifest, a generated frontend/mobile,
the assistant, voice, XMI and image → UML. Undo/Redo and Presence (§37 items
7 and 10) have no dedicated archived cycle and are not verified as
implemented. See `HANDOFF_LATEST.md` for the stage summary and
`NEXT_STEPS.md` for what comes next.

> The per-area sections below (Backend, Frontend, Mobile, SDD / planning,
> Domain) were appended cycle by cycle; where an older sentence in them
> contradicts this paragraph, this paragraph wins.

### Backend

- Dockerized Django project skeleton exists (`config` settings package,
  empty `apps/`).
- **In progress by a parallel workstream**: migration from Django REST
  Framework to Django Ninja, addition of Django Channels + Daphne (ASGI),
  addition of Argon2 password hashing + PyJWT, and bootstrap of
  pytest + pytest-django + hypothesis, including a health-check endpoint
  and one smoke test. This is **not confirmed complete** as of this
  reconciliation — its final result was not available to verify.
- **Postgres is now a hard test prerequisite.** With `backend/apps/users/` and
  `backend/apps/organizations/` landing the project's first migrations, `pytest-django` builds its test
  database from the `POSTGRES_*` env vars on every run — a reachable `db`
  service (`docker compose up -d db backend`) is required before
  `docker compose exec backend pytest` (or `cd backend && pytest`) will
  work. `apps/uml_modeling/` itself stays DB-free and unaffected.
- **SDD Cycle 4** (`tenant-aware-registration-login`) is **fully
  implemented**, single PR: `register_user` (`apps/users/services.py`) is
  now `@transaction.atomic` and provisions exactly one `Organization` +
  `OWNER` `Membership` per registration via three additive
  `organizations/services.py` helpers — `build_slug_base`/
  `derive_workspace_name` (pure, `hypothesis`-property-tested) and
  `generate_unique_slug` (bounded 5-attempt suffixed retry + final
  long-token fallback, raising `OrganizationError` on exhaustion, which
  rolls the whole registration transaction back). `create_organization`,
  every model, and every migration stay byte-for-byte unchanged. 185/185
  backend tests pass. `sdd-verify`/`sdd-archive` are the remaining steps.

### Frontend

- Dockerized Next.js (App Router, TypeScript) skeleton exists with a
  minimal `env.ts`/`api.ts` pair.
- **In progress by a parallel workstream**: addition of Tailwind CSS +
  shadcn/ui + Cytoscape.js + cytoscape-fcose + Jotai, and bootstrap of
  Vitest + React Testing Library, including one smoke test. This is **not
  confirmed complete** as of this reconciliation — its final result was
  not available to verify.

- **SDD Cycle 3** (`frontend-auth-integration`) is **fully implemented**
  across its 3 chained PRs (`stacked-to-main`): a credentialed, CSRF-aware
  transport seam (`lib/api.ts` — `credentials: "include"` on every request,
  automatic CSRF priming/retry, typed `ApiError`/`NetworkError`); domain
  clients `lib/auth.ts` (`register`/`login`/`logout`/`fetchMe`) and
  `lib/organizations.ts` (`listOrganizations`/`createOrganization`), one
  module per backend Django app; Jotai session/organization state
  (`state/session.ts`'s `useSession()` discriminated union
  `loading|authenticated|anonymous|error`, `state/organizations.ts`'s
  `useOrganizations()` with `localStorage`-persisted active org); a
  `SessionGuard` Client Component gating the `(app)` route group
  (`/dashboard`), with `(auth)` hosting `/login`/`/register`; the
  organization panel (`OrgSwitcher`, `OrgEmptyState`, `CreateOrgForm`,
  `AppTopbar` with the app's only logout affordance); and a session-aware
  landing navbar ("Iniciar sesión"/"Registrarse" when anonymous, "Ir al
  panel" when authenticated). 67/67 frontend tests pass, `npm run lint`
  clean, `next build` succeeds (`/`, `/login`, `/register`, `/dashboard`
  all prerender as static `○`), `backend/` byte-for-byte unchanged.
  `sdd-verify`/`sdd-archive` are the remaining steps. Deviations from
  design.md are documented inline in `tasks.md` (Phase 2, 4.1, 5.5, 6.1,
  6.5, 7.2) — most notably: `lib/auth.ts` exports `fetchMe()` (not
  `getMe()`) with object-arg signatures, matching design.md's authoritative
  "Interfaces" contract over tasks.md's looser prose; `OrgSwitcher` and
  `CreateOrgForm` were made purely presentational (props, not their own
  `useOrganizations()` call) to avoid duplicate `listOrganizations()`
  fetches between the sibling `AppTopbar`/`dashboard/page.tsx` containers
  under `(app)/layout.tsx` — a small remaining duplicate-fetch tradeoff
  (exactly 2 `useOrganizations()` instances per dashboard visit, one per
  container) is accepted as low-risk since the request is an idempotent GET
  converging on the same shared `organizationsAtom`.

- **SDD Cycle 5** (`ssr-protected-routes`) is **fully implemented**, single
  PR, frontend-only (`backend/` byte-for-byte unchanged): `(app)/layout.tsx`
  and `(gate)/layout.tsx` are now `async` Server Components that `await
  requireUser(nextPath)` (new `lib/server-session.ts`) as their first
  statement, before any protected markup can be emitted — a session cookie's
  *validity*, not merely its presence, is checked server-side on every
  direct/no-JS request, closing the gap where `SessionGuard`'s client-only
  gate let an anonymous `curl`/deep-link request receive the full RSC
  payload. `getServerUser()` (React `cache()`-wrapped) forwards the whole
  cookie jar verbatim to `GET {internalApiUrl}/api/auth/me` with
  `cache: "no-store"`; `200` → `User`, `401`/`403` → `null` (redirect to
  `/login?next=<safe(nextPath)>`), anything else (5xx, network failure) →
  throws, caught by `requireUser` and treated as "render normally, let
  `SessionGuard`'s client retry state own it" — an outage is never
  misread as a logout. New `lib/env.ts::internalApiUrl` (falls back to
  `apiUrl`) lets the frontend container reach `backend:8000` instead of
  `localhost:8000` (which is the container itself). `SessionGuard.tsx` and
  its test are byte-for-byte untouched — this is additive server-side
  defense-in-depth, not a replacement for the existing client-side skeleton/
  error/retry UX. 102/102 frontend tests pass (15 new: 13 in
  `server-session.test.ts`, 2 in `env.test.ts`), zero regressions.
  **Deployment precondition**: the browser must send the Django `sessionid`
  cookie to the Next.js origin — true for localhost and same-parent-domain
  deploys, false for a split `app.x.com`/`api.y.com` deployment (every
  authenticated user would bounce to `/login`). **Deviation found during
  manual verification, not anticipated by design.md**: `docker-compose.yml`'s
  `backend` service needed `ALLOWED_HOSTS` to additionally include `backend`
  (the Compose service name) — Django's `CommonMiddleware` otherwise rejects
  the `Host: backend:8000` header the frontend container's server-side fetch
  sends, returning `400 Bad Request` for every `/api/auth/me` call from
  inside the Docker network (misread by `getServerUser` as a 5xx-class
  failure, so it degraded silently to the client-retry fallback rather than
  the intended redirect — sd-apply added `backend.environment.ALLOWED_HOSTS`
  to `docker-compose.yml` and updated `backend/env.example` to document it).
  A second finding: design.md's Technical Approach claims the 307 response
  has nothing flushed to the body ("nothing has flushed when the gate
  throws"); verified against the real running stack (both `next dev` and a
  `next build && next start` production run) that Next.js 16.3.3 actually
  streams a small inert `<html id="__next_error__">` document shell
  alongside every `redirect()`-triggered 307 — it carries a `NEXT_REDIRECT`
  error digest and dev-mode stack trace, never dashboard/org data or
  `AppTopbar`/`SessionGuard`-authenticated markup, so the underlying spec
  requirement ("the response body contains no protected-route markup")
  still holds, but DD8's literal `rg -c "<html" body.txt` verification
  command does not — see `openspec/changes/ssr-protected-routes/tasks.md`
  Phase 6 for the full 8-step manual verification transcript.
  `sdd-verify`/`sdd-archive` are the remaining steps.

- **SDD Cycle 4** (`tenant-aware-registration-login`) is **fully
  implemented**, single PR: `LoginForm.tsx` now resolves the caller's
  organizations via `listOrganizations()` directly (never
  `useOrganizations()`, which would fire an anonymous fetch on the login
  page) and branches the post-login destination — a valid `next` wins
  unconditionally over org-count branching; otherwise 0 orgs → `/dashboard`
  unchanged, 1 org → set active + `/dashboard`, 2+ orgs → the new
  `/select-organization` picker (`app/(gate)/select-organization/page.tsx`,
  under a new `(gate)` route group with its own `SessionGuard` + centered
  card, no topbar). `RegisterForm.tsx` adopts the sole provisioned org
  (read from `GET /api/orgs` post-register, since org data is deliberately
  excluded from `UserOut`) before redirecting. New shared pieces:
  `lib/next-path.ts::isSafeNext` (the precedence-rule predicate, with
  `safe()` re-expressed through it, byte-identical), `state/organizations.ts
  ::useSetActiveOrg()` (the write half of `useOrganizations`, consumed by
  both the hook and the auth forms), `components/workspace/OrgPicker.tsx`
  (presentational, no `activeSlug`), and `components/workspace/roleLabels.ts`
  (shared with `OrgSwitcher`, preventing translation-table drift). 87/87
  frontend tests pass (17 new), `backend/` and every pre-existing
  frontend behavior unchanged. `sdd-verify`/`sdd-archive` are the
  remaining steps.

- **SDD Cycles 7–9** (`uml-canvas-ui`, `uml-command-bus`, `uml-document-persistence`,
  merged 2026-09-12, then `uml-canvas-remove-ui`, this entry) brought the
  UML canvas domain to the frontend for the first time: `lib/uml_documents.ts`
  (domain client for `apps/uml_documents`, one module per backend Django
  app), a Cytoscape.js `DiagramCanvas`, `AddClassForm`/`AddAttributeForm`/
  `AddRelationshipControl` for growing a diagram, and `state/document.ts`'s
  `useDocument` (POST command → refetch → `setDocument`). **Cycle 9
  (`uml-canvas-remove-ui`, this entry) closes the create/destroy gap** those
  cycles deliberately deferred: `RemoveClassControl` (class select + a
  mandatory confirmation step stating the exact client-derived cascade
  count), `RemoveAttributeControl` (class → attribute select, immediate
  submit), and `RemoveRelationshipControl` (relationship select labelled by
  endpoint names + kind, immediate submit) are wired into
  `documents/[docId]/page.tsx` under a new "Eliminar" heading. `UmlCommandIn`
  now covers 6 of the backend's 7 command shapes — only `RenameClass` has no
  UI. `backend/` diff is empty for this cycle: all three remove commands,
  their schemas, and cascade behavior already existed and were already
  tested. `sdd-verify`/`sdd-archive` remain.
  **Known documentation gap**: Cycles 7–8 (`uml-canvas-ui`,
  `uml-command-bus`, `uml-document-persistence`) never received their own
  `DECISIONS_LOG.md`/`CURRENT_STATE.md` sync entries when they merged; this
  paragraph is the first mention of the canvas domain existing at all in
  this file. A full backfill of those three cycles' individual design
  decisions is out of `uml-canvas-remove-ui`'s scope and remains pending.

- **SDD Cycle 10** (`uml-document-list`) is **fully implemented**, single PR,
  additive on both sides (`backend/apps/uml_documents/models.py` and its
  migrations byte-for-byte unchanged): `/dashboard` now lists an
  organization's documents instead of only redirecting to one just created.
  `GET /orgs/{slug}/documents` (`services.list_documents`, gated exactly like
  the existing single-document read — no `require_role`, so `VIEWER` reads
  too) returns a lightweight `DocumentSummaryOut` (`id`/`name`/`revision`/
  `updated_at`, `name` flat unlike `DocumentOut.metadata.name`), newest-updated
  first. `lib/uml_documents.ts::listDocuments` + `state/documents.ts`'s
  `useDocuments` (local `useState`, cloned from `useMembers`'s shape, not a
  Jotai atom) feed the new presentational `DocumentList` (real `next/link`
  rows, empty-state copy instead of `null` when there are zero documents).
  The "Nuevo Diagrama" entry point moved into a new "Mis Diagramas" header
  row, above the list, and now discloses the unmodified `CreateDocumentForm`
  behind a click instead of always rendering it. 319/319 backend tests pass
  (8 new), 251/251 frontend tests pass (23 new), zero regressions.
  `sdd-verify`/`sdd-archive` remain.

- **SDD Cycle 11** (`uml-relationship-kinds`) is **fully implemented**,
  single PR, `backend/` diff empty (`RelationshipIn.kind` was already the
  full 4-kind `Literal`; only the frontend had hardcoded `association`). The
  canvas now supports all 4 UML 2.5 relationship kinds with per-kind
  notation, not just association: `AddRelationshipControl` gained a `Tipo de
  relación` select (defaulting to `association`) that drives the submitted
  `AddRelationship.relationship.kind`; selecting `generalization` hides both
  multiplicity selects and always submits `"1"`/`"1"` (UML 2.5 has no
  multiplicity there), with the earlier multiplicity choice preserved (not
  reset) if the user switches back. `DiagramCanvas`'s `toElements` now
  copies `relationship.kind` into edge `data`, and the exported `STYLE`
  renders each kind's UML 2.5 terminator — hollow triangle
  (generalization), hollow diamond (aggregation, at the first-clicked/
  "whole" `source` end), filled diamond (composition, same end), plain line
  (association, no terminator) — while leaving the pinned `edge.self-loop`
  geometry untouched. 278/278 frontend tests pass (18 new). `sdd-verify`/
  `sdd-archive` remain.

### Mobile

- `mobile/` is a bare Flutter scaffold (default counter-app template plus
  an `AppConfig` reading `API_BASE_URL`). It does not yet implement
  anything domain-specific for the CASE tool. This is the instructor-
  mandated real Flutter client for the main tool (see `PROJECT_VISION.md`
  and `ARCHITECTURE.md`) — still to be designed and built out.

### Manual smoke checklist — Cycle 3 real cross-origin cookie flow (not automated)

Unit tests stub `fetch` at the module boundary (proposal D8); no MSW, no real HTTP.
This checklist is the deferred proof for the real browser session-cookie round trip,
per design.md's Testing Strategy and proposal Risk table. Run with the backend at
`http://localhost:8000` and the frontend at `http://localhost:3000`:

1. **Register → reload → still authenticated.** Visit `/register`, submit a unique
   email + password, land on `/dashboard` authenticated. Reload the page: `useSession()`
   re-fetches `GET /api/auth/me` and the session stays authenticated (no bounce to
   `/login`) — proves the `HttpOnly` session cookie survives a hard reload.
2. **Logout → `/`.** From the panel, click "Cerrar sesión". Confirm the request hits
   `POST /api/auth/logout`, the client session clears, and the browser lands on `/`
   (proposal Q4 — a deliberate logout is an exit, not a prelude to `/login`).
3. **Backend stopped + load `/dashboard` → retry panel, not `/login`.** Stop the
   backend container, then visit `/dashboard` directly. `GET /api/auth/me` fails as a
   network error, not a `401` — confirm the guard renders the retry panel ("No pudimos
   verificar tu sesión...") and does **not** redirect to `/login` (DD5's "an outage must
   not resolve to anonymous").

Not yet run against a real deployed cross-domain origin (`app.example.com` →
`api.example.com`) — the CSRF body-token fallback path (DD2) is unverified beyond the
cookie fast path exercised by local dev (proposal's Open Question 1 in design.md).

### End-to-end testing

- Cypress bootstrap is planned but has not been started by anyone yet.

### SDD / planning

- `openspec/` is initialized at the repo root (config + specs + changes
  directories exist). **SDD Cycle 1** (`canonical-uml-model`) has run
  through explore → propose → spec → design → tasks → apply; `sdd-verify`
  and `sdd-archive` are the remaining steps for this change.
- **SDD Cycle 2** (`multi-tenant-identity`) is **fully implemented**
  across its 3 chained PRs (`stacked-to-main`, review-budget guard), and
  was subsequently split from a single `apps/identity/` app into two
  apps per Django's one-app-per-domain convention:
  `backend/apps/users/` (`AUTH_USER_MODEL = "users.User"`, the `User`
  model, `register_user`/`authenticate_user` services, `auth_router`) and
  `backend/apps/organizations/` (`Organization`, `TenantScopedModel`/
  `Membership` models, the tenancy/membership services and
  `_assert_not_last_owner` guard, `permissions.py`
  (`resolve_membership`/`require_role`), `organizations_router`/
  `memberships_router`) — the project's **first migrations** (PR 1);
  services + permissions (PR 2); schemas, routers mounted in
  `config/api.py`, and the DD2 cross-origin session/CSRF settings block
  in `config/settings.py` plus `backend/env.example` (PR 3). 168/168
  backend tests pass. `sdd-verify`/`sdd-archive` are the remaining steps.
  Three deviations from design.md were required and are documented in
  `tasks.md`'s Phase 5 note: (1) the installed django-ninja 1.7 has no
  `NinjaAPI(csrf=True)` kwarg — CSRF is enforced equivalently via
  `django_auth`'s built-in check plus an explicit `check_csrf()` call on
  the two anonymous unsafe endpoints; (2) `org_slug` (a mount-prefix path
  segment) needed an explicit `Path[str]` annotation per operation,
  since this ninja version does not auto-detect prefix-only path params;
  (3) `email-validator` was added as a new, small dependency to support
  `EmailStr` in the schemas — the proposal's "no new dependency" line is
  now inaccurate by that one package.
- **SDD Cycle 12** (`2026-09-14-realtime-uml-collaboration`) is **implemented**
  (Phases 1–7 of `tasks.md`; Phase 8 verification below). Two members of one
  organization now see each other's edits on one UML document with no
  reload: `submit_command` (`apps/uml_documents/services.py`) is
  `@transaction.atomic` and locks the row with `_get_row(...,
  for_update=True)` chained AFTER `.for_organization(...)` (DD1 — closes a
  lost-update race between two concurrent commands that predated this
  feature), then broadcasts the resulting document via
  `transaction.on_commit` (DD2) to a sync `DocumentConsumer`
  (`apps/uml_documents/consumers.py`) joined to group `uml-doc-{doc_id}`
  (DD3). The consumer authorizes with membership only — no `require_role`
  (DD4), via the new `resolve_membership_for_user(user, org_slug)` extracted
  in `apps/organizations/permissions.py` — and re-authorizes on every
  relay, closing `4403` if membership was revoked (DD5). The wire payload is
  the existing `DocumentOut`, promoted from `api._document_out` to
  `codec.document_out(document)` (DD6/DD7), so a broadcast and a `GET
  .../documents/{docId}` stay byte-identical. `config/asgi.py`'s
  `"websocket"` route now serves `apps/uml_documents/routing.py` through
  `OriginValidator(AuthMiddlewareStack(URLRouter(...)),
  CORS_ALLOWED_ORIGINS)` (DD9) — no new env var, no CSRF equivalent (the
  socket performs no writes). `CHANNEL_LAYERS` uses
  `channels_redis.core.RedisChannelLayer` from discrete `REDIS_HOST`/
  `REDIS_PORT` env vars (DD8; a new `redis:7-alpine` Compose service with a
  healthcheck backs it). On the frontend, `useDocument`
  (`state/document.ts`) gained a second effect that opens
  `openDocumentSocket` (`lib/uml_documents.ts`, the sole place that builds a
  WS URL, derived from `lib/env.ts`'s `wsUrl`), merges every
  incoming/refetched document monotonically by revision so a duplicate or
  out-of-order delivery costs zero re-renders (DD11), and reconnects with
  capped exponential backoff (1s→2s→4s→8s→10s) on any non-terminal close —
  `4401`/`4403`/`4404` are terminal, so a revoked/unauthenticated client
  never hammers the handshake (DD13). `DiagramCanvas.tsx` gained a
  `draggingRef`/`pendingUpdateRef` guard so a remote update mid-drag defers
  its `cy.json()`/layout sync until the `free` event, instead of
  re-laying-out under the user's cursor (DD12); `pendingSourceId`/
  `pendingTargetId` needed no guard — verified unreachable from
  `useDocument`, so `app/(app)/documents/[docId]/page.tsx` has zero diff
  from this cycle. The "does `runserver` serve WebSocket in dev?" question
  is resolved as yes (DD10, `daphne` precedes `django.contrib.staticfiles`
  in `INSTALLED_APPS`) — the acceptance banner readback and the
  Redis-service healthcheck still need one `docker compose build && docker
  compose up` restart to observe, deferred to the maintainer per this
  project's docker-lifecycle convention. Full regression:
  339/339 backend (`pytest`) and 293/293 frontend (`vitest run`) pass, plus
  clean `eslint`/`tsc --noEmit`/`next build`.
- **SDD Cycle 14** (`2026-09-16-uml-class-operations`) is **implemented**
  (Phases 1–14 of `tasks.md`). **Operations are now reachable end to end** —
  the domain (`UmlOperation`/`UmlClass.operations`), codec round-trip, and
  `empty_element_name` validation all existed with zero production callers
  before this cycle; `AddOperation`/`RemoveOperation` (mirroring
  `AddAttribute`/`RemoveAttribute` verbatim) open the write path: closed
  command union 7→9, `_HANDLERS` 7→9, `CommandIn`/`UmlCommandIn` discriminated
  unions both grow by 2, `AddOperationForm`/`RemoveOperationControl` mount
  under the existing "Agregar"/"Eliminar" panels, and `DiagramCanvas` renders
  a second UML-notation compartment below attributes (`+ crearUsuario():
  Usuario`), separated by its own divider — additive-only layout math keeps
  a zero-operations class byte-identical to before this cycle. A new
  `duplicate_operation_name` rule (name-only, scoped per class) brings the
  fixed validation registry from **10 rules to 11**. **v1 scope**:
  `parameters` stays UI-unreachable — the domain/codec/persistence already
  carry a non-empty tuple losslessly, but no form collects one; the wire
  schema (`UmlOperationIn`) has no `parameters` field at all, and the mapper
  always constructs `parameters=()`. 384/384 backend tests pass (25 new),
  335/335 frontend tests pass (17 new), clean `eslint`/`next build`.
  `sdd-verify`/`sdd-archive` are the remaining steps.
- **SDD Cycle 13** (`2026-09-15-uml-node-position-sync`) is **implemented**
  (Phases 1–7 of `tasks.md`). **The document socket is now bidirectional** —
  Cycle 12 gave `DocumentConsumer` only `document_update`; this cycle adds
  its first `receive_json`, handling `node.claim`/`node.position`/
  `node.release` with a per-message `require_role(OWNER, EDITOR)` re-check.
  Dragging a class node now claims it via a new ephemeral Redis lock module
  (`apps/uml_documents/locks.py` — `SET NX PX` + owner-token compare-and-
  delete/compare-and-expire Lua scripts, TTL 10s, key
  `uml-lock:{doc_id}:{class_id}`), streams throttled (50ms) live positions
  to every other connection with **zero database write**, and on release
  persists the final position through a new `services.save_layout_position`
  — a `submit_command` sibling under the same row lock that never touches
  `dispatcher.apply()` or the `UmlCommand` union. **`ProjectDocument.layout`
  is now live**: `with_layout` (built in Cycle 1, never called in
  production before this cycle) has its first real caller, and `layout` is
  pruned of any class id absent from the current model on every persisted
  release. The two lock domains stay deliberately disjoint — a held Redis
  claim never blocks, delays, or is consulted by `RemoveClass` or any other
  `UmlCommand`, verified end-to-end in `test_consumers.py`. On the
  frontend, `toElements` (`DiagramCanvas.tsx`) now seeds each node's
  initial position from `document.layout.positions` instead of always
  running a full `fcose` layout on load; a foreign-held node is
  `ungrabify()`d with a dashed-amber affordance, and `state/document.ts`
  exposes `sendClaim`/`sendPosition`/`sendRelease` plus a `locks` state and
  a ref-based live-position listener so a remote drag moves a node with
  zero re-render. 359/359 backend tests pass (20 new, across the new
  `test_locks.py` and additions to `test_services.py`/`test_consumers.py`),
  317/317 frontend tests pass (24 new, across `DiagramCanvas.test.tsx`,
  `document.test.ts`, `uml_documents.test.ts`, `page.test.tsx`), clean
  `eslint`/`tsc --noEmit`. `sdd-verify`/`sdd-archive` are the remaining
  steps.

### Domain

- **SDD Cycle 1 is implemented** (`backend/apps/uml_modeling/`, change
  `canonical-uml-model`): `CanonicalUmlModel` (alias `UmlModel`) with
  classes, enumerations, relationships, and generation metadata;
  `ProjectDocument`/`DiagramLayout` (identity, opaque `owner_id`, pure
  revision increment via `with_model`/`with_layout`); and the single
  validation `engine.validate()` with its full 10-rule Cycle-1 registry
  (`EMPTY_ELEMENT_NAME`, `DUPLICATE_CLASS_NAME`, `DUPLICATE_ATTRIBUTE_NAME`,
  `DUPLICATE_ENUMERATION_LITERAL`, `UNKNOWN_ATTRIBUTE_TYPE`,
  `INVALID_RELATIONSHIP_ENDPOINT`, `INVALID_MULTIPLICITY`,
  `GENERALIZATION_CYCLE`, `SELF_ASSOCIATION`, `CLASS_WITHOUT_ATTRIBUTES`).
  This is a pure, DB-free, framework-agnostic domain layer: no
  `models.py`, no migrations, no urlconf, no Ninja/Pydantic schemas, no
  persistence, and no auth wiring yet — `owner_id` is a validated-opaque
  string only. 80 backend tests cover it (TDD, `pytest` + `hypothesis`),
  with zero regression to the pre-existing health-check smoke test.
- **SDD Cycle (`2026-09-17-uml-relational-mapping`) is implemented**
  (`backend/apps/relational_mapping/`, spec §21): a pure, DB-free
  `map_to_relational(CanonicalUmlModel) -> RelationalModel` — the first stage
  of the future Spring Boot generator pipeline. `domain/` (`Table`, `Column`,
  `PrimaryKey`, `ForeignKey`, `UniqueConstraint`, `Index`, `EnumType`,
  `RelationalModel`, all frozen) + `mapping/` (`errors`, `naming`, `mapper`,
  a 5-stage pipeline: hierarchy -> enumerations -> tables -> relationships ->
  freeze). Settled rules: synthetic UUID PK on every table unconditionally,
  Single Table inheritance with a verbatim-class-name `class_type`
  discriminator, native-`ENUM`-flavored enumerations, composition FKs always
  `NOT NULL CASCADE` (nullable only for the documented self-composition tree
  exception), association/aggregation FK nullability from the referenced
  end's `Multiplicity.lower`, and join tables for many-to-many. A new
  `MULTI_PARENT_GENERALIZATION` `ERROR` rule (`apps.uml_modeling`) is the
  primary defense against a multi-parent tree; the mapper's own
  `MultipleGeneralizationParentsError`/`GeneralizationCycleError`/
  `UnknownEnumerationError`/`DanglingRelationshipEndpointError` are
  defense-in-depth only — the mapper never calls `validate()`. Zero Django/DB/
  Java imports in the new module. 442/442 backend tests pass (58 new).
  `sdd-verify`/`sdd-archive` are the remaining steps.
- `UmlCommand`/Command Bus, the Cytoscape canvas, persistence (Django
  ORM), and realtime collaboration are implemented for the UML domain
  (see Backend/Frontend sections above). The Domain Manifest, the
  assistant pipeline, and all AI/voice/image/XMI features are **not
  started**.
- **SDD Cycle (`2026-09-18-spring-boot-generator-core`) is implemented**
  (`backend/apps/spring_generator/`, spec §22, item 12 — first slice): a
  pure, DB-free, filesystem-free `generate_table_sources(table, *,
  base_package="com.modelia.generated") -> GeneratedSources`, turning one
  `relational_mapping.domain.schema.Table` (scalar columns only, no FK,
  no discriminator, no enum) into in-memory Java source for one JPA
  `@Entity` class (`domain/`) and one Spring Data JPA repository
  interface (`persistence/`), at `src/main/java/<base_package
  path>/{domain,persistence}/...`. `domain/` (`GeneratedFile`/
  `GeneratedSources`, frozen) + `emit/` (`errors`, `naming`, `javatypes`,
  `context`, `renderer`, `templates/*.java.j2`), mirroring
  `relational_mapping`'s `domain/`+`mapping/` split one cycle later in
  the same pipeline. Settled rules: boxed Java types only (never
  primitives), `TIMESTAMPTZ -> java.time.OffsetDateTime`,
  `TEXT -> String` + `columnDefinition = "TEXT"`, the PK gets `@Id` +
  `@GeneratedValue(strategy = GenerationType.UUID)` and explicitly no
  `@NotNull`, non-PK non-nullable columns get `@NotNull` (never
  `@NotBlank`), a `VARCHAR` with a `length` gets `@Size(max=length)`, a
  typed `UngeneratableTableError` hierarchy rejects any FK/discriminator/
  `ENUM`/composite-or-non-UUID-PK table in a fixed check order before any
  render, a Java reserved-word field name gets a trailing `_` while
  `@Column(name=...)` preserves the original DB name, and every emitted
  file's field order, import grouping, and text is byte-identical across
  repeated calls on the same input. Jinja2 (`emit/templates/*.java.j2`,
  loaded from `emit/templates/` — never Django's app-root `templates/`,
  which would expose the `.java.j2` files to Django's own `APP_DIRS`
  template loader) owns all emitted Java text; a LibCST guard
  (`tests/test_no_concat_guard.py`) parses every module under `emit/`
  and fails on manual string `+`, `str.join`, `%`-formatting, or any
  f-string in the generator's own Python source (`.format()` and a
  reassignment-loop comma-join are the allowed alternatives) — it never
  parses Java and never runs at render time. 93 new backend tests
  (structural-only per proposal D2: expected paths, class/field/
  annotation lines, brace balance — no `javac`, no Java parser), full
  suite green. `sdd-verify`/`sdd-archive` are the remaining steps.
- **SDD Cycle (`2026-09-18-spring-boot-generator-application-api-layer`) is
  implemented** (`backend/apps/spring_generator/`, spec §22, item 12 —
  third slice, extends both cycles below): `generate_table_sources(table)`
  grows from 2 to **6** emitted files per call, in fixed layer order
  `domain/`, `persistence/`, `application/dto/<E>RequestDto.java`,
  `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`,
  `api/<E>Controller.java` (DD50a) — a generated backend now has a callable
  REST surface for the first time. A new sibling entry point
  `generate_shared_error_sources(*, base_package) -> GeneratedSources`
  (DD42, mirroring DD30's `generate_enum_source` precedent) emits exactly
  two per-project `errors/` files once, never per-`Table`. **A real defect
  is fixed in the same slice**: the DTO layer flattens every relationship
  field to a raw FK `UUID` scalar (e.g. `categoryId`, never the related
  entity type) instead of letting JPA's EAGER-fetch `@ManyToOne`/
  `@OneToOne` serialize nested entities, which would have contradicted
  spec §27's flat-FK-id UI contract. FK resolution in the service always
  goes through `relatedRepository.findById(...).orElseThrow(...)` — never
  `EntityManager.getReference()`, which would defer the not-found check
  past the point the service can convert it into the typed 404. **DD48
  amends DD18**: the entity's no-arg constructor is now `public`, not
  `protected` — a compilation prerequisite, since DD39 puts the service in
  a different package (`application`) than the entity (`domain`), and
  `protected` would not compile across that boundary. Resource path
  segments are pluralized and kebab-cased by a new dependency-free
  `naming.resource_path_segment` (DD45; `order_line` → `/api/order-lines`).
  55 new backend tests (`spring_generator` grows from 133 to 188), full
  631-test backend suite green, single PR (`size:exception`, confirmed by
  the user over the session's 400-line budget). `sdd-verify`/`sdd-archive`
  are the remaining steps.
- **SDD Cycle (`2026-09-18-spring-boot-generator-relationships-enums`) is
  implemented** (`backend/apps/spring_generator/`, spec §22 — second
  slice, extends the core cycle above): `generate_table_sources(table)`
  now emits FK-bearing and enum-bearing tables instead of rejecting them.
  A `Column` that is part of a FK renders as `@ManyToOne`+`@JoinColumn`,
  or `@OneToOne`+`@JoinColumn(..., unique = true)` when the FK's column
  set exactly matches one of the table's own `unique_constraints`; a
  self-referencing FK (`Category.parent -> Category`) generates cleanly
  with no special-casing and no import, because the referenced
  entity/enum always lives in the same `{base_package}.domain` package
  (DD27). A `Column` with `enum_type_name` set renders as
  `@Enumerated(EnumType.STRING)` typed `pascal_case(enum_type_name)`. New
  pure `generate_enum_source(enum_type, *, base_package) -> GeneratedFile`
  (`emit/renderer.py` + new `emit/templates/Enum.java.j2`) turns a
  `relational_mapping.domain.schema.EnumType` into a standalone
  annotation-free Java `enum`, with SCREAMING_SNAKE_CASE constants
  (`in_progress`/`InProgress`/`in-progress`/`IN PROGRESS` all converge on
  `IN_PROGRESS`) and the verbatim source label preserved via a
  `getLabel()` accessor — the DD32 recovery hook for a future DDL/DTO
  slice. `reject_out_of_scope`'s check set narrowed to non-UUID/composite
  PK, discriminator, and (newly) composite FK, in that fixed order;
  `ForeignKeysUnsupportedError` was renamed to
  `CompositeForeignKeyUnsupportedError` (no back-compat alias — its only
  two consumers were inside this app) and a new
  `UngeneratableSourceError` root now sits above both
  `UngeneratableTableError` and the new `UngeneratableEnumError` branch
  (`EmptyEnumTypeError`, `DuplicateEnumConstantError`). `javatypes.py` is
  untouched — FK and enum columns bypass its scalar `ColumnType` lookup
  entirely at both call sites in `context.py` (the field builder and the
  import-collection loop), which is what makes a bare `ENUM` column
  without `enum_type_name` the only remaining path to a rejection instead
  of a `KeyError`. 40 new backend tests (`spring_generator` grows from 93
  to 133, including `test_rejections.py`'s DD35-order rewrite and
  `test_determinism.py`'s widened `hypothesis` strategies proving DD36
  needed no new ordering rule), full 576-test backend suite green,
  single PR (`size:exception`, confirmed by the user over the session's
  800-line budget). `sdd-verify`/`sdd-archive` are the remaining steps.

## Pending (status against spec section 37)

This is the spec's own recommended implementation order, kept as a reference
list. **Status as of 2026-09-19:** items 1–6, 8, 9 and 11 are done and
archived; item 12 is partial (see the paragraph after the list); items 7
(Undo/Redo) and 10 (Presence) have no dedicated archived cycle; items 13–26
are not started.

1. `CanonicalUmlModel`
2. `ProjectDocument` + `DiagramLayout`
3. Validation engine
4. `UmlCommand` + Command Bus
5. Canvas (Cytoscape.js)
6. Persistence (Django ORM)
7. Undo/Redo
8. Auth + ownership
9. Realtime (Django Channels + Daphne)
10. Presence
11. UML → RelationalModel
12. Spring Boot backend generator
13. Generated backend compilable
14. OpenAPI
15. Postman collection
16. Domain Manifest
17. Frontend generator
18. Generic CRUD (generated apps)
19. `AssistantCommand`
20. Text → command (ONNX Runtime + Optimum)
21. Executor
22. STT (Vosk, Spanish, local)
23. Voice → command
24. Android via Next.js PWA + Capacitor (generated output)
25. XMI 2.1
26. Image → UML (Moondream)

SDD Cycle 1 (`canonical-uml-model`, items 1–3) was verified and archived on
2026-09-05; the command bus (item 4) was archived on 2026-09-12. Both are in
`openspec/changes/archive/`.

Item 12 (Spring Boot backend generator) now has three slices implemented:
`2026-09-18-spring-boot-generator-core` (scalar-only tables, `domain/`+
`persistence/`), `2026-09-18-spring-boot-generator-relationships-enums`
(FK relationship fields, enum fields, and standalone enum source), and
`2026-09-18-spring-boot-generator-application-api-layer` (DTOs, service,
REST controller, and shared error handling — `application/`, `application/
dto/`, `api/`, `errors/`; see the Domain section above). Still out of
scope for a future slice: Single Table inheritance generation,
bidirectional `@OneToMany`, `@ManyToMany`/`@JoinTable`, filtering/search
(pending a §33 generation-metadata extension), relation-navigation
sub-resource endpoints, `validation/`/`config/` layer generation, and an
orchestrating caller that walks a whole `RelationalModel`, combines
per-table/per-enum output, and calls `generate_shared_error_sources`
exactly once per generated project (including cross-artifact Java
class-name collision detection). Item 13 (generated backend compilable)
still has no JVM/Gradle host anywhere in repo infra and remains its own
future cycle.
