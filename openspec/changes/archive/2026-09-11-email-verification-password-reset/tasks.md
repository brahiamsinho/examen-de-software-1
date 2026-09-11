# Tasks: Email Verification & Password Reset

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1400-1800 (backend ~800-900, frontend ~800-900) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | Unit 1 backend, Unit 2 frontend |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

First backend+frontend change this session; two stacks plus a migration, four
endpoints, three screens, and property/timing tests push well past the 400-line
budget. `single-pr` requires maintainer-approved `size:exception` before apply;
if the maintainer instead prefers a split, retarget to `feature-branch-chain`
using the units below.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Backend: model, migration, tokens, emails, services, API | PR 1 | `pytest backend/apps/users/tests -k "token or verify or reset or email"` | `docker compose up mailpit` + manual POST to `/api/auth/verify-email` | Revert `apps/users/{models,tokens,emails,services,errors,schemas,api}.py` + migration; reverse migration drops `is_verified`/`EmailToken` |
| 2 | Frontend: 3 screens, forms, banner | PR 2 | `npm test -- VerifyEmail ForgotPassword ResetPassword Banner` | `npm run dev` + visit `/verify-email?token=...` | Revert `components/auth/*Form.tsx`, `VerifyEmailBanner.tsx`, `app/(auth)/{verify-email,forgot-password,reset-password}`, `lib/auth.ts` additions |

## Phase 1: Backend Foundation

- [x] 1.1 `models.py`: add `EmailToken` (uuid pk, `user` FK CASCADE, `purpose`, `token_hash` unique, `expires_at`, `used_at`, `created_at`, index on `user,purpose,created_at`) + `User.is_verified` (default False).
- [x] 1.2 Generate additive migration `0002_*.py`; verify reverse drops both.
- [x] 1.3 RED: hypothesis test — distinct raws → distinct hashes; no `token_hash` ever equals its raw.
- [x] 1.4 GREEN: create `tokens.py` — `issue_token(user, purpose)→(raw, EmailToken)`, `hash_token(raw)` (sha256), `resolve_token(raw, purpose)`.
- [x] 1.5 RED: mail test — plain-text body only; recipient is always `user.email` from DB even if a spoofed string is passed (header-injection case).
- [x] 1.6 GREEN: create `emails.py` — `send_verification_email`, `send_reset_email` (plain-text `send_mail`, link built from `FRONTEND_BASE_URL`).
- [x] 1.7 `settings.py`/`env.example`: env-driven `EMAIL_BACKEND/HOST/PORT/TIMEOUT/DEFAULT_FROM_EMAIL` + `FRONTEND_BASE_URL`, no Mailpit literal.
- [x] 1.8 `docker-compose.yml`: add dev-only `mailpit` service (SMTP 1025, UI 8025).

## Phase 2: Backend Services (RED-first)

- [x] 2.1 RED: `django_capture_on_commit_callbacks(execute=True)` — commit creates 1 token + 1 email; mocked org-provisioning failure → 0 tokens, empty `mail.outbox`.
- [x] 2.2 GREEN: wire `transaction.on_commit` into `register_user`.
- [x] 2.3 RED: `verify_email` — valid marks used+verifies; used/expired/invalid rejected with specific errors.
- [x] 2.4 GREEN: implement `verify_email(*, token) -> User`.
- [x] 2.5 RED: `resend_verification` — 59s cooldown rejected, 61s accepted, 5th ok/6th capped (explicit `created_at`).
- [x] 2.6 GREEN: implement `resend_verification(*, user) -> None`.
- [x] 2.7 RED: `request_password_reset` — identical status+body for existing/non-existing/throttled email; non-match/throttled apply the fixed delay; existing path creates token+email.
- [x] 2.8 GREEN: implement `request_password_reset(*, email) -> None` (never raises/branches visibly; fixed delay on miss/throttled).
- [x] 2.9 RED: `confirm_password_reset` — success sets password+`is_verified=True`; sibling reset token invalidated; weak-password/expired/used/invalid rejected.
- [x] 2.10 GREEN: implement `confirm_password_reset(*, token, new_password) -> User`.

## Phase 3: Backend API Wiring

- [x] 3.1 `errors.py`: add `TokenInvalidError`, `TokenExpiredError`, `TokenUsedError`, `ResendCooldownError`, `ResendRateLimitError`.
- [x] 3.2 `schemas.py`: add `VerifyIn`, `ResetRequestIn`, `ResetConfirmIn`, `MessageOut`; `is_verified` on `UserOut`.
- [x] 3.3 RED: endpoint tests — 4 routes, status map (400/400/409/429/429), CSRF on anonymous endpoints.
- [x] 3.4 GREEN: `api.py` — 4 endpoints (`verify-email`; `resend-verification` `django_auth`; `password-reset/request`; `password-reset/confirm`) + `_ERROR_STATUS_MAP` rows.

## Phase 4: Frontend Foundation

- [x] 4.1 Add `is_verified: boolean` to frontend `User` type; add 4 client functions to `lib/auth.ts`.
- [x] 4.2 RED (Vitest): dashboard renders banner only when `is_verified=false`.
- [x] 4.3 GREEN: wire `is_verified` through session state + dashboard.

## Phase 5: Frontend Components

- [x] 5.1 RED+GREEN: `VerifyEmailForm.tsx` — token from `searchParams`, auto-submit, paste fallback, `router.replace()` fixed literal path only (open-redirect case), token never re-sent after initial POST (referer/log case), `ApiError.detail` on failure.
- [x] 5.2 RED+GREEN: `ForgotPasswordForm.tsx` — always renders the same generic confirmation regardless of response.
- [x] 5.3 RED+GREEN: `ResetPasswordForm.tsx` — token+password submit, `router.replace()` fixed literal path only (open-redirect case), inline `ApiError.detail` on failure.
- [x] 5.4 RED+GREEN: `VerifyEmailBanner.tsx` — session-only jotai dismiss atom (not `localStorage`, DD6); null when verified/dismissed; ≥44x44 dismiss target with visible/aria-label name.

## Phase 6: Frontend Routing

- [x] 6.1 Create `app/(auth)/{verify-email,forgot-password,reset-password}/page.tsx`, Suspense-wrapped wherever the page actually calls `useSearchParams()`. Confirmed: `verify-email` and `reset-password` need it (token comes from the query string); `forgot-password` does not (its form never reads `useSearchParams()`), matching the existing `register/page.tsx` precedent — not wrapped, by design, not by omission.
- [x] 6.2 Mount `VerifyEmailBanner` in `(app)/dashboard/page.tsx`.

## Phase 7: Docs

- [x] 7.1 Append DD1-DD6 to `docs/ai/DECISIONS_LOG.md`.
