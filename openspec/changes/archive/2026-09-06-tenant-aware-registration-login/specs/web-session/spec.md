# Delta for Web Session

## MODIFIED Requirements

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
