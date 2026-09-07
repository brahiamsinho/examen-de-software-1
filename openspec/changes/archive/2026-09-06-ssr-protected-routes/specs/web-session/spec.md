# Delta for Web Session

## MODIFIED Requirements

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
