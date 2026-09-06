# Web Session Specification

## Purpose

Give the Next.js frontend a credentialed, CSRF-aware transport and a client-side session
lifecycle (register, login, logout, route protection) that correctly consumes the existing
session-cookie backend without ever silently sending anonymous requests.

## Requirements

### Requirement: Credentialed CSRF-Aware Transport

The system MUST send `credentials: "include"` on every API request. The system MUST prime the
CSRF cookie via `GET /api/auth/csrf` only when the `csrftoken` cookie is absent, and MUST attach
the current `X-CSRFToken` header value (read from `document.cookie`, never cached) on unsafe
methods. The system MUST normalize failed responses into a typed `ApiError {status, code,
detail}`.

#### Scenario: Credentialed request succeeds

- GIVEN a valid session cookie exists
- WHEN any API request is issued through the shared transport
- THEN the request includes credentials and the response is parsed as JSON or `ApiError`

#### Scenario: CSRF priming skipped when cookie present

- GIVEN the `csrftoken` cookie already exists
- WHEN an unsafe request is issued
- THEN no priming `GET /api/auth/csrf` call is made
- AND the request carries the existing token in `X-CSRFToken`

#### Scenario: Stale CSRF token retried once

- GIVEN an unsafe request returns `403` with a CSRF error code
- WHEN the transport handles that response
- THEN it re-primes the CSRF cookie and retries the request exactly once
- AND a second CSRF failure surfaces as `ApiError`, not an infinite retry

### Requirement: Registration

The system MUST let an anonymous visitor register with email and password, establishing an
authenticated session on success.

#### Scenario: Successful registration

- GIVEN an anonymous visitor submits a unique email and a password meeting backend validation
- WHEN the registration form is submitted
- THEN the session becomes `authenticated` and the user is redirected to `/dashboard`

#### Scenario: Duplicate email surfaces backend detail

- GIVEN an email already registered
- WHEN registration is submitted with that email
- THEN the form displays the backend `detail` message
- AND the session remains `anonymous`

### Requirement: Login and Logout

The system MUST let a registered user authenticate via email and password, and MUST clear
client-side session state and redirect to `/` on logout.

#### Scenario: Successful login

- GIVEN a registered user's correct credentials
- WHEN the login form is submitted
- THEN the session becomes `authenticated`
- AND the user is redirected per the `next` resolution rule

#### Scenario: Invalid credentials rejected

- GIVEN incorrect credentials
- WHEN the login form is submitted
- THEN one generic error is shown
- AND the session remains `anonymous`

#### Scenario: Logout redirects to landing

- GIVEN an authenticated session
- WHEN logout is triggered
- THEN client session state is cleared
- AND the user is redirected to `/`

### Requirement: Session State and Route Protection

The system MUST model session state as exactly one of `loading | authenticated | anonymous |
error`. Protected routes MUST render a skeleton while `loading` and MUST NOT render protected
content before resolution. `anonymous` MUST redirect to `/login?next=<path>`. Network or `5xx`
failures MUST set `error` (retry UI), and MUST NOT redirect as if logged out. Post-login
redirect MUST honor `next` only when it is a single-leading-slash relative path, else fall back
to `/dashboard`.

#### Scenario: Anonymous access redirected with next

- GIVEN no session cookie
- WHEN `/dashboard` is visited
- THEN the visitor is redirected to `/login?next=/dashboard`
- AND login success returns to `/dashboard`

#### Scenario: Backend outage does not log out

- GIVEN `GET /api/auth/me` fails with a network error or `5xx`
- WHEN the protected layout evaluates session state
- THEN the state becomes `error` with a retry action
- AND no redirect to `/login` occurs

#### Scenario: Open-redirect guarded

- GIVEN `next` is an absolute or protocol-relative URL
- WHEN post-login redirect resolves
- THEN the user is sent to `/dashboard` instead of the untrusted `next` value
