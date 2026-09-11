# Web Organization Workspace Specification

## Purpose

Give an authenticated user a panel that lists their organizations with role, lets them select
and persist an active organization, reach a non-blocking empty state at zero organizations, and
create a new organization without a manual refresh.

## Requirements

### Requirement: Organization List and Active Selection

The system MUST list the authenticated user's organizations with each membership's role. The
system MUST let the user select an active organization and MUST persist that selection in
`localStorage`, falling back to the first listed organization when the stored value is missing
or no longer valid. When the current user removes themselves (leaves) their currently-active
organization, the system MUST repoint the active-organization selection — both in-memory state
and the persisted `localStorage` value — to another organization the user still belongs to, or
to a valid "no organization" state if none remain, and MUST NOT continue to reference the
organization just left.
(Previously: covered list display, active selection, and persisted-selection fallback on load,
with no self-removal repointing behavior.)

#### Scenario: Organization list shows role

- GIVEN an authenticated user with memberships in two organizations
- WHEN the panel loads
- THEN both organizations are listed with their respective role

#### Scenario: Active selection persists across reload

- GIVEN a user selects an organization as active
- WHEN the page is reloaded
- THEN the same organization remains active

#### Scenario: Stale persisted selection falls back

- GIVEN a persisted active-org value that no longer matches any membership
- WHEN the panel loads
- THEN the first listed organization becomes active instead

#### Scenario: Leaving the active organization repoints to a remaining one

- GIVEN a user belongs to two organizations and the currently active one is organization A
- WHEN the user removes themselves from organization A
- THEN the active-organization selection repoints to organization B
- AND the persisted `localStorage` value is updated to organization B
- AND no request or UI state continues to reference organization A

#### Scenario: Leaving the sole active organization falls back to no-organization state

- GIVEN a user belongs to exactly one organization, which is the currently active one
- WHEN the user removes themselves from that organization
- THEN the active-organization selection becomes the valid "no organization" state
- AND the persisted `localStorage` value no longer references the left organization
- AND the user is redirected to `/dashboard`, which renders its existing empty state

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

### Requirement: Organization Creation

The system MUST let an authenticated user create an organization by name. On success, the
creator MUST appear as `OWNER`, the new organization MUST appear in the list without a manual
page refresh, and it MUST become the active organization.

#### Scenario: Successful creation becomes active

- GIVEN an authenticated user submits a unique organization name
- WHEN creation succeeds
- THEN the organization appears in the list with role `OWNER`
- AND it becomes the active organization without a manual refresh

#### Scenario: Duplicate slug surfaces backend detail

- GIVEN an organization name that collides with an existing slug
- WHEN creation is submitted
- THEN the form displays the backend `409` `detail` message
- AND no organization is added to the list
