# Web Member Management Specification

## Purpose

Give an organization `OWNER` a screen to view, add, re-role, and remove members of the active
organization from the web app, surfacing the backend's `organization-membership` invariants
(role restriction on add, last-owner protection) inline instead of as generic errors. Non-OWNER
roles see the roster read-only and can remove themselves ("leave organization").

## Requirements

### Requirement: Members List Visibility

The system MUST let any authenticated member of the active organization view its members list,
showing each member's email, role label, and a marker identifying the current user's own row.

#### Scenario: Members list shows email, role, and self marker

- GIVEN an authenticated user who is a member of the active organization with two other members
- WHEN the members screen loads
- THEN all three members are listed with email and role label
- AND the row matching the current user carries a self marker

#### Scenario: Non-owner sees the roster without mutation controls

- GIVEN an authenticated user with role `EDITOR` or `VIEWER` on the active organization
- WHEN the members screen loads
- THEN the roster renders normally
- AND no add-member, role-change, or remove-other-member control is rendered
- AND one explanatory line states that only an `OWNER` can manage members

### Requirement: Add Member by Email (Owner Only)

The system MUST let an `OWNER` add an existing registered user to the active organization by
email, restricted to role `EDITOR` or `VIEWER`. The system MUST NOT expose `OWNER` as an
assignable role in the add-member form. The system MUST NOT render the add-member control for a
non-OWNER.

#### Scenario: Owner adds a member successfully

- GIVEN an `OWNER` viewing the members screen
- WHEN they submit an existing user's email with role `EDITOR`
- THEN the new member appears in the list with role `EDITOR` without a manual page refresh

#### Scenario: Owner form never offers OWNER as a role

- GIVEN an `OWNER` viewing the add-member form
- WHEN the role selector is rendered
- THEN only `EDITOR` and `VIEWER` are selectable options

#### Scenario: Add-member control is absent for non-owners

- GIVEN a user with role `EDITOR` or `VIEWER`
- WHEN the members screen loads
- THEN no add-member form or control is present anywhere on the screen

### Requirement: Change Member Role (Owner Only)

The system MUST let an `OWNER` change another member's role between `EDITOR` and `VIEWER` from
the members screen, MUST NOT render a role-change control for a non-OWNER, and MUST surface the
backend's last-owner-invariant error inline against the affected row rather than as a generic
failure when a role change is rejected.

#### Scenario: Owner changes a member's role successfully

- GIVEN an `OWNER` and a member currently listed with role `EDITOR`
- WHEN the `OWNER` changes that member's role to `VIEWER`
- THEN the member's row updates to show role `VIEWER` without a manual page refresh

#### Scenario: Role-change control is absent for non-owners

- GIVEN a user with role `EDITOR` or `VIEWER`
- WHEN the members screen loads
- THEN no control to change another member's role is rendered

### Requirement: Remove Member (Owner) and Leave Organization (Self)

The system MUST let an `OWNER` remove any other member from the active organization. The system
MUST let any member, regardless of role, remove themselves ("leave organization"). The system
MUST NOT render a remove-other-member control for a non-OWNER, and MUST always render a
self-removal control for every role.

#### Scenario: Owner removes another member

- GIVEN an `OWNER` and a member with role `EDITOR` on the active organization
- WHEN the `OWNER` removes that member
- THEN the member disappears from the list without a manual page refresh

#### Scenario: Non-owner leaves the organization

- GIVEN a user with role `EDITOR` or `VIEWER` on the active organization
- WHEN that user triggers the leave-organization control on their own row
- THEN their membership is removed
- AND they are redirected to `/dashboard`

#### Scenario: Remove-other-member control is absent for non-owners

- GIVEN a user with role `EDITOR` or `VIEWER`
- WHEN the members screen loads
- THEN no control to remove another member is rendered
- AND a self-removal ("leave organization") control is still rendered on their own row

### Requirement: Last-Owner Error Surfacing

When a role change or removal is rejected by the backend's `LastOwnerError` (409), the system
MUST display that error's `detail` message inline against the affected member's row, MUST NOT
collapse it into a generic error message, and MUST leave the member's role and list membership
unchanged.

#### Scenario: Demoting the sole owner surfaces the 409 inline

- GIVEN an organization with exactly one `OWNER`, viewed by that `OWNER`
- WHEN a role change to `EDITOR` or `VIEWER` is attempted on that owner's own row
- THEN the backend's `LastOwnerError` `detail` message renders inline on that row
- AND the row's role remains `OWNER`

#### Scenario: Removing the sole owner surfaces the 409 inline

- GIVEN an organization with exactly one `OWNER`
- WHEN removal of that owner's membership is attempted
- THEN the backend's `LastOwnerError` `detail` message renders inline on that row
- AND the member remains in the list
