# Exploration: Email Verification & Password Reset (Mailpit)

Scope: add a dev-only Mailpit mail-catcher, email verification at
registration, and a forgot-password/reset-password flow. Does not
implement anything — output is options with tradeoffs for `sdd-propose`.

## Current State

Confirmed by direct reads (not just a grep pass): **zero existing email
infrastructure**.

- `backend/config/settings.py` — no `EMAIL_BACKEND`/`EMAIL_HOST`/`EMAIL_PORT`
  anywhere; fully env-driven via `django-environ`, `DEBUG` already computed
  as `env.bool("DEBUG", default=False)`.
- `backend/apps/users/models.py` — custom `User(AbstractBaseUser,
  PermissionsMixin)`, UUID pk, email-only `USERNAME_FIELD`. No
  `is_verified`/`email_verified_at` field.
- `backend/apps/users/services.py` — `register_user` is
  `@transaction.atomic`: creates the `User`, then calls
  `create_organization` in the **same** atomic block, and returns the
  user. `authenticate_user` raises one generic `InvalidCredentialsError`
  for both unknown-email and wrong-password — an anti-enumeration pattern
  already established that the reset-request endpoint must mirror.
- `backend/apps/users/api.py` — `auth_router` has `/csrf` (GET,
  `auth=None`), `/register` and `/login` (POST, `auth=None`, manual
  `_reject_unless_csrf_valid` double-submit CSRF check), `/logout`/`/me`
  (`auth=django_auth`). `register()` calls Django's `login(request, user)`
  immediately after `register_user` succeeds — **registration currently
  creates a fully usable, logged-in session with zero verification gate**.
  Domain errors map centrally through `_ERROR_STATUS_MAP` in
  `register_exception_handlers`.
- `backend/apps/users/errors.py` / `schemas.py` — flat `UserError`
  subclasses with stable `code` strings; thin Ninja `Schema` request/
  response classes.
- `docker-compose.yml` — **single file**; dev/prod split by each service's
  Dockerfile `target: dev|prod`, not by a separate compose file. No
  `docker-compose.prod.yml` exists. The established dev-only pattern is
  `entrypoint.sh` gating `seed_demo` on `settings.DEBUG` at container
  boot — this is the pattern to mirror for Mailpit, not a compose-file
  split.
- `backend/env.example` — fully env-var driven, commented by section; a
  new `EMAIL_*` block should follow the same style.
- Frontend (`frontend/src/lib/auth.ts`, `RegisterForm.tsx`, `api.ts`) —
  thin per-domain client functions wrapping `apiFetch`; `ApiError.detail`
  carries the backend's JSON error message; forms are client components
  with local `useState`, `router.replace()` on success, Jotai
  `sessionAtom`. New screens should reuse this exact shape.

## Affected Areas

- `backend/config/settings.py` — add env-driven `EMAIL_BACKEND`/
  `EMAIL_HOST`/`EMAIL_PORT`.
- `backend/apps/users/models.py` — new `is_verified` field + migration;
  a token model (or two).
- `backend/apps/users/services.py` — `register_user` composition with
  email sending (must use `transaction.on_commit`, never send inside the
  atomic block); new service functions for verify/reset.
- `backend/apps/users/api.py`, `errors.py`, `schemas.py` — new endpoints,
  error codes, schemas.
- `docker-compose.yml` + `backend/env.example` — Mailpit service (SMTP
  1025, web UI 8025), `EMAIL_*` vars.
- `frontend/src/lib/auth.ts`, `frontend/src/components/auth/`,
  `frontend/src/app/` — new client functions, forms, routes.

## Approaches

1. **Stateless `PasswordResetTokenGenerator` (Django built-in, HMAC, no DB
   table) for reset; custom token model only for verification.**
   - Pros: no new table for reset, leverages well-tested Django code.
   - Cons: this project uses Ninja, not `contrib.auth` views, so
     uidb64+token encoding must be reimplemented as API endpoints;
     stateless tokens don't naturally support single-use revocation for
     verification (no password-hash-change side effect there).
   - Effort: Low (reset) / Medium (verification).
2. **Explicit DB-backed token model(s)** (`EmailVerificationToken`/
   `PasswordResetToken`, or one model with a `purpose` field): `user` FK,
   hashed token, `expires_at`, `used_at`.
   - Pros: uniform for both features, explicit single-use/expiry matches
     this project's existing explicit-invariant style in `services.py`,
     easy to extend with rate-limit counters later.
   - Cons: new migration, more code, must store a hash (not the raw
     token) to avoid DB leakage.
   - Effort: Medium. **Recommended.**
3. **Registration gating: non-blocking `is_verified` flag (current
   login-on-register behavior kept) vs. blocking login until verified.**
   - Non-blocking: matches current `register()` exactly, minimal blast
     radius on existing tests and the already-shipped org-auto-
     provisioning/session flow.
   - Blocking: requires touching the already-shipped
     `ssr-protected-routes`/tenant-aware-login session-check boundary —
     larger, higher-regression-risk change.
   - Effort: Low (non-blocking, recommended) / Medium-High (blocking).

## Recommendation

Option 2 (explicit DB-backed token model) for both verification and
reset — matches this project's convention of explicit, testable,
spec-cited invariants rather than reimplementing Django's stateless
uidb64 flow outside `contrib.auth`. Keep registration **non-blocking**
(add `is_verified`, don't gate login) to minimize blast radius on the
already-shipped auth/tenancy/SSR-protection cycles. Send email via
`transaction.on_commit(...)` registered inside `register_user`'s atomic
block — never synchronously inside the transaction, since a rollback
(e.g. an org-slug collision) must not have already emailed a token for a
user row that no longer exists. Add Mailpit as a docker-compose service
(`axllent/mailpit`, ports 1025 SMTP / 8025 web UI) with
`EMAIL_BACKEND`/`EMAIL_HOST`/`EMAIL_PORT` fully env-driven, no hardcoded
Mailpit default that could resolve outside dev.

## Open Questions / Risks

- Reset-request endpoint must return an identical response regardless of
  whether the email exists (mirror `authenticate_user`'s existing
  anti-enumeration precedent).
- No rate-limiting middleware exists anywhere in this project today —
  needs explicit throttling/cooldown to prevent mail-bombing.
- Sending email inside `register_user`'s `@transaction.atomic` block is a
  real risk already flagged by the user — must use `transaction.on_commit`.
- Token expiry/single-use duration is not yet decided — needs a
  proposal-time decision.
- Non-blocking verification means unverified users keep full access
  immediately after registering — must be an explicit product decision,
  not an oversight.
- Single compose file (no `docker-compose.prod.yml`) — Mailpit config
  must stay confined to dev env files/`DEBUG`-gated settings branches,
  never a default that resolves in prod.

## Ready for Proposal

Yes. Two decisions should be surfaced to the user before/at proposal:
(1) non-blocking vs. blocking email verification, (2) exact token expiry
windows.
