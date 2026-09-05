# Proposal: Cycle 2 — Multi-Tenant Identity (Users, Organizations, Memberships)

## Intent

Section 5 of the frozen spec requires "registro e inicio de sesión", section 20 requires
Django Auth + ownership with authorization-filtered queries, and the instructor added a
non-negotiable requirement that the product be a **multi-tenant SaaS**: multiple
organizations, each with members and roles. Today none of that exists. Cycle 1 shipped a
deliberately DB-free domain whose `ProjectDocument.owner_id: str` is an opaque placeholder
(D6) with nothing behind it, the backend has **zero migrations**, and every endpoint is
anonymous.

Cycle 2 establishes the identity and tenancy substrate: the project's first real Django ORM
usage, a custom `User`, `Organization`, `Membership`, session login, and — most importantly —
a **stated, enforced rule for row-level tenant isolation** that every later cycle
(persistence, collaboration, generation) inherits instead of inventing per-endpoint.

Doing this now, before project persistence, is deliberate: `AUTH_USER_MODEL` and the
tenant-key column are the two things that are nearly free before the first migration exists
and expensive to retrofit after real data lands.

## Scope

### In Scope (section 38 cycle shape)

**Objective**: a persisted, session-authenticated identity and tenancy layer with an enforced
row-level isolation contract.

Use cases (project-local identifiers):

- `IDN-C2-1` — Register an account (email + password) and obtain an authenticated session.
- `IDN-C2-2` — Log in and log out via session authentication; identify the current user.
- `IDN-C2-3` — Create, read, rename, and delete an `Organization` carrying a `plan` label.
- `IDN-C2-4` — Manage `Membership`: add an existing user to an organization, assign or
  change their role, remove them, subject to the last-owner invariant.
- `IDN-C2-5` — Enforce row-level tenant isolation: every tenant-scoped read/write is bound
  to exactly one `organization_id`, and a non-member cannot observe that an organization
  exists.

### Out of Scope

- **Persisting `ProjectDocument` / `CanonicalUmlModel`.** They stay in-memory and DB-free.
  No `organization` FK on projects this cycle; no reconciliation of `owner_id` (see Tech Debt).
- **Plan-limit enforcement.** `plan` is stored and returned; nothing reads it to allow or
  deny. "Starter allows 3 members" is a later cycle.
- **Token invitations** (spec §20: single-use token, expiration, email delivery) and any
  email infrastructure. This cycle adds *existing* users by email only (see D5).
- **`ProjectMembership` / project-level roles** (spec §20). Roles are organization-level only.
- **JWT / token auth** (D2), password reset, email verification, SSO, MFA, "roles avanzados"
  (Enterprise marketing perk), audit logging, org-switching UI polish.
- **Frontend and mobile.** No Next.js login/registration UI and no Flutter auth in this
  cycle; the backend contract lands first (see Risks — this is a scheduling risk, not a
  denial that they are needed).
- Channels/realtime authentication (the WS handshake reusing this session) — later cycle.
- Django admin registration for the new models is optional, not a deliverable.

## Capabilities

> Contract with `sdd-spec`. Existing specs in `openspec/specs/`: `uml-domain-model`,
> `project-document`, `uml-validation` — none of their requirements change this cycle.

### New Capabilities

- `user-authentication`: the custom `User` model, email-as-identifier, registration,
  session login/logout, current-user introspection, password policy and hashing.
- `organization-tenancy`: the `Organization` entity, its slug identity, its `plan` label
  (stored, unenforced), and organization CRUD with authorization.
- `organization-membership`: `Membership`, the role set, role assignment, add/remove, and
  the last-owner invariant.
- `tenant-isolation`: the cross-cutting rule that every tenant-scoped row carries
  `organization_id`, how scoping is applied, the escape hatch, and the non-member response
  contract.

### Modified Capabilities

None. `project-document`'s requirements are intentionally untouched; the reconciliation of
`owner_id` with real `User`/`Organization` foreign keys is deferred and logged as tech debt.

## Resolved Decisions

**D1 — One new app, `backend/apps/identity/`.** Not two apps (`accounts/` + `organizations/`).
Rationale: `Membership` is the join between `User` and `Organization`, so splitting them
creates a bidirectional dependency between two migration graphs for what is a single bounded
context (*who you are* and *which tenant you act inside*). A custom `AUTH_USER_MODEL` also has
to exist before the project's first `migrate`; keeping it in one app keeps that ordering
trivially correct. The app is kept architecturally separate from `uml_modeling/` and is
explicitly **allowed** to depend on `django.contrib.auth` and the ORM — the Cycle-1 AST test
forbidding those imports guards `apps/uml_modeling/domain/` only, and must not be widened to
this app. Per D7 of Cycle 1, intra-backend imports stay acyclic and one-directional:
`identity` may later be imported by a project-persistence app; `uml_modeling.domain` imports
nothing and must keep importing nothing.

**D2 — Session authentication, not JWT (fixed by the user).** `django.contrib.auth` sessions
with a custom `User`, exposed through Django Ninja's `django_auth`. Rationale: it is the
smallest correct thing, it reuses the Argon2 hasher and the password validators already
configured in `settings.py`, and it gives CSRF protection and server-side revocation for free.
`PyJWT` is already an installed dependency and spec §20 names it, so JWT remains the expected
later path — most likely driven by the Flutter client, for which cookie handling is awkward.
This cycle must therefore keep authentication behind one seam (a single Ninja auth class) so
adding a token backend later is additive rather than a rewrite of every endpoint.

**D3 — The tenant key travels in the URL path, not in the session.** Tenant-scoped routes are
shaped `/orgs/{org_slug}/...`; the session may store a "last used organization" purely as a UI
convenience default, and that value is never authoritative for authorization. Rationale: a
session-only "active organization" makes every request's tenant implicit — it silently breaks
two browser tabs on two organizations, it makes logs and error reports ambiguous about which
tenant was affected, and it has no meaning at all in a Channels consumer or a management
command, which this project's roadmap definitely reaches. An explicit path segment is
greppable, cacheable, and testable. Organizations are addressed by a unique `slug` over a UUID
primary key rather than a sequential integer, so URLs do not leak tenant count or allow
enumeration.

**D4 — Isolation is explicit-by-construction, not implicit middleware magic.** Every
tenant-scoped model inherits an abstract `TenantScopedModel` carrying a non-null
`organization` FK and a manager exposing `for_organization(org)`; unscoped access requires a
deliberately ugly, greppable `.unscoped()` call. A shared resolver
(`resolve_membership(request, org_slug) -> Membership`) runs per request, verifies the caller's
`Membership`, and hands the endpoint an already-validated `Organization`. **Rejected**: a
middleware/thread-local that stashes a "current organization" and auto-filters a default
manager. Rationale: implicit tenancy is invisible tenancy — the failure mode is not an error
but a silent cross-tenant read, and thread-locals do not survive async Channels consumers,
background jobs, or tests, which is exactly where this project is heading. A test asserting
that every concrete `TenantScopedModel` subclass is reachable only through a scoped path is
part of this cycle. **Response contract**: a non-member requesting an existing organization
receives `404`, not `403`, so organization existence is not leaked to outsiders.

**D5 — Three organization roles: `OWNER`, `EDITOR`, `VIEWER`.** This confirms the marketing
page's "Owner / Editor / Lector" hint, with role codes stored in English and Spanish display
labels rendered by the UI. Rationale: three roles is the minimum that separates the three
genuinely distinct capability classes this product has — tenancy administration (manage
members, roles, organization, plan), model mutation (create and edit projects), and read-only
access (required by the "Lector" promise and by future realtime presence for non-editing
viewers). **Rejected**: a fourth `ADMIN` tier, because it differs from `OWNER` only by "cannot
delete the organization or transfer ownership", which is better expressed as an invariant than
as a role; the Enterprise tier's "roles avanzados" perk is where a richer model belongs.
**Invariant**: an organization MUST always have at least one `OWNER` — the last owner can be
neither removed nor demoted. **Membership creation** is direct-add of an already-registered
user by email; adding an unregistered address requires the token-invitation flow that spec §20
describes and this cycle defers. `(user, organization)` is unique together.

**D6 — Email is the user identifier.** `AbstractBaseUser` + `PermissionsMixin` with
`USERNAME_FIELD = "email"`, unique and case-insensitively normalized, and no `username` field.
Rationale: registration, login, and member-add are all email-driven in the product surface
already designed; keeping a vestigial `username` would create a second identity users must
learn and a second uniqueness rule to defend. `AUTH_USER_MODEL = "identity.User"` is set in the
same commit as the first migration — this project has **no migrations at all yet**, which is
the one moment where a custom user model costs nothing.

**D7 — `plan` is a stored label with no behaviour.** `Organization.plan` is a `TextChoices`
field (`STARTER` / `TEAM` / `ENTERPRISE`, default `STARTER`) matching the landing page's tiers
in `frontend/src/components/landing/Pricing.tsx`. Nothing in this cycle reads it to allow or
deny anything. Rationale: recording the tier now keeps the marketing surface and the data model
honest with a single column, while enforcement without billing, upgrade paths, or a downgrade
policy would be speculative and is a cycle of its own.

## Approach

One new Django app, `backend/apps/identity/`, containing the project's first `models.py` and
first migration.

```
backend/apps/identity/
├── apps.py
├── models.py           # User (+ UserManager), Organization, Membership,
│                       # TenantScopedModel (abstract), Role/Plan TextChoices
├── migrations/0001_initial.py
├── schemas.py          # Ninja/Pydantic request+response schemas
├── services.py         # register_user, create_organization, add_member,
│                       # change_role, remove_member — invariants live here, not in views
├── permissions.py      # resolve_membership(request, org_slug), role requirements
├── api.py              # auth_router, organizations_router, memberships_router
└── tests/
```

- `config/settings.py` gains `apps.identity` in `INSTALLED_APPS`, `AUTH_USER_MODEL`, and the
  cross-origin session settings required for a cookie session shared with a Next.js app on
  another origin: `CORS_ALLOW_CREDENTIALS`, `CSRF_TRUSTED_ORIGINS`, `SESSION_COOKIE_SAMESITE`,
  and `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` — all env-driven, never hardcoded, per the
  existing project convention.
- `config/api.py` mounts the routers on the existing `NinjaAPI` beside `/health`.
- Business invariants (last-owner, unique membership, self-removal, role changes) live in
  `services.py` and are unit-tested independently of HTTP, so the later Channels and
  project-persistence cycles can call them without going through a view.
- Argon2 and the password validators are already configured in `settings.py`; `argon2-cffi`,
  `PyJWT`, and `psycopg2-binary` are already in `backend/requirements/base.txt`. **No new
  dependency is introduced by this cycle.**
- **Testing shifts from DB-free to DB-backed.** This is the first cycle whose tests need a real
  Postgres: `pytest-django`'s `django_db` marker and a reachable `db` service. Exact endpoint
  shapes, schemas, and status codes belong to `sdd-spec` / `sdd-design`, not here.

**Strict TDD Mode is enabled project-wide** (`openspec/config.yaml: strict_tdd: true`).
Implementation in `sdd-apply` MUST follow RED-GREEN-REFACTOR, one use case at a time, with the
first work unit that touches DB-backed testing including the `django_db` fixture setup rather
than deferring it.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/identity/` | New | Entire cycle deliverable: models, migration, services, schemas, routers, tests |
| `backend/apps/identity/migrations/0001_initial.py` | New | The project's **first** migration |
| `backend/config/settings.py` | Modified | `INSTALLED_APPS`, `AUTH_USER_MODEL`, session/CSRF/CORS-credential settings (env-driven) |
| `backend/config/api.py` | Modified | Mount the identity routers on the existing `NinjaAPI` |
| `backend/apps/uml_modeling/` | Untouched | Stays DB-free and auth-free; its AST import guard is not widened |
| `backend/requirements/*` | Untouched | No new dependency |
| `docker-compose.yml`, `.env` | Verify only | Confirm the `db` service is reachable for `migrate` and DB-backed tests |
| `openspec/specs/` | New | Four new capability specs |
| `docs/ai/CURRENT_STATE.md`, `ARCHITECTURE.md`, `DECISIONS_LOG.md`, `NEXT_STEPS.md` | Modified | Dual-documentation convention; D1–D7 go to `DECISIONS_LOG.md` |
| `frontend/`, `mobile/` | Untouched | Deliberately deferred |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Cross-origin cookie sessions (Next.js on another origin) break on CSRF/SameSite | **High** | Treat CORS-credentials + `CSRF_TRUSTED_ORIGINS` + SameSite as first-class, env-driven settings in this cycle; include an explicit CSRF-token acquisition endpoint in the spec; test the cross-origin flow, not just same-origin |
| Cookie sessions are awkward for the Flutter client, forcing an unplanned JWT cycle | Medium | D2 keeps auth behind a single Ninja auth class so a token backend is additive; `PyJWT` is already installed and spec §20 already sanctions it |
| An endpoint forgets to scope a query and leaks across tenants | Medium | D4's explicit `for_organization()` + greppable `.unscoped()` + a test asserting every `TenantScopedModel` subclass is unreachable unscoped; 404-not-403 for non-members |
| A custom `User` model proves wrong later and is expensive to change | Low | This is the cheapest possible moment — zero migrations and zero rows exist today; email-as-identifier is the conventional shape |
| Three roles prove too coarse once project-level collaboration lands | Medium | Org-level roles and future `ProjectMembership` are different axes; adding project roles later is additive, and D5 records why a fourth org role was rejected |
| Test suite regresses from "no database required" to "Postgres required", breaking a contributor's local run | Medium | Keep `uml_modeling` tests DB-free so the split stays visible; document the `db` prerequisite in `CURRENT_STATE.md` |
| Scope creep into project persistence, invitations, or plan enforcement | **High** | The Out-of-Scope list is explicit and the Tech Debt section names the follow-ups; no `organization` FK is added to any project structure this cycle |
| Backend-only cycle leaves nothing demoable to the instructor | Medium | Ninja's auto-generated OpenAPI docs make the endpoints exercisable without a UI; the frontend auth cycle should follow immediately |

## Rollback Plan

Rollback is more expensive than Cycle 1's because this cycle introduces schema, so it is
staged:

1. **Before the first deploy with real data** (the expected case): `python manage.py migrate
   identity zero`, then `git revert` the cycle commits and drop the `apps.identity` /
   `AUTH_USER_MODEL` lines from `settings.py`. Because this is the project's first migration
   and `uml_modeling` has no models, no other table depends on `identity`, so nothing cascades.
2. **After data exists**: reverting `AUTH_USER_MODEL` is not safely reversible in place —
   recovery is to restore the Postgres volume from a dump taken before the first `migrate`. A
   pre-migration dump MUST therefore be part of the first deployment step.
3. Partial rollback of endpoints alone (unmounting the routers in `config/api.py`) is always
   safe and leaves the schema intact.

`uml_modeling`, the frontend, and the mobile client are untouched by any of these paths.

## Dependencies

- **No new package dependencies.** `Django`, `django-ninja`, `argon2-cffi`, `PyJWT`,
  `psycopg2-binary`, and `django-cors-headers` are already in `backend/requirements/base.txt`;
  `pytest-django` is already in `backend/requirements/test.txt`.
- **A reachable PostgreSQL instance** is now a hard prerequisite for running the backend test
  suite and for `migrate` — previously optional. The Docker Compose `db` service already exists.
- Builds on archived Cycle 1 (`canonical-uml-model`) but **does not modify it**.
- **Blocks / is a prerequisite for**: project persistence, realtime collaboration
  authentication, and any authorization-filtered project listing (spec §20).

## Explicit Tech Debt (section 38)

1. **`ProjectDocument` and `CanonicalUmlModel` are NOT organization-scoped.** They remain pure,
   in-memory dataclasses. `ProjectDocument.owner_id: str` stays the opaque Cycle-1 placeholder
   (D6 of Cycle 1) and is **not** reconciled with the real `User` primary key in this cycle.
2. **Reconciling `owner_id` with real FKs is future work.** The project-persistence cycle must
   decide whether the persisted project row carries `owner_id` → `User` FK, `organization_id` →
   `Organization` FK, or both, and whether the pure `ProjectDocument` dataclass keeps its opaque
   string while only the ORM row carries the relationships. Cycle 1's D6 chose an opaque `str`
   precisely to keep both options open; that choice is now due.
3. **No tenant-scoped model actually exists yet.** `TenantScopedModel` ships with `Membership`
   as its only real consumer, so the isolation contract from D4 is proven by unit tests but not
   yet by a second, richer table. It must be re-validated when projects are persisted.
4. `plan` is stored but never enforced (D7); no billing, upgrade, or downgrade path.
5. Token-based invitations with expiry and single use (spec §20), plus all email
   infrastructure, are absent. Members can only be added if they already registered.
6. `ProjectMembership` and project-level roles (spec §20) do not exist; roles are org-level only.
7. Password reset, email verification, MFA, and SSO (Enterprise perk) are absent.
8. No frontend or mobile authentication UI consumes these endpoints yet.
9. No audit trail of membership or role changes.

## Success Criteria

- [ ] A visitor can register with an email and password and receives an authenticated session.
- [ ] A registered user can log in, read their own identity, and log out; the session is
      invalidated server-side on logout.
- [ ] A user can create an organization, becomes its `OWNER` automatically, and can rename or
      delete it.
- [ ] An `OWNER` can add an existing registered user as `EDITOR` or `VIEWER`, change a member's
      role, and remove a member.
- [ ] The last `OWNER` of an organization can be neither removed nor demoted, and the attempt
      fails with a clear, tested error.
- [ ] A user who is not a member of an organization receives `404` for every route scoped to
      it, and never learns whether it exists.
- [ ] Every tenant-scoped query in the codebase goes through `for_organization()`; a test
      asserts no concrete `TenantScopedModel` subclass is reachable through an unscoped default
      path without the explicit `.unscoped()` escape hatch.
- [ ] `Organization.plan` round-trips one of `STARTER` / `TEAM` / `ENTERPRISE` and provably
      gates nothing.
- [ ] `AUTH_USER_MODEL` points at `identity.User`, and `python manage.py migrate` applies
      cleanly from an empty database.
- [ ] `backend/apps/uml_modeling/` is byte-for-byte unchanged and its domain-purity import test
      still passes.
- [ ] `cd backend && pytest` is green against a live Postgres.
- [ ] `docs/ai/CURRENT_STATE.md` and `DECISIONS_LOG.md` reflect the real post-cycle state and
      decisions D1–D7.

## Proposal question round

This phase ran without an interactive channel to the user, so the following product questions
are recorded rather than asked. Answers may adjust the proposal before `sdd-spec` runs;
silence means the stated assumption stands.

1. **Adding an unregistered person.** This cycle assumes an owner can only add someone who has
   already registered (D5). Is "invite by email address, they sign up later" required for the
   instructor demo? If yes, token invitations move from Tech Debt #5 into scope and the cycle
   grows meaningfully.
2. **One user, many organizations.** The model assumes a user may belong to several
   organizations with a different role in each, and creates a fresh organization for each
   registration only if asked. Should registration auto-create a personal organization so no
   user is ever org-less, or is an empty "you belong to no organization yet" state acceptable?
3. **Leaving and deleting.** Can a non-owner member remove themselves from an organization?
   And what should deleting an organization do — hard delete, or soft-delete/archive given that
   projects will eventually hang off it? The proposal currently assumes hard delete, which is
   cheap now and awkward to change after projects are persisted.
4. **Role semantics for the exam demo.** `VIEWER` is assumed to be read-only on models but
   still able to join a realtime session as a passive participant. Is a viewer expected to be
   visible in presence, or invisible?
5. **Frontend timing.** This cycle is backend-only. Is a working login screen needed in the
   same deliverable for grading, or is an OpenAPI-exercisable backend contract sufficient for
   now?
