# Delta for Web Organization Workspace

## MODIFIED Requirements

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
