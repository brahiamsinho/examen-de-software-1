# Current State

This is the "real state document" required by `product-04-next-django.md`
section 1 — kept independent of the frozen spec, updated as work actually
lands. Be honest here even when it's unflattering: this file should never
claim more progress than actually exists.

## Where the project actually is

**Nothing from the real UML/CASE-tool domain exists yet.** No
`CanonicalUmlModel`, no canvas, no collaboration, no code generation, no
AI/voice/XMI features have been built. What exists is a dockerized
infrastructure skeleton that is mid-migration from its original generic
scaffold onto the corrected stack, plus SDD tooling that has been
initialized but not yet used for a real cycle.

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
- `UmlCommand`/Command Bus, the Cytoscape canvas, persistence (Django
  ORM), realtime collaboration, the relational mapper, the Spring Boot
  generator, the Domain Manifest, the assistant pipeline, and all
  AI/voice/image/XMI features are **not started**.

## Pending (SDD Cycle 1 and beyond)

Per the spec's own recommended implementation order (section 37), the next
work — once explored/proposed via SDD — should proceed roughly in this
order:

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

SDD Cycle 1 (see `NEXT_STEPS.md`) targeted items 1–3 only:
`CanonicalUmlModel`, `ProjectDocument`/`DiagramLayout`, and the
validation engine. Implementation (`sdd-apply`) is complete; `sdd-verify`
and `sdd-archive` remain before item 4 (`UmlCommand` + Command Bus)
starts as its own cycle.
