# Web Account Recovery Specification

## Purpose

Give a web user the three screens needed to complete verification and password recovery
(`/verify-email`, `/forgot-password`, `/reset-password`), plus a dismissible reminder banner on
the dashboard, matching the existing `RegisterForm`/`LoginForm` conventions.

## Requirements

### Requirement: Verify-Email Screen

The system MUST provide a `/verify-email` client screen that reads `token` from
`searchParams`, submits it to the confirm-verification endpoint, and falls back to a manual
paste-token field when the param is absent. On success it MUST redirect via `router.replace()`;
on failure it MUST surface `ApiError.detail`.

#### Scenario: Verification succeeds from the emailed link
- GIVEN a user opens `/verify-email?token=<valid-token>`
- WHEN the screen submits that token automatically
- THEN the user sees a success state
- AND is redirected via `router.replace()`

#### Scenario: Verification failure shows the backend error
- GIVEN a user opens `/verify-email?token=<expired-or-invalid-token>`
- WHEN the token submission fails
- THEN the screen displays that failure's `ApiError.detail` message
- AND no redirect occurs

#### Scenario: Manual token entry when no link param is present
- GIVEN a user opens `/verify-email` with no `token` query param
- WHEN the screen renders
- THEN a paste-the-token field is shown for manual submission

### Requirement: Forgot-Password Request Screen

The system MUST provide a `/forgot-password` client screen that submits an email to the
request-reset endpoint and always renders the same generic confirmation message, regardless of
the backend response content, matching the request-reset anti-enumeration contract.

#### Scenario: Submitting any email shows the generic confirmation
- GIVEN a user submits an email on `/forgot-password`
- WHEN the request-reset call completes
- THEN the same generic confirmation message is shown
- AND the screen never differentiates based on whether the account exists

### Requirement: Reset-Password Confirm Screen

The system MUST provide a `/reset-password` client screen that reads `token` from
`searchParams`, collects a new password, and submits both to the confirm-reset endpoint. On
success it MUST redirect via `router.replace()`; on failure it MUST surface `ApiError.detail`
inline.

#### Scenario: Reset succeeds from the emailed link
- GIVEN a user opens `/reset-password?token=<valid-token>` and submits a valid new password
- WHEN the confirm-reset call succeeds
- THEN the user sees a success state
- AND is redirected via `router.replace()`

#### Scenario: Reset failure shows the backend error inline
- GIVEN a user submits an expired, used, or invalid token, or a password failing validation
- WHEN the confirm-reset call fails
- THEN the screen displays that failure's `ApiError.detail` message
- AND no redirect occurs

### Requirement: Dismissible Verify-Email Banner on Dashboard

The dashboard MUST show a dismissible banner prompting an unverified authenticated user to
verify their email, MUST NOT block any dashboard functionality, and MUST NOT render the banner
for a user whose `is_verified` is `true`.

#### Scenario: Banner shown to an unverified user
- GIVEN an authenticated user with `is_verified = false`
- WHEN the dashboard loads
- THEN the verify-email banner is rendered
- AND all other dashboard functionality remains usable

#### Scenario: Banner absent for a verified user
- GIVEN an authenticated user with `is_verified = true`
- WHEN the dashboard loads
- THEN the verify-email banner is not rendered

#### Scenario: Dismissing the banner hides it
- GIVEN an unverified user sees the verify-email banner
- WHEN they dismiss it
- THEN the banner disappears without navigating away from the dashboard
