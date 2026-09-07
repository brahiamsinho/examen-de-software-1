# Web Session Specification

## Purpose

Give the Next.js frontend a credentialed, CSRF-aware transport and a client-side session
lifecycle (register, login, logout, route protection) that correctly consumes the existing
session-cookie backend without ever silently sending anonymous requests.

## Requirements

### Requirement: Credentialed CSRF-Aware Transport

The system MUST send `credentials: "include"` on every API request. The system MUST prime the
CSRF cookie via `GET /api/auth/csrf` only when the `csrftoken` cookie is absent, and MUST attach
the current `X-CSRFToken` header value on unsafe methods. The token value comes from
`document.cookie` when readable, and otherwise from a module-level cache populated by the priming
response body — required because the deployed topology serves the app and the API from different
domains, where JS on the app domain cannot read a cookie scoped to the API domain. The cache is
invalidated after login/logout and re-primed automatically, once, on a `403` CSRF failure. The
system MUST normalize failed responses into a typed `ApiError {status, code, detail}`.

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
authenticated session on success. The backend-provisioned organization returned by
registration MUST become the client's active organization before redirect. The redirect
target itself is unchanged: `/dashboard`.
(Previously: registration set no active organization; the backend created no organization to
adopt.)

#### Scenario: Successful registration

- GIVEN an anonymous visitor submits a unique email and a password meeting backend validation
- WHEN the registration form is submitted
- THEN the session becomes `authenticated` and the user is redirected to `/dashboard`

#### Scenario: Duplicate email surfaces backend detail

- GIVEN an email already registered
- WHEN registration is submitted with that email
- THEN the form displays the backend `detail` message
- AND the session remains `anonymous`

#### Scenario: Provisioned organization becomes active before redirect

- GIVEN registration succeeds and the client fetches the caller's organizations, resolving the
  single newly provisioned organization (the backend response itself carries no organization
  data, per the "No org data in the auth response" non-goal)
- WHEN the redirect to `/dashboard` occurs
- THEN that provisioned organization is already set as the active organization

### Requirement: Login and Logout

The system MUST let a registered user authenticate via email and password, and MUST clear
client-side session state and redirect to `/` on logout. On successful login, the system MUST
resolve the caller's organizations and branch the post-login destination: a valid `next`
parameter MUST take precedence over organization-count branching; otherwise, zero organizations
route to `/dashboard` unchanged, exactly one organization sets that organization active and
routes to `/dashboard`, and two or more organizations route to the organization picker.
(Previously: post-login destination was unconditionally `next` or `/dashboard`, with no
organization-count awareness.)

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

#### Scenario: Zero organizations after login stays on the unchanged empty-state path

- GIVEN a user with zero organization memberships logs in with no `next` parameter
- WHEN the login form is submitted successfully
- THEN the user is redirected to `/dashboard`
- AND no organization picker is shown

#### Scenario: Exactly one organization sets it active and proceeds

- GIVEN a user with exactly one organization membership logs in with no `next` parameter
- WHEN the login form is submitted successfully
- THEN that organization becomes the active organization
- AND the user is redirected to `/dashboard` with no picker shown

#### Scenario: Two or more organizations route to the picker

- GIVEN a user with two or more organization memberships logs in with no `next` parameter
- WHEN the login form is submitted successfully
- THEN the user is routed to the organization picker instead of directly to `/dashboard`

#### Scenario: A valid next parameter takes precedence over organization-count branching

- GIVEN a user with two or more organization memberships is redirected to
  `/login?next=/dashboard` by the route guard
- WHEN that user logs in successfully
- THEN the user is sent to the valid `next` destination
- AND the organization picker is not shown, regardless of organization count

### Requirement: Session State and Route Protection

The system MUST model session state as exactly one of `loading | authenticated | anonymous |
error`. Protected routes MUST render a skeleton while `loading` and MUST NOT render protected
content before resolution. `anonymous` MUST redirect to `/login?next=<path>`. Network or `5xx`
failures MUST set `error` (retry UI), and MUST NOT redirect as if logged out. Post-login
redirect MUST honor `next` only when it is a single-leading-slash relative path, else fall back
to `/dashboard`. For both the `(app)` and `(gate)` route groups, the server MUST validate
session *validity* — not merely cookie presence — before emitting any protected-route markup;
an anonymous or invalid session MUST receive a redirect response instead of protected content.
The server-side validity check MUST NOT be cached across requests, since the session identity it
resolves is per-request and per-user.
(Previously: route protection was enforced client-side only; the server rendered protected-route
markup into the RSC payload regardless of session validity, relying solely on `SessionGuard` to
hide it after mount.)

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

#### Scenario: Anonymous server-side request never receives protected markup

- GIVEN no session cookie is present on the request
- WHEN a protected route under `(app)` or `(gate)` is requested directly, before any client
  script runs
- THEN the server responds with a redirect to `/login?next=<path>`
- AND the response body contains no protected-route markup

#### Scenario: A present but invalid or expired cookie is rejected server-side

- GIVEN a session cookie is present on the request, but the backend session it references is
  invalid or expired
- WHEN the server-side session check runs before rendering a protected route
- THEN the request is redirected to `/login?next=<path>`, exactly as if no cookie were present
- AND cookie presence alone MUST NOT be treated as proof of a valid session

#### Scenario: Backend unreachable during the server check falls through to the client retry state

- GIVEN the backend is unreachable or returns a network error or `5xx` during the server-side
  session check
- WHEN a protected route is requested
- THEN the server does NOT redirect the request to `/login`
- AND the response instead falls through to render normally, leaving the client `SessionGuard`'s
  existing `error`/retry state to handle the failure
