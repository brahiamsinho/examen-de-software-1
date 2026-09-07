# Organization Tenancy Specification

## Purpose

Define the `Organization` entity as the tenant boundary of the system: its slug-based
identity, its stored-but-unenforced `plan` label, and authorized CRUD over it.

## Requirements

### Requirement: Organization Entity

The system MUST represent a tenant as an `Organization` addressed by a unique, non-sequential
`slug` (not by a sequential integer primary key) so that URLs do not leak tenant count or allow
enumeration. The system MUST store a `plan` field as `TextChoices` with values `STARTER`,
`TEAM`, `ENTERPRISE`, defaulting to `STARTER`.

#### Scenario: New organization defaults to STARTER

- GIVEN an authenticated user creates an organization without specifying a plan
- WHEN the organization is persisted
- THEN its `plan` is `STARTER`

#### Scenario: Slug uniqueness enforced

- GIVEN an organization exists with slug `acme`
- WHEN a new organization is created with slug `acme`
- THEN the creation is rejected as a duplicate slug

#### Scenario: Plan gates nothing

- GIVEN an organization has `plan = STARTER`
- WHEN any tenant-scoped operation is performed under that organization
- THEN the operation succeeds or fails independently of `plan`, since `plan` enforces no limit
  this cycle

### Requirement: Create Organization

The system MUST allow any authenticated user to create an organization, and MUST make the
creator its `OWNER` in the same transaction.

#### Scenario: Creator becomes OWNER

- GIVEN an authenticated user with no existing organizations
- WHEN that user creates a new organization
- THEN the organization is persisted
- AND a `Membership` binding that user to the organization with role `OWNER` is created

### Requirement: Read Organization

The system MUST allow a member to read their organization's details. A caller who is not a
member MUST NOT be able to distinguish a real organization from a nonexistent one (see
`tenant-isolation` for the shared 404 contract).

#### Scenario: Member reads organization details

- GIVEN a user is a member of an organization
- WHEN that user requests the organization's details
- THEN the response contains the organization's slug, name, and plan

### Requirement: Rename Organization

The system MUST allow only an `OWNER` of an organization to rename it. `EDITOR` and `VIEWER`
MUST NOT be authorized to rename.

#### Scenario: Owner renames organization

- GIVEN a user with role `OWNER` on an organization
- WHEN that user submits a new name
- THEN the organization's name is updated

#### Scenario: Non-owner rename rejected

- GIVEN a user with role `EDITOR` or `VIEWER` on an organization
- WHEN that user attempts to rename it
- THEN the request is rejected as unauthorized
- AND the organization's name is unchanged

### Requirement: Delete Organization

The system MUST allow only an `OWNER` to delete an organization. Deletion MUST be a hard delete
that cascades to all `Membership` rows for that organization.

#### Scenario: Owner hard-deletes organization

- GIVEN a user with role `OWNER` on an organization that has other members
- WHEN that user deletes the organization
- THEN the organization record no longer exists
- AND every `Membership` row referencing it no longer exists

#### Scenario: Non-owner delete rejected

- GIVEN a user with role `EDITOR` or `VIEWER` on an organization
- WHEN that user attempts to delete it
- THEN the request is rejected as unauthorized
- AND the organization and its memberships remain intact
