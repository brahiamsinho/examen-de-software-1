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
or no longer valid.

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

### Requirement: Zero-Organization Empty State

A user with zero organization memberships MUST still reach `/dashboard`. The dashboard MUST
render a non-blocking empty-state prompt offering organization creation instead of redirecting
to a separate onboarding flow.

#### Scenario: Zero-org user reaches dashboard

- GIVEN an authenticated user belongs to no organization
- WHEN `/dashboard` is visited
- THEN the dashboard renders normally with an empty-state prompt
- AND no redirect to a blocking onboarding route occurs

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
