# Design: Email Verification & Password Reset

## Technical Approach

One `EmailToken` table discriminated by `purpose`, consumed by four new service
functions in `apps/users/services.py`. `api.py` stays thin; new `UserError`
subclasses map through `_ERROR_STATUS_MAP`. Mail is plain-text `send_mail`
scheduled with `transaction.on_commit`. Frontend adds three `(auth)` screens
mirroring `LoginForm`'s shape plus a dashboard banner.

## Architecture Decisions

### DD1 — Single-table token with fast hash lookup

**Choice**: `token_hash = sha256(raw).hexdigest()`, `unique=True`, raw =
`secrets.token_urlsafe(32)` (256 bits). Lookup is one indexed `get(token_hash=…)`.
**Alternatives**: Django's stateless `PasswordResetTokenGenerator` (no `used_at`,
no cap query); a password-style slow hash (`make_password`).
**Rationale**: The spec demands single-use + expiry + a `created_at` cap query —
all stateful, so the signed-token option is out. A slow hash forces a full-table
scan per submission and buys nothing: 256 bits of CSPRNG entropy is not
brute-forceable, so the attack a slow hash defends against does not exist here.
`secrets` matches the `generate_unique_slug` precedent.

### DD2 — Purpose column, not two tables

**Choice**: One model, `purpose ∈ {verify, reset}`. **Rejected**: separate
`VerificationToken`/`ResetToken`. **Rationale**: identical shape and identical
cooldown/cap query; two tables duplicate both and the migration.

### DD3 — Throttle by querying `created_at`

**Choice**: `filter(user, purpose, created_at__gte=now-60s).exists()` → cooldown;
`filter(created_at__gte=now-1h).count() >= 5` → cap. **Rejected**: cache/middleware
throttle, `django-ratelimit`. **Rationale**: proposal forbids new dependencies; the
table already stores exactly the needed timestamp.

### DD4 — Anti-enumeration lives in the service, not the view

**Choice**: `request_password_reset` returns `None` on every path (miss, hit,
throttled); `api.py` returns one module-level constant response. Mail always goes to
`user.email` from the DB, never the submitted string (no header-injection surface).
The miss and throttled branches additionally apply a fixed artificial delay before
returning, to approximate (not eliminate) the response time of the hit branch's real
SMTP send — see "Timing-parity limit" under Open Questions below.
**Rejected**: raising an error the view swallows — an early-return bug would leak.
**Rationale**: mirrors `authenticate_user`'s one-generic-error pattern.

### DD5 — Link URL from `FRONTEND_BASE_URL` env var

Settings must hold no literal host (project rule). `EMAIL_BACKEND/HOST/PORT/
TIMEOUT/DEFAULT_FROM_EMAIL` are all `env(...)` with Django's own defaults, so an
unset environment falls back to `EMAIL_BACKEND=smtp` behavior unchanged — no
Mailpit literal reaches `settings.py`.

### DD6 — Banner dismissal is session-only (jotai atom), not `localStorage`

**Rejected**: `localStorage`, as in `state/organizations.ts`.
**Rationale**: the active-org key is a *preference* that must survive reload; a
verification reminder is a *nag* that should return next session until resolved.
Persisting it also re-introduces the SSR hydration-mismatch problem that module's
docblock already calls out.

## Data Flow

    register_user (atomic)  ──create User, Org, EmailToken──┐
         │                                                  │
         └─ transaction.on_commit(send) ────────COMMIT──────┴──→ SMTP → Mailpit
                                        (rollback ⇒ never fires)

    email link → /verify-email?token=raw → POST /api/auth/verify-email
       → sha256 → indexed lookup → expiry/used checks → is_verified=True, used_at=now

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/apps/users/models.py` | Modify | `User.is_verified`; `EmailToken` (uuid pk, `user` FK CASCADE, `purpose`, `token_hash` unique, `expires_at`, `used_at`, `created_at`; index on `user,purpose,created_at`) |
| `backend/apps/users/migrations/0002_*.py` | Create | `AddField` + `CreateModel`, additive only |
| `backend/apps/users/emails.py` | Create | `send_verification_email`, `send_reset_email` — plain text, builds URL from `FRONTEND_BASE_URL` |
| `backend/apps/users/tokens.py` | Create | `issue_token(user, purpose)` → `(raw, EmailToken)`; `hash_token(raw)`; `resolve_token(raw, purpose)` |
| `backend/apps/users/services.py` | Modify | `on_commit` in `register_user`; `verify_email`, `resend_verification`, `request_password_reset`, `confirm_password_reset` |
| `backend/apps/users/errors.py` | Modify | `TokenInvalidError`, `TokenExpiredError`, `TokenUsedError`, `ResendCooldownError`, `ResendRateLimitError` |
| `backend/apps/users/schemas.py` | Modify | `VerifyIn`, `ResetRequestIn`, `ResetConfirmIn`, `MessageOut`; `UserOut.is_verified` |
| `backend/apps/users/api.py` | Modify | 4 endpoints + `_ERROR_STATUS_MAP` rows |
| `backend/config/settings.py`, `env.example`, `docker-compose.yml` | Modify | `EMAIL_*` + `FRONTEND_BASE_URL`; `mailpit` service |
| `frontend/src/app/(auth)/{verify-email,forgot-password,reset-password}/page.tsx` | Create | Suspense-wrapped (required for `useSearchParams`) |
| `frontend/src/components/auth/{VerifyEmail,ForgotPassword,ResetPassword}Form.tsx` | Create | `LoginForm` shape |
| `frontend/src/components/auth/VerifyEmailBanner.tsx` | Create | Renders `null` when verified or dismissed |
| `frontend/src/lib/auth.ts`, `state/session.ts`, `(app)/dashboard/page.tsx` | Modify | 4 clients, `is_verified` on `User`, dismiss atom, banner mount |
| `docs/ai/DECISIONS_LOG.md` | Modify | DD1–DD6 (project dual-documentation rule) |

## Interfaces / Contracts

```python
def verify_email(*, token: str) -> User                       # TokenInvalid/Expired/Used
def resend_verification(*, user: User) -> None                # ResendCooldown/RateLimit
def request_password_reset(*, email: str) -> None             # never raises, never branches visibly
                                                                # miss/throttled paths sleep a fixed delay first
def confirm_password_reset(*, token: str, new_password: str) -> User  # + PasswordPolicyError
```

| Method | Path | Auth | Body → Response |
|---|---|---|---|
| POST | `/api/auth/verify-email` | none + CSRF | `{token}` → 200 `MessageOut` |
| POST | `/api/auth/resend-verification` | `django_auth` | `{}` → 202 `MessageOut` |
| POST | `/api/auth/password-reset/request` | none + CSRF | `{email}` → 200 fixed `MessageOut` |
| POST | `/api/auth/password-reset/confirm` | none + CSRF | `{token, password}` → 200 `MessageOut` |

Status map: `token_invalid` 400, `token_expired` 400, `token_used` 409,
`resend_cooldown` 429, `resend_rate_limited` 429.

## Testing Strategy

Highest-risk surfaces needing dedicated RED tests:

| Surface | Approach |
|---|---|
| `on_commit` timing | `django_capture_on_commit_callbacks(execute=True)` for the happy path; a monkeypatched `create_organization` failure asserting no token row and empty `mail.outbox`. **Gotcha**: plain `django_db` never commits, so `on_commit` silently never fires — a test written without this fixture passes vacuously |
| Token hashing | hypothesis property: distinct raws → distinct hashes, and no persisted `token_hash` ever equals its raw token |
| Expiry boundaries | 24h/1h computed exactly; write `created_at`/`expires_at` explicitly (both writable) — no `freezegun` dependency |
| Throttle arithmetic | 59s vs 61s, 5th vs 6th token in the rolling hour, via explicit `created_at` |
| Enumeration parity | assert identical `status_code` **and** `response.content` across existing / non-existing / throttled email |
| Single-use + sibling invalidation | second submission rejected; a second outstanding reset token rejected after confirm |
| Frontend | Vitest+RTL: token-from-`searchParams` vs paste fallback; forgot-password renders the same copy even when the client rejects; banner matrix (unverified/verified/dismissed) |

Following covered patterns, no new dedicated suites: CSRF on anonymous endpoints,
`_ERROR_STATUS_MAP` wiring, `ApiError.detail` rendering, Suspense boundary.

UI conventions (from the ui-ux-pro-max priority table, not a database query): the
dismiss control must carry a visible or `aria-label`ed name (never icon-only), a
≥44×44px target, and the banner must use an existing semantic token pair — not a
raw hex — for its warning surface.

## Threat Matrix

Standard matrix is **N/A** — no shell commands, subprocesses, VCS/PR automation,
executable-file classification, or process integration. Domain-applicable rows:

| Surface | Status | Control |
|---|---|---|
| Open redirect from emailed link | Applicable | Screens `router.replace()` a fixed literal path; no user-controlled destination, `next` is not read here |
| Email header injection | Applicable | Recipient is always `user.email` from the DB, never the submitted string |
| Token in server logs / Referer | Applicable | Token travels in the POST body; the query param is consumed and never re-sent |
| Enumeration oracle via throttle | Applicable | DD4 — one constant response object |

## Migration / Rollout

Single additive migration; reverse drops both. No backfill — existing users default
to `is_verified=False`, which gates nothing. Mailpit is a dev compose service only.

## Open Questions

- [x] **Timing-parity limit** — RESOLVED by the user: the spec text now requires
  status/body parity (achievable, tested) plus a **fixed artificial delay** on the
  non-match/throttled paths to approximate — not eliminate — the hit path's response
  time. A job queue (which would achieve exact parity) stays explicitly out of scope
  for this change; the residual timing gap is an accepted risk at this project's
  scale. `request_password_reset`'s non-match and throttled branches must apply this
  fixed delay before returning, in addition to the existing `EMAIL_TIMEOUT` /
  `fail_silently=True` bound on the SMTP call itself. See
  `specs/password-reset/spec.md`'s "Anti-Enumeration Reset Request" requirement and
  its new "fixed timing-parity delay" scenario for the exact contract.
