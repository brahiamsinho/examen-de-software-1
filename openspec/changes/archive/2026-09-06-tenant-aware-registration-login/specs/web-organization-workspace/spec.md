# Delta for Web Organization Workspace

## ADDED Requirements

### Requirement: Post-Login Organization Picker

When a login resolves two or more organizations for the caller (per `web-session` § "Login and
Logout" branching, and only when no valid `next` parameter takes precedence), the system MUST
present a one-time picker screen listing each organization with the caller's role, reusing
`OrgSwitcher`'s presentational shape. Selecting an organization MUST set it as the active
organization and MUST then redirect the user onward. The exact route/URL shape of this screen
is a design-level decision, not a requirement of this spec.

#### Scenario: Picker lists organizations with role

- GIVEN a login resolves the caller into two or more organizations with no precedence-winning
  `next` parameter
- WHEN the picker screen is reached
- THEN every one of the caller's organizations is listed with that membership's role

#### Scenario: Explicit selection sets the active organization and proceeds

- GIVEN the picker screen is showing the caller's organizations
- WHEN the caller selects one organization
- THEN that organization becomes the active organization
- AND the caller is redirected onward

#### Scenario: Selection survives a page reload

- GIVEN the caller selected an organization from the picker and was redirected
- WHEN the page is reloaded
- THEN the selected organization remains the active organization

## MODIFIED Requirements

### Requirement: Zero-Organization Empty State

A user with zero organization memberships MUST still reach `/dashboard`. The dashboard MUST
render a non-blocking empty-state prompt offering organization creation instead of redirecting
to a separate onboarding flow. This state is now reached only by a legacy pre-change account
that predates auto-provisioned registration, or by a user whose sole organization was
subsequently deleted by its owner — it is no longer the default landing for a fresh signup,
since registration now provisions one organization. No redirect to a blocking onboarding route
MUST ever occur, preserving the property that makes leaving legacy accounts unbackfilled safe.
(Previously: described as the default landing after any fresh registration; behavior is
unchanged, only the documented preconditions are corrected.)

#### Scenario: Zero-org user reaches dashboard

- GIVEN an authenticated user belongs to no organization
- WHEN `/dashboard` is visited
- THEN the dashboard renders normally with an empty-state prompt
- AND no redirect to a blocking onboarding route occurs

#### Scenario: Legacy pre-change account reaches the empty state

- GIVEN a user account created before registration provisioned organizations, with zero
  organization memberships
- WHEN `/dashboard` is visited
- THEN the dashboard renders the same non-blocking empty-state prompt
- AND that user is not retroactively assigned an organization

#### Scenario: Sole organization deleted falls back to the empty state

- GIVEN a user whose only organization was deleted by its `OWNER`
- WHEN `/dashboard` is visited
- THEN the dashboard renders the same non-blocking empty-state prompt
