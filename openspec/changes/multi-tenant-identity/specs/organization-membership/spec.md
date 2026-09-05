# Organization Membership Specification

## Purpose

Define `Membership` as the join between `User` and `Organization`: the three-role set
(`OWNER`, `EDITOR`, `VIEWER`), how members are added and removed, role changes, and the
last-owner invariant that guarantees every organization always has at least one `OWNER`.

## Requirements

### Requirement: Membership Uniqueness and Roles

The system MUST bind each `(user, organization)` pair to exactly one `Membership` record,
unique together, carrying exactly one role from `OWNER`, `EDITOR`, `VIEWER`.

#### Scenario: Duplicate membership rejected

- GIVEN a user already has a `Membership` in an organization
- WHEN an `OWNER` attempts to add that same user to the same organization again
- THEN the request is rejected as a duplicate membership
- AND no second `Membership` row is created

### Requirement: Add Member by Email Lookup

The system MUST allow an `OWNER` to add an existing registered user to the organization by
email lookup, assigning `EDITOR` or `VIEWER`. The system MUST NOT invite unregistered
addresses; a lookup miss MUST fail with a clear, tested error rather than starting an
invitation flow.

#### Scenario: Add existing user succeeds

- GIVEN an `OWNER` and a separately registered user identified by email
- WHEN the `OWNER` adds that email with role `EDITOR`
- THEN a `Membership` for that user, that organization, and role `EDITOR` is created

#### Scenario: Add unregistered email fails clearly

- GIVEN an `OWNER` and an email with no matching `User`
- WHEN the `OWNER` attempts to add that email
- THEN the request is rejected with a clear, tested "user not found" error
- AND no `Membership` or invitation artifact is created

#### Scenario: Non-owner cannot add members

- GIVEN a user with role `EDITOR` or `VIEWER` on an organization
- WHEN that user attempts to add a member
- THEN the request is rejected as unauthorized

### Requirement: Change Member Role

The system MUST allow an `OWNER` to change another member's role between `OWNER`, `EDITOR`,
and `VIEWER`, subject to the last-owner invariant.

#### Scenario: Owner changes a member's role

- GIVEN an `OWNER` and a member with role `EDITOR`
- WHEN the `OWNER` changes that member's role to `VIEWER`
- THEN the `Membership` role is updated to `VIEWER`

#### Scenario: Demoting the sole owner fails

- GIVEN an organization with exactly one `OWNER`
- WHEN a request attempts to change that owner's role to `EDITOR` or `VIEWER`
- THEN the request is rejected with a clear, tested last-owner-invariant error
- AND the role remains `OWNER`

### Requirement: Remove Member

The system MUST allow an `OWNER` to remove another member, MUST allow any member to remove
themselves (self-removal), and MUST reject removal of the sole remaining `OWNER`.

#### Scenario: Owner removes another member

- GIVEN an `OWNER` and a member with role `EDITOR`
- WHEN the `OWNER` removes that member
- THEN the member's `Membership` no longer exists

#### Scenario: Non-owner self-removal allowed

- GIVEN a user with role `EDITOR` or `VIEWER` on an organization
- WHEN that user removes themselves
- THEN their own `Membership` no longer exists

#### Scenario: Removing the sole owner fails

- GIVEN an organization with exactly one `OWNER`
- WHEN any request attempts to remove that owner's `Membership`
- THEN the request is rejected with a clear, tested last-owner-invariant error
- AND the `Membership` remains intact

### Requirement: Viewer Visibility in Presence

The `Membership`/role model MUST NOT exclude `VIEWER` members from any presence-relevant
identity field, so that a future realtime layer can treat a `VIEWER` as visible the same as any
other role. This cycle adds no realtime code; it only constrains the data model.

#### Scenario: Viewer membership exposes the same identity fields

- GIVEN memberships with roles `OWNER`, `EDITOR`, and `VIEWER` on the same organization
- WHEN each membership's identity-relevant fields are read
- THEN the `VIEWER` membership exposes the same set of fields as the `OWNER` and `EDITOR`
  memberships
