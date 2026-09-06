# Tasks: Cycle 2 — Multi-Tenant Identity

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1800–2600 (26 new files, 16 tests; ~700 authored source + ~1100+ test lines + ~100 generated migration) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (skeleton+models+migration) → PR 2 (services+permissions) → PR 3 (schemas+api+cross-origin+cleanup) |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main (resolved by user for this session) |

Decision needed before apply: No — resolved: stacked-to-main, 3 chained PRs
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | App skeleton, `AUTH_USER_MODEL`, models, first migration | PR 1 | `cd backend && pytest apps/identity/tests/test_apps.py apps/identity/tests/test_models_*.py apps/identity/tests/test_tenant_scoping.py apps/identity/tests/test_isolation_contract.py` | `python manage.py migrate` against empty Postgres `db` service | `migrate identity zero`; drop `apps.identity` from `INSTALLED_APPS` + revert `AUTH_USER_MODEL` |
| 2 | Services + permissions (invariants, no HTTP) | PR 2 | `cd backend && pytest apps/identity/tests/test_services_*.py apps/identity/tests/test_permissions.py` | N/A — pure service-layer unit tests, no server needed | Revert `services.py`/`permissions.py`; PR 1 models remain valid standalone |
| 3 | Schemas, API routers, CSRF/session settings | PR 3 | `cd backend && pytest apps/identity/tests/test_api_*.py apps/identity/tests/test_cross_origin_session.py` | `python manage.py runserver` + `curl` against `/api/auth/csrf`, `/api/orgs` | Unmount routers in `config/api.py`; leaves schema/DB intact per design's stated safe partial rollback |

## Phase 0: App Skeleton & `AUTH_USER_MODEL` Wiring (blocks all migrations)

- [x] 0.1 Create `backend/apps/identity/__init__.py` (empty).
- [x] 0.2 Create `backend/apps/identity/apps.py`: `IdentityConfig(AppConfig)`, `name="apps.identity"`, `label="identity"`.
- [x] 0.3 `backend/config/settings.py`: add `"apps.identity"` to `INSTALLED_APPS` and set `AUTH_USER_MODEL = "identity.User"`.
- [x] 0.4 RED: `tests/test_apps.py` — app registered, label exactly `identity`.
- [x] 0.5 GREEN: confirm 0.4 passes via 0.1–0.3.

## Phase 1: Test Infrastructure

- [x] 1.1 Create `tests/__init__.py` and `tests/conftest.py` (`csrf_client`, `auth_client`, `owner`, `member`, `outsider`, `organization` fixtures).
- [x] 1.2 Create `tests/factories.py` (`make_user`, `make_organization`, `make_membership`, `make_org_with_roles`, unique-email counter).

## Phase 2: Models & First Migration

- [x] 2.1 Create `constants.py` (`Role`, `Plan` `TextChoices`).
- [x] 2.2 Create `errors.py` (`IdentityError` + all 8 subclasses with `code`).
- [x] 2.3 RED: `test_models_user.py` (CI email uniqueness, Argon2 hash, `USERNAME_FIELD`, no `username`, manager methods).
- [x] 2.4 GREEN: `models.py` — `UserManager`, `User` (UUID pk, `Lower("email")` constraint per DD7).
- [x] 2.5 RED: `test_models_organization.py` (slug uniqueness, `plan` default `STARTER`, UUID pk).
- [x] 2.6 GREEN: `models.py` — `Organization`.
- [x] 2.7 RED: `test_tenant_scoping.py` (`for_organization` scoping, raising default manager, `.unscoped()`, reverse access).
- [x] 2.8 GREEN: `models.py` — `TenantScopedQuerySet`, `TenantScopedManager`, `TenantScopedModel` (DD1).
- [x] 2.9 RED: `test_models_membership.py` (unique-together, role choices, cascade, viewer same fields).
- [x] 2.10 GREEN: `models.py` — `Membership(TenantScopedModel)`.
- [x] 2.11 RED: `test_isolation_contract.py` (enumerate `TenantScopedModel` subclasses).
- [x] 2.12 GREEN: confirm 2.11 passes against current model set.
- [x] 2.13 Run `makemigrations identity`; hand-review `0001_initial.py` (Lower-email constraint, `(user,organization)` unique, `(organization,role)` index, swappable dependency).
- [x] 2.14 `migrate` against empty Postgres; document the `db` service prerequisite in `docs/ai/CURRENT_STATE.md`.

> **Deviation note (PR 1, discovered during apply):** tasks 0.4/0.5 assumed
> `test_apps.py` could go GREEN from the app skeleton + `AUTH_USER_MODEL`
> setting alone. In practice, `django.setup()` populates
> `django.contrib.admin`, which unconditionally imports
> `django.contrib.auth.admin` → `get_user_model()` at import time — so
> **any** test run (even one that touches no DB) raises
> `ImproperlyConfigured` once `AUTH_USER_MODEL = "identity.User"` is set
> without a concrete `User` model existing. This confirms, more strictly
> than tasks.md's phase split implies, design.md's own rollout note that
> steps 1–2 and 3–4 "must be one commit." Practical effect on this PR's
> TDD trail: 0.4 (RED) and 2.3 (RED, `test_models_user.py`) were both
> written and confirmed RED before any model code existed; `models.py` was
> then authored as one atomic GREEN covering `User`, `Organization`,
> `TenantScopedModel`, and `Membership` together (rather than 4 separate
> GREEN steps), because `makemigrations`/any DB-touching test needs the
> whole app's model graph to be internally consistent before it can run at
> all. `test_models_organization.py`, `test_tenant_scoping.py`,
> `test_models_membership.py`, and `test_isolation_contract.py` were still
> written before running the suite (so each is a real, independent
> assertion of the spec, not written after the fact to match existing
> code) but passed on first execution against that already-complete
> `models.py`, rather than driving four more incremental RED cycles.
>
> Separately, `migrate` was verified against a genuinely empty database by
> creating a throwaway Postgres database (`identity_clean_check`) inside
> the running `db` service and running `python manage.py migrate` against
> it (all 19 migrations, including `identity.0001_initial`, applied
> cleanly; the throwaway database was dropped afterward) — the shared dev
> database already had `auth`/`admin`/`contenttypes`/`sessions` migrations
> applied from before this PR's `AUTH_USER_MODEL` swap, so migrating it
> in-place would not have proven a from-empty bootstrap.

## Phase 3: Services

- [x] 3.1 RED: `test_services_auth.py` (duplicate email, weak password, generic invalid-credentials).
- [x] 3.2 GREEN: `services.py` — `register_user`, `authenticate_user`.
- [x] 3.3 RED: `test_services_organizations.py` (creator→OWNER atomically, rename, hard-delete cascade, duplicate slug).
- [x] 3.4 GREEN: `services.py` — `create_organization`, `rename_organization`, `delete_organization`, `list_user_organizations`.
- [x] 3.5 RED: `test_services_memberships.py` (add-by-email, unregistered email, duplicate membership, role change, self-removal, last-owner demote+remove).
- [x] 3.6 GREEN: `services.py` — `add_member`, `change_member_role`, `remove_member`, `list_memberships`, `_assert_not_last_owner` (DD3, `select_for_update`).

## Phase 4: Permissions

- [x] 4.1 RED: `test_permissions.py` (`resolve_membership` 404 for unknown slug and non-member; `require_role` rejects wrong roles).
- [x] 4.2 GREEN: `permissions.py` — `resolve_membership`, `require_role` (DD4).

> **Deviation note (PR 2, same pattern as PR 1):** `test_services_auth.py`
> was written and confirmed RED before `services.py` existed (3.1 → RED,
> 3.2 → GREEN as one atomic file covering `register_user` and
> `authenticate_user`, since Python has no way to partially define a
> module). `services.py` was then authored complete (all ten functions +
> `_assert_not_last_owner`) in that same GREEN step, because
> `create_organization`/`add_member`/etc. share imports and the
> `_assert_not_last_owner` helper — splitting the file across three
> separate GREEN commits would have meant temporarily-broken imports for
> functions not yet under test. `test_services_organizations.py` and
> `test_services_memberships.py` were still written as independent
> assertions of their specs (not reverse-engineered from passing code) but
> passed on first execution against the already-complete `services.py`
> (5/5 and 10/10 respectively), rather than driving two more incremental
> RED cycles. Same for `permissions.py`: 4.1 was confirmed RED
> (`ImportError: cannot import name 'permissions'`) before the file
> existed; 4.2 authored both functions together and all 6 assertions
> passed first run.

## Phase 5: Schemas, API & Cross-Origin Settings

- [x] 5.1 Create `schemas.py` (all request/response schemas per design's API Surface table).
- [x] 5.2 RED: `test_api_auth.py` (`/auth/csrf`, `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/me`).
- [x] 5.3 GREEN: `api.py` — `auth_router`, `register_exception_handlers`; `config/api.py` mounts routers (see deviation note: `NinjaAPI(csrf=True)` does not exist on the installed django-ninja 1.7 — CSRF is enforced equivalently, see below).
- [x] 5.4 RED: `test_api_organizations.py` (CRUD status codes, 404-not-403 non-member contract).
- [x] 5.5 GREEN: `api.py` — `organizations_router`.
- [x] 5.6 RED: `test_api_memberships.py` (list/add/role-change/remove, error bodies).
- [x] 5.7 GREEN: `api.py` — `memberships_router`.
- [x] 5.8 `backend/config/settings.py`: add DD2 cross-origin session/CSRF block (env-driven); created `backend/env.example` (docker-compose.yml's referenced filename — no `.env.example` convention existed anywhere in the repo yet) documenting all env vars including the 6 new DD2 ones and the deployment matrix.
- [x] 5.9 RED: `test_cross_origin_session.py` (token acquisition, rejection without token, acceptance with `X-CSRFToken`, `SameSite=None ⇒ Secure`).
- [x] 5.10 GREEN: confirm 5.9 passes via 5.8.

> **Deviation note (PR 3, discovered during apply):** design.md's exact API
> Surface code block specifies `NinjaAPI(csrf=True)`. The installed
> django-ninja version resolved from `requirements/base.txt`'s
> `>=1.1,<2.0` range is **1.7.0**, whose `NinjaAPI.__init__` has no `csrf`
> kwarg at all (confirmed via `inspect.signature`). In this version, CSRF
> enforcement is delegated entirely to auth classes: `ninja.security.
> SessionAuth` (aliased `django_auth`) enforces the double-submit check by
> default (`csrf=True` is its own constructor default) for every
> authenticated, unsafe-method request. `organizations_router` and
> `memberships_router` are mounted with `Router(auth=django_auth)`;
> `/auth/logout` and `/auth/me` use `auth=django_auth` explicitly. The two
> genuinely anonymous unsafe endpoints (`POST /auth/register`,
> `POST /auth/login`) have no auth class for ninja to hook CSRF into, so
> they call `ninja.utils.check_csrf(request)` directly and return its
> `HttpResponseForbidden` verbatim when validation fails — functionally
> identical to design.md's stated intent ("anonymous POST /auth/register
> and POST /auth/login are CSRF-protected too") without the nonexistent
> kwarg. `test_cross_origin_session.py` proves this behaviorally (token
> acquisition, 403 without token, 201 with the correct `X-CSRFToken`
> header, and a 403 on an authenticated unsafe request without a token).
>
> Second deviation: `org_slug` lives in `memberships_router`'s *mount
> prefix* (`/orgs/{org_slug}/members`), not in each operation's own
> relative path string. The installed ninja version's `ViewSignature` only
> derives `path_params_names` from the operation's own registered path, so
> it does not auto-classify a prefix-only path segment as a "path" source
> the way design.md's "Ninja binds the prefix path parameter" note
> assumes — it silently defaulted to "query", producing 422s. Fixed by
> annotating `org_slug: Path[str]` (ninja's explicit `Path` type) on every
> `memberships_router` operation; Django's URL resolver already supplies
> the value from the mounted prefix as a view kwarg regardless of this
> per-operation path model, so the fix is additive and changes no
> behavior other than the parameter's declared source.
>
> Third: design's exact schema code block types `email: EmailStr`, which
> requires the `email-validator` package (a `pydantic[email]` transitive
> extra) that was not installed and not listed in `requirements/base.txt`.
> The proposal's Affected Areas table states "no new dependency", which
> is now inaccurate by one small, pure-Python package. Added
> `email-validator>=2.1,<3.0` to `requirements/base.txt` and installed it
> in the running container rather than deviate from the design's exact,
> explicitly-requested schema shape (hand-rolling email validation would
> have been the larger deviation). Flagged as a risk in the apply report
> for the archiving decision.

## Phase 6: Cleanup

- [x] 6.1 `rg "\.unscoped\(\)"` audit — confirm `resolve_membership` is the sole call site. Result: exactly 3 files match under `backend/apps/identity/` — `models.py` (the method's own definition + internal use inside `for_organization`), `permissions.py` (`resolve_membership`, the sole production call site), and `tests/test_tenant_scoping.py` (test coverage). No other production call site exists.
- [x] 6.2 Update `docs/ai/CURRENT_STATE.md`: first migration, `AUTH_USER_MODEL` swap, Postgres test-db prerequisite, and PR 3 completion (this cycle is now fully implemented).
