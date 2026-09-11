# Proposal: Email Verification & Password Reset

## Intent

A user who forgets their password today is locked out permanently — there is no
recovery path, only a manual DB/shell reset. Registration also accepts any
typed email with no proof of ownership, so support has no way to tell a real
address from a typo. This change adds a self-service recovery path and an
ownership signal, plus the dev mail infrastructure (Mailpit) both need.

## Scope

### In Scope

- Mailpit dev service in `docker-compose.yml` (SMTP 1025 / UI 8025); `EMAIL_*`
  fully env-driven in `settings.py`, documented in `backend/env.example`.
- `User.is_verified` — informational flag only. Login and protected routes are
  NOT gated on it (closed decision).
- DB-backed single-use token model (hashed token, `expires_at`, `used_at`,
  `purpose`). Expiry: **24h** verification, **1h** reset (closed decision).
- Registration dispatches the verification email via `transaction.on_commit`
  inside the existing atomic block — never inside the transaction.
- Endpoints: confirm-verification, resend-verification, request-reset,
  confirm-reset. Request-reset returns an identical response whether or not the
  account exists (mirrors `authenticate_user`).
- Frontend screens `/verify-email` and `/forgot-password` + `/reset-password`,
  matching `RegisterForm`/`LoginForm` shape (client component, `useState`,
  `ApiError.detail`, `router.replace()`), Spanish copy.

### Out of Scope

- Gating login/protected routes on `is_verified`; re-verification on email change.
- Generic rate-limiting middleware or a throttling dependency.
- HTML email templates, branding, background job queue, production SMTP provider.
- Admin-triggered resets and account-lockout policy.

## Capabilities

### New Capabilities

- `email-verification`: issuing, emailing, expiring, and consuming a single-use
  verification token; `is_verified` transition; resend + cooldown.
- `password-reset`: anti-enumeration reset request, single-use 1h token, and
  password-change confirmation.
- `transactional-email`: env-driven mail configuration and the dev-only Mailpit
  catcher, including its prod-safety invariant.
- `web-account-recovery`: verify-email, forgot-password, and reset-password
  screens.

### Modified Capabilities

- `user-authentication`: registration additionally creates a verification token
  and schedules its email on commit; `User` gains non-gating `is_verified`.

## Approach

Exploration's Option 2 (explicit DB-backed token model), one model with a
`purpose` field. Services own the logic; `api.py` stays thin; errors are flat
`UserError` subclasses with stable codes mapped through `_ERROR_STATUS_MAP`.

Three previously-open product decisions, settled here:

1. **Link-carried opaque token, not a numeric code.** The email links to
   `/verify-email?token=...` (and `/reset-password?token=...`); the screen reads
   `searchParams` and submits, with a paste-the-token fallback field when the
   param is absent. Rationale: a 6-digit code has low entropy and would *require*
   a real brute-force throttle this project does not have; a high-entropy token
   makes guessing a non-issue. It also reuses the `(auth)` route group and the
   `useSearchParams` pattern `LoginForm` already uses for `next`.
2. **Resend exists, throttled without new dependencies.** A 60s cooldown plus a
   5-per-rolling-hour cap, both derived by querying the token table's
   `created_at` for that user — no middleware, no package. Verification resend
   (known caller) returns an explicit cooldown error; reset-request returns the
   same generic response when throttled, so the throttle cannot be used as an
   enumeration oracle.
3. **Plain-text email via `send_mail`.** Copy lives in a small
   `apps/users/emails.py`; no HTML template, no template files. Proportional to
   a dev-scoped project.

Confirming a reset consumes the token and invalidates every other outstanding
reset token for that user.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `docker-compose.yml` | Modified | `mailpit` service (dev) |
| `backend/config/settings.py`, `backend/env.example` | Modified | Env-driven `EMAIL_*`; no Mailpit literal in settings |
| `backend/apps/users/models.py` | Modified | `is_verified` + token model + migration |
| `backend/apps/users/services.py` | Modified | `on_commit` dispatch; verify/reset/resend services |
| `backend/apps/users/emails.py` | New | Plain-text message builders |
| `backend/apps/users/api.py`/`errors.py`/`schemas.py` | Modified | 4 endpoints, codes, schemas |
| `frontend/src/lib/auth.ts` | Modified | 4 client functions |
| `frontend/src/components/auth/`, `frontend/src/app/(auth)/` | New | 3 forms + 3 routes |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Mailpit config leaks into a prod deploy | Med | No Mailpit literal in `settings.py`; values only in `env.example` + the dev compose service |
| Email sent for a rolled-back registration | Med | `transaction.on_commit` only; asserted in tests |
| Reset-request leaks account existence via status, body, or timing | Med | One generic response incl. the throttled path; spec scenario |
| Raw token recoverable from a DB dump | Low | Only the hash is stored; raw token exists once, in the email |
| Mail-bomb via unbounded resend | Med | Cooldown + hourly cap on the token table |
| Unverified users retain full access (by design) | — | Explicit closed product decision, not an oversight |

## Rollback Plan

Revert the branch and run the reverse migration (drops `is_verified` and the
token table). Everything is additive: no existing column changes shape, no
existing endpoint changes contract, and registration/login behave exactly as
today if the email path is removed. Remove the `mailpit` compose service and the
`EMAIL_*` env block; with no `EMAIL_*` set, Django falls back to its default
backend and nothing else regresses.

## Dependencies

- `axllent/mailpit` image (dev only, pulled by compose).
- No new Python or npm package.

## Success Criteria

- [ ] A user who registers receives a verification email in Mailpit and can
      verify from the link; a second use of the same token fails.
- [ ] A verification token older than 24h and a reset token older than 1h are
      both rejected as expired.
- [ ] A user who forgot their password can request, receive, and complete a
      reset, then log in with the new password.
- [ ] Reset-request returns a byte-identical response for a registered and an
      unregistered email, including when throttled.
- [ ] A rolled-back registration sends no email.
- [ ] Login and every protected route behave identically for verified and
      unverified users.
