# Decisions Log

## 2026-09-06 — Cycle 4 apply: implementation complete (tenant-aware-registration-login)

`sdd-apply` implemented all 23 tasks (Phases 1–9) from
`openspec/changes/tenant-aware-registration-login/tasks.md`, following
design.md's DD1–DD8 (extending proposal.md's D1–D8) with strict TDD,
single PR. 185/185 backend tests pass, 87/87 frontend tests pass (17 new),
no new migration file, `backend/apps/{users,organizations}/{models,api,
schemas,constants}.py` byte-for-byte unchanged as required.

**Backend** (Phases 1–4): `organizations/services.py` gained three additive
functions — `build_slug_base`/`derive_workspace_name` (pure, DB-free,
`hypothesis`-property-tested in the new `test_slug_properties.py`) and
`generate_unique_slug` (DB-touching, bounded 5-attempt suffixed retry +
final long-token fallback, raising `OrganizationError` on total exhaustion).
`users/services.py::register_user` became `@transaction.atomic` and now
provisions exactly one `Organization` + `OWNER` `Membership` per
registration via the existing, unchanged `create_organization`; a forced
`OrganizationError` during provisioning rolls the `User` back too (asserted
via `User.objects.count() == 0`). `test_registration_does_not_auto_create_an_organization`
was rewritten into its inverse (`test_registration_provisions_exactly_one_organization`)
per D7's REMOVED+ADDED requirement pair. `seed_demo.py` needed only a
docstring/`help` text correction — each demo user now also owns an
auto-provisioned personal workspace in addition to `acme-demo`, verified by
a new idempotency-safe assertion.

**Frontend** (Phases 5–8): `lib/next-path.ts` gained `isSafeNext` (the
precedence-rule predicate `LoginForm` needs), with `safe()` re-expressed
through it, byte-identical behavior. `state/organizations.ts` gained
`useSetActiveOrg()` (the write half of `useOrganizations`, extracted so the
auth forms can set the active org without mounting the fetch effect).
`LoginForm.tsx`'s submit handler now branches on `listOrganizations()`
directly (never `useOrganizations()`, which would 401 on the login page):
a valid `next` wins unconditionally; otherwise 0 orgs → `/dashboard`
unchanged, 1 org → set active + `/dashboard`, 2+ orgs → the new
`/select-organization` picker; a post-login org-fetch failure degrades to
`/dashboard` without reusing the login error. `RegisterForm.tsx` adopts the
sole provisioned org (fetched via `listOrganizations()` post-register, per
D2's rejection of org data in `UserOut`) before redirecting, non-fatally on
fetch failure. The post-login picker landed as `components/workspace/OrgPicker.tsx`
(presentational, no `activeSlug` — nothing is active yet) plus a new
`app/(gate)/` route group (`SessionGuard` + centered-card shell, no topbar)
hosting `/select-organization`; `OrgSwitcher.tsx`'s private `ROLE_LABELS`
moved to a shared `components/workspace/roleLabels.ts` so both components
read the same translation table.

Deviations from the proposal, all called out and justified in design.md's
Deviations table (DV1–DV5), confirmed exactly as designed with no further
drift:

1. **`state/organizations.ts` gains `useSetActiveOrg()` (DV1)** despite the
   proposal marking it Untouched — additive only, `useOrganizations`'s
   public shape unchanged.
2. **`lib/next-path.ts` gains `isSafeNext` (DV2)**, not in the proposal's
   Affected Areas — required for the `next`-precedence rule; `safe()`
   stayed byte-identical (all 4 pre-existing tests still pass unmodified).
3. **`OrgSwitcher.tsx`'s `ROLE_LABELS` moved to `roleLabels.ts` (DV3)** —
   zero behavior change, confirmed via the pre-existing `OrgSwitcher.test.tsx`
   passing unmodified as an approval test before and after the extraction.
4. **A new `app/(gate)/` route group (DV4)** — cheaper than reusing `(app)`
   (would double-render via `AppTopbar`) or `(auth)` (no session guard).
5. **The provisioned org is read from `GET /api/orgs`, not the register
   response (DV5)** — D2 already rejects org data in `UserOut`; no spec
   text change, same observable scenario.

One process note, not a design deviation: `generate_unique_slug` was
initially added to `organizations/services.py` in the same edit as the pure
helpers (Phase 1), ahead of Phase 2's dedicated RED test. This was caught
and corrected before the RED/GREEN evidence was recorded — the function was
reverted, its RED test written and confirmed failing (`AttributeError`),
then the function was reinstated as the GREEN step, preserving a truthful
TDD cycle for Phase 2.

## 2026-09-06 — Cycle 3 apply: implementation complete (frontend-auth-integration)

`sdd-apply` implemented all tasks from
`openspec/changes/frontend-auth-integration/tasks.md`, across 3 chained PRs
(`stacked-to-main`, mirroring Cycle 2's split), following design.md's DD1–DD7
(extending the proposal's D1–D8) with strict TDD. 67/67 frontend tests pass,
`npm run lint` clean, `next build` succeeds, `backend/` byte-for-byte
unchanged across all 3 PRs.

- **PR 1** (Phase 0–2): `frontend/env.local.example`; `lib/api.ts` rewritten
  as the credentialed CSRF-aware transport seam (D3); domain clients
  `lib/auth.ts`/`lib/organizations.ts`.
- **PR 2** (Phase 3–5): Jotai state (`state/session.ts`, `state/organizations.ts`,
  D5); `SessionGuard` (D1/D4) and `(auth)`/`(app)` route-group layouts (D2);
  `LoginForm`/`RegisterForm` and their routes.
- **PR 3** (Phase 6–8, this entry): the organization panel (`OrgSwitcher`,
  `OrgEmptyState`, `CreateOrgForm`, `AppTopbar`, `/dashboard`); the
  session-aware landing navbar (proposal Q3); full-suite verification and
  this doc sync.

Deviations from design.md/tasks.md, documented inline in `tasks.md` per
phase, summarized here:

1. **`lib/auth.ts` exports `fetchMe()`, object-arg signatures (PR1, Phase 2).**
   design.md's "Interfaces" section (the literal exported TS contract) was
   followed over tasks.md's looser prose (`getMe()`, positional args):
   `register(input)`, `login(input)`, `fetchMe()`, `createOrganization(input)`
   with `slug` **required** — the backend's `OrganizationIn` schema has no
   slug default, so tasks.md's `createOrganization(name)` shorthand cannot
   construct a valid request body against the real backend.
2. **Route-group layouts get no `LayoutRoutes` entry at all (PR2, Phase
   4.1).** DD4 predicted both `(auth)/layout.tsx` and `(app)/layout.tsx`
   would key on `"/"` in the generated `.next/types/routes.d.ts`; the actual
   generated shape after adding both groups is stricter — route groups
   don't appear in that type at all. DD4's conclusion (explicit
   `{children: React.ReactNode}` typing) still holds, but for a stronger
   reason than originally stated.
3. **`/login` needs a `<Suspense>` boundary (PR2, Phase 5.5).** `LoginForm`
   calls `useSearchParams()`; Next's production build fails without a
   wrapping `Suspense` boundary on a page that calls it from a Client
   Component. Not called out in design.md — discovered via the mandatory
   `frontend/AGENTS.md` doc-gate read, not from memory.
4. **`AppTopbar`/`(app)/layout.tsx` wiring deferred from PR2 to PR3 (Phase
   4.7/5.6).** `AppTopbar` (the only logout affordance, task 5.6) didn't
   exist until Phase 6, so `(app)/layout.tsx` temporarily rendered
   `<SessionGuard>{children}</SessionGuard>` only in PR2; PR3 completed the
   originally intended `<SessionGuard><AppTopbar/>{children}</SessionGuard>`
   tree and picked up 5.6's deferred logout test as 6.7.
5. **`OrgSwitcher`/`CreateOrgForm` made purely presentational (PR3, Phase
   6.1/6.5).** Both were designed self-contained (owning their own
   `useOrganizations()` call) in tasks.md's prose, but `AppTopbar` and
   `app/(app)/dashboard/page.tsx` are siblings under `(app)/layout.tsx` (not
   parent/child), so two self-contained hook instances would each fire an
   independent `listOrganizations()` GET on every dashboard visit. Both
   components now take `organizations`/`activeSlug`/`onCreate`/`onSelect` as
   props from their container instead (container-presentational split),
   collapsing 3 potential hook instances down to 2 (one per container,
   architecturally unavoidable given the sibling layout). The corresponding
   unit tests moved from hook-mocking/localStorage-integration style to
   plain prop-driven assertions; the localStorage persistence and
   stale-slug-fallback behavior stay covered by Phase 3's
   `state/__tests__/organizations.test.ts`, and the full "create → appears
   in list → becomes active without refetch" scenario is proven end-to-end
   in `app/(app)/dashboard/__tests__/page.test.tsx`.
6. **Role label "Lector", not "Visualizador" (PR3, Phase 6.2).** proposal.md
   Q2 already establishes "Propietario / Editor / Lector" as the Spanish
   role-label convention; `OrgSwitcher`'s `ROLE_LABELS` was corrected to
   match rather than introduce a second, inconsistent translation for
   `VIEWER`.
7. **`Navbar.tsx` became a Client Component (PR3, Phase 7.2).** Reading
   `useSession()` to show "Ir al panel" vs. "Iniciar sesión"/"Registrarse"
   requires `"use client"`; confirmed the pre-existing, un-mocked
   `app/__tests__/page.test.tsx` (`Home` page test, which renders `<Navbar/>`
   without stubbing `fetch`) still passes — the real `fetchMe()` call
   rejects harmlessly into `useSession()`'s `error` state after the test's
   synchronous assertions already ran, no regression.

8. **`app/(app)/dashboard/page.tsx` is a full Client Component, not the
   Server-Component-shell pattern (PR3, Phase 6.6; found by `sdd-verify`,
   backfilled here).** design.md's DD3 and File Architecture table describe
   every `(app)` page as a thin static server shell delegating to client
   children, the pattern `(auth)/login/page.tsx` and
   `(auth)/register/page.tsx` follow. `dashboard/page.tsx` instead needs
   `useOrganizations()` directly to own the container half of Phase 6's
   container-presentational split (deviation 5 above), so it is `"use
   client"` end to end. This is not a security regression — a fully
   client-rendered page never puts protected data in the server-rendered RSC
   payload at all, which is stricter than the intended pattern, not weaker —
   and it does not break any spec scenario (17/17 still pass). It is,
   however, the precedent for any future `(app)` page: reach for the
   Server-Component-shell pattern by default, and only fall back to a full
   Client Component when the page's own data (not a child's) is needed
   before render, as here.

`docs/ai/CURRENT_STATE.md` reflects the full post-cycle state, including the
manual smoke checklist (real cross-origin cookie flow, task 8.5) not yet run
against a deployed cross-domain origin. Success criteria from `proposal.md`
are met with these eight noted, non-blocking deviations. `sdd-verify` ran
(`pass_with_warnings`, 0 CRITICAL) and flagged deviation 8 above plus a stale
`web-session/spec.md` line describing the pre-DD2 cookie-only CSRF reading,
both fixed in this same pass; `sdd-archive` remains.

## 2026-09-06 — Cycle 2 follow-up: split `identity` into `users` + `organizations`

Pre-merge, `backend/apps/identity/` was refactored into two apps —
`backend/apps/users/` (`User`, `UserManager`, `register_user`/
`authenticate_user`, `auth_router`) and `backend/apps/organizations/`
(`Organization`, `Membership`, `TenantScopedModel`, the tenancy/membership
services, `permissions.py`, `organizations_router`/`memberships_router`) —
at the project owner's explicit request, per Django's one-app-per-domain
convention. `AUTH_USER_MODEL` is now `"users.User"`; `INSTALLED_APPS` lists
both apps in place of `apps.identity`. Done before any real deployment (no
migration or data cost), so this is a rename/split, not a runtime migration.
168/168 backend tests pass (the app-registration test split into two,
+1 net). `openspec/changes/multi-tenant-identity/{proposal,design,tasks}.md`
and their specs were updated to reference the new module paths; the
2026-09-05 entry below is left as the historical record of that PR's
original (single-app) implementation.

## 2026-09-05 — Cycle 2 apply: implementation complete (multi-tenant-identity)

`sdd-apply` implemented all tasks from
`openspec/changes/multi-tenant-identity/tasks.md` in `backend/apps/identity/`,
across 3 chained PRs (`stacked-to-main`), following design.md's DD1–DD7
(recorded there, extending the proposal's D1–D7) with strict TDD. 167/167
backend tests pass (128 baseline + 39 new this PR), zero regression to
`backend/apps/uml_modeling/` (byte-for-byte unchanged) or `/health`.

- **PR 1**: app skeleton, `AUTH_USER_MODEL = "identity.User"`, `User`/
  `Organization`/`TenantScopedModel`/`Membership` models, the project's
  first migration.
- **PR 2**: `services.py` (all invariants — register/authenticate, org
  CRUD, membership add/role-change/remove, the shared `_assert_not_last_owner`
  guard) and `permissions.py` (`resolve_membership`/`require_role`).
- **PR 3**: `schemas.py`, `api.py` (three routers + centralized exception
  handling per DD6), the DD2 cross-origin session/CSRF settings block, and
  `backend/env.example`.

Three deviations from design.md, found only once real HTTP wiring was
exercised against the actually-installed django-ninja version (full
detail in `tasks.md`'s Phase 5 note):

1. **No `NinjaAPI(csrf=True)` kwarg.** The installed django-ninja
   (resolved as 1.7.0 from `requirements/base.txt`'s `>=1.1,<2.0` range)
   has no `csrf` constructor parameter. CSRF is enforced with equivalent
   coverage instead: `django_auth` (ninja's session auth) enforces the
   double-submit check by default for every authenticated unsafe request;
   the two anonymous unsafe endpoints (`register`, `login`) call
   `ninja.utils.check_csrf()` explicitly. Proven behaviorally by
   `test_cross_origin_session.py`.
2. **Mount-prefix path params need an explicit `Path[str]` annotation.**
   `org_slug` lives in `memberships_router`'s mount prefix, not in each
   operation's own relative path; this ninja version does not
   auto-classify it as a path source (it silently defaulted to "query",
   producing 422s) the way design.md's "Ninja binds the prefix path
   parameter" note assumed. Fixed with `ninja.Path[str]`; no behavior
   change beyond the declared parameter source.
3. **`email-validator` added as a new dependency.** design.md's schema
   code block types `email: EmailStr`, which pydantic requires
   `email-validator` for. The proposal's Affected Areas table states "no
   new dependency" for `backend/requirements/*`; that line is now
   inaccurate by this one small, pure-Python package. Kept the design's
   exact schema shape rather than deviate into hand-rolled validation.

`docs/ai/CURRENT_STATE.md` reflects the full post-cycle state. Success
criteria from `proposal.md` are met with these three noted, non-blocking
deviations; `sdd-verify`/`sdd-archive` remain.

## 2026-09-05 — Cycle 1 apply: implementation complete (canonical-uml-model)

`sdd-apply` implemented all 23 tasks from
`openspec/changes/canonical-uml-model/tasks.md` in `backend/apps/uml_modeling/`,
following DD1–DD9 below exactly, with strict TDD (RED→GREEN→REFACTOR,
`pytest` + `hypothesis`, no `pytest-django` DB fixtures needed). 80 backend
tests pass with zero regression to the pre-existing health-check smoke test
(81/81 total). Notes for `sdd-verify`:

- **`EMPTY_ELEMENT_NAME` on whitespace-only names**: implemented as the
  design's noted deliberate superset — a name is empty if
  `name.strip() == ""`, not only `name == ""`. The spec scenario only
  shows the literal empty-string case; whitespace-only is additionally
  covered and tested (`test_empty_element_name_flags_a_whitespace_only_class_name`).
- **Duplicate-name rules anchor on the second (and later) occurrence**,
  not the first: `DUPLICATE_CLASS_NAME`, `DUPLICATE_ATTRIBUTE_NAME`, and
  `DUPLICATE_ENUMERATION_LITERAL` each flag every element after the first
  one sharing a name, so the diagnostic count is deterministic
  (N-1 diagnostics for N same-named elements). Neither the spec nor the
  design mandated a specific anchor; this was the implementation choice.
- **Integration coverage for uml-validation REQ4** (every `path`/
  `element_ref` resolves to a real element) was added as one dedicated
  test (`test_validation_integration.py`) exercising the full 10-rule
  registry together via `validate()`, plus a shared
  `diagnostic_resolves_to_a_real_element()` helper in `tests/factories.py`
  (task 7.6). The helper was not retrofitted into every individual
  per-rule test file (each already asserts `path`/`element_ref` directly
  against its own fixture) — flagged here rather than silently deviating.
- No deviation from DD1–DD9 or the module layout; no models/migrations/
  urlconf/schemas were added, matching the design's explicit scope limit.

## 2026-09-05 — Cycle 1 design: canonical UML domain, project document, validation engine

Architecture decisions for the `canonical-uml-model` change (SDD design phase).
The scope-level decisions D0–D8 are recorded in
`openspec/changes/canonical-uml-model/proposal.md`; the decisions below (DD1–DD9)
are the design-level ones that govern how the code is actually shaped.

- **Three layers inside one Django app, with `domain/` as a leaf.**
  `backend/apps/uml_modeling/` is a registration shell (`apps.py` only): no
  `models.py`, no migrations, no urlconf, no Ninja/Pydantic schemas. Inside it,
  `validation/` reads `domain/` and `documents.py` composes `domain/`; nothing
  imports `validation/`, and `domain/` imports nothing local. The whole app
  imports neither Django, Ninja, nor Pydantic, so the single `validate()` entry
  point stays callable from every future channel (HTTP, Channels, XMI import,
  assistant, generation) exactly as document section 10 requires.
- **DD1 — Two enforcement layers, deliberately distinct.** Construction
  invariants raise `ValueError`/`TypeError` from `__post_init__`; model-level
  semantic problems become `Diagnostic`s. The specs demand both: a class-typed
  attribute and an empty `owner_id` must be impossible to construct, while
  duplicate names and dangling references must be reportable, navigable, and
  fixable rather than fatal.
- **DD2 — The boundary between those layers.** Construction rejects only what is
  *unrepresentable or mistyped*; it never rejects user-fixable content. Concretely,
  `Multiplicity(-1, None)` and `Multiplicity(2, 1)` MUST remain constructible,
  because otherwise the `INVALID_MULTIPLICITY` diagnostic could never be produced.
  `Multiplicity` is therefore a deliberately unvalidated value object.
- **DD3 — Frozen dataclasses, `tuple` for ordered collections.** `frozen=True`
  combined with `list` fields is only shallow immutability. Real snapshots are
  needed by the later command bus, undo/redo, and optimistic-revision cycles, and
  immutable sequences also make `hypothesis` shrinking deterministic. The specs'
  word "list" is read as "ordered sequence".
- **DD4 — Explicit static rule registry over a decorator registry.** The ten
  Cycle-1 rules are listed as a `RULES: tuple[Rule, ...]` in `validation/engine.py`,
  importing named functions from `validation/rules/`. This gives deterministic
  diagnostic order, no import-time side effects, no hidden global mutable state,
  a greppable list, and a registry that a test can assert on directly. A `@rule`
  decorator would have made ordering depend on import order.
- **DD5 — Registry injected via default argument**: `validate(model, rules=RULES)`.
  The public one-argument call matches the spec exactly, while the engine's
  aggregation and its "never short-circuit" behaviour can be tested with fake
  rules without touching the real ten.
- **DD6 — Rules keep the bare `(CanonicalUmlModel) -> Iterable[Diagnostic]`
  signature** and build their own local id→element dictionaries, instead of the
  engine passing a shared prebuilt index. This preserves the spec's "callable in
  isolation" requirement with zero setup, and at class-diagram scale (tens of
  elements) the repeated dictionary construction is negligible. Adding an optional
  second parameter later is non-breaking.
- **DD7 — `ElementId = NewType("ElementId", str)`, generated from `uuid4().hex`.**
  Strings serialize to JSON and XMI with no adapter, `NewType` costs nothing at
  runtime, and ids are already the alphabet of the diagnostic `path` grammar.
- **DD8 — Pure mutation helpers take an explicit `now: datetime`.**
  `ProjectDocument.with_model(...)` / `.with_layout(...)` never call
  `datetime.now()` internally, keeping the domain clock-free and deterministic;
  revision and timestamp tests need no `freezegun` or monkeypatching.
- **DD9 — `DiagnosticCode` is a `StrEnum`, path builders live in
  `validation/diagnostics.py`.** The ten codes are fixed and closed, so an enum
  prevents typos and enables exhaustiveness tests; the slash-rooted `path` grammar
  is part of the diagnostic contract and belongs next to `Diagnostic` rather than
  in a separate module.
- **Two refinements to the proposal's file layout.** `validation/rules/structure.py`
  was added because `CLASS_WITHOUT_ATTRIBUTES` fits none of the four originally
  proposed rule files, and no separate `paths.py` was created (see DD9).
- **Normative generalization direction.** For `RelationshipKind.GENERALIZATION`,
  `source` is the specific (child) and `target` is the general (parent). Cycle
  detection runs an iterative DFS over the child→parent digraph and emits exactly
  one diagnostic per cycle, anchored at the lowest-sorted participating class id,
  so the diagnostic count is deterministic. A self-generalization is a length-1
  cycle reported as `GENERALIZATION_CYCLE`; `SELF_ASSOCIATION` stays scoped to
  `ASSOCIATION`.
- **No sequence diagram this cycle.** `openspec/config.yaml` requires sequence
  diagrams for realtime/collaboration flows (Django Channels); no realtime flow is
  in Cycle 1's scope, so the rule does not apply. A `validate()` call-flow diagram
  is documented instead, as the only non-obvious control flow in the change.

## 2026-08-31 — Scope pivot to the real exam spec + stack corrections + dual-mobile clarification + SDD adoption

- **Scope pivot: the real project is the CASE-tool exam spec, not the
  originally-scaffolded generic CRUD app.** `product-04-next-django.md`
  (repo root) was found to be the actual, authoritative exam statement — an
  offline-first collaborative CASE tool for UML class diagramming with
  manual/voice/image/XMI input converging into a `CanonicalUmlModel`,
  realtime collaboration, and automatic generation of a Spring Boot
  backend + Next.js frontend + Android (Capacitor) app from the modeled
  domain. The previously scaffolded Django+DRF/Next.js/Flutter CRUD
  skeleton was infrastructure only and never described this real scope.
  `docs/ai/*` is being reconciled to describe the real target, while
  `product-04-next-django.md` itself stays frozen as the authoritative
  source (per its own section 1) and is never edited to reflect progress.
- **Stack corrections applied** (in progress by parallel workstreams at
  the time of this entry, not yet fully confirmed — see
  `CURRENT_STATE.md`): backend moves from Django REST Framework to
  **Django Ninja**; adds **Django Channels + Daphne** (ASGI) for realtime;
  adds **Argon2** password hashing + **PyJWT**; bootstraps
  **pytest + pytest-django + hypothesis**. Frontend adds
  **Tailwind CSS + shadcn/ui + Cytoscape.js + cytoscape-fcose + Jotai**;
  bootstraps **Vitest + React Testing Library**. Cypress (E2E) bootstrap is
  planned but not yet started by anyone.
- **Dual mobile requirement clarified — both mandatory, not conflicting.**
  The document's own generated-output Android strategy (section 26) is
  **Next.js PWA + Capacitor**, wrapping the same generated Next.js code —
  this applies only to applications the tool generates for its end users.
  Separately, the course instructor explicitly and firmly requires this
  project itself to ship a real **Flutter** mobile client (`mobile/`) for
  the main CASE tool. These are two independent requirements from two
  independent sources; neither supersedes or replaces the other, and both
  must be satisfied.
- **Adopted SDD (Spec-Driven Development) going forward, hybrid mode:
  OpenSpec files + Engram.** The spec document's own section 1 mandates
  deriving use cases, grouping them into cycles, proposing acceptance
  criteria, implementing one use case at a time, and maintaining a
  document of real state separate from the vision document — this is
  effectively an SDD-shaped requirement written directly into the exam
  statement. `openspec/` was initialized at the repo root (`sdd-init`) to
  formalize this: every future feature (starting with `CanonicalUmlModel`
  + `ProjectDocument`/`DiagramLayout` + the validation engine) goes through
  explore → propose → spec → design → tasks → apply → verify → archive,
  with Engram persisting cross-session decisions and context.

## Original scaffold decisions

- **Django settings package named `config`** — keeps the settings/urls/wsgi/asgi
  package name generic and decoupled from any specific app or product name.
- **Env vars via django-environ, no hardcoding** — secrets, hosts, DB
  credentials, and CORS origins must never be committed or baked into code;
  `environ.Env` centralizes reading them with sane `.env` file support.
- **psycopg2-binary over psycopg3** — chosen for tutorial/documentation
  ubiquity: most Django docs, tutorials, and Stack Overflow answers still
  assume psycopg2, and the binary wheel avoids build-toolchain friction in
  the Docker image.
- **CORS via django-cors-headers** — the Next.js frontend is a separate
  origin from the Django API, so cross-origin requests need to be
  explicitly allow-listed rather than silently blocked or wide open.
- **Tailwind intentionally NOT added** — it was not requested by the spec;
  adding it now would be an unnecessary dependency/opinion for a bare
  scaffold.
- **Flutter not dockerized** — mobile apps are built/run via the Flutter
  SDK against emulators/physical devices on the host, not inside a Linux
  container; there is no meaningful way to "run" a mobile app in a
  server-style container.
- **Multi-stage Dockerfiles with dev/prod targets (backend + frontend)** —
  a single Dockerfile serves both live-reload local development (bind
  mounts, dev server) and a leaner production image (built artifacts,
  gunicorn/`next start` or standalone output) without duplicating base
  layers.
- **Env-example files written without the leading dot** (`env.example`,
  `env.local.example`) — the Write/Bash sandbox used to generate this
  scaffold refuses any file path containing the substring `.env`, even for
  placeholder content. Documented in each file and in the root README;
  rename them locally (e.g. `mv env.example .env`) to restore the
  conventional dotfile name.
