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

### Requirement: Server-Generated Organization Slug

The system MUST provide a slug-generation utility used when a caller (e.g. registration) does
not supply a slug. The base MUST be `slugify(source)[:40]`; if the slugified result is empty,
the base MUST be the literal `workspace`. Every attempt MUST always append a suffix — bare-base
values MUST NOT be tried — so the clean namespace stays available for deliberate organization
creation. Attempts 1 through 5 MUST use `f"{base}-{secrets.token_hex(3)}"` (a fresh 6-character
lowercase hex token per attempt). If all 5 attempts collide, a final attempt 6 MUST use
`f"workspace-{secrets.token_hex(8)}"`. If that also collides, the utility MUST raise an
`OrganizationError` rather than persist a duplicate or malformed slug. Every generated slug
MUST stay within `SlugField(max_length=60)` and MUST remain non-sequential, inheriting the
`Organization Entity` requirement's no-tenant-count-leakage constraint.

#### Scenario: Base derived from a normal source string

- GIVEN a source string `"Acme Corp"`
- WHEN a slug is generated
- THEN the base is `acme-corp`
- AND the generated slug is `acme-corp-{6 lowercase hex chars}`

#### Scenario: Non-Latin source falls back to the literal base

- GIVEN a source string that slugifies to an empty string
- WHEN a slug is generated
- THEN the base used is the literal `workspace`

#### Scenario: First attempt is never a bare base

- GIVEN any source string
- WHEN a slug is generated and no collision occurs
- THEN the returned slug is `{base}-{6-hex-char suffix}`, never the bare `{base}` alone

#### Scenario: Collision retried up to 5 suffixed attempts

- GIVEN the first 4 generated `{base}-{hex}` candidates already exist as slugs
- WHEN slug generation is attempted
- THEN a 5th `{base}-{hex}` candidate is tried
- AND if it does not collide, that candidate is returned

#### Scenario: Exhaustion falls back to the final long-token form

- GIVEN all 5 `{base}-{hex}` attempts collide
- WHEN slug generation continues
- THEN a 6th attempt uses the form `workspace-{16 lowercase hex chars}`
- AND if it does not collide, that candidate is returned

#### Scenario: Total exhaustion raises an error

- GIVEN all 5 `{base}-{hex}` attempts and the final `workspace-{token}` attempt all collide
- WHEN slug generation is attempted
- THEN the utility raises `OrganizationError`
- AND no slug is returned

#### Scenario: Generated slug never exceeds the field length

- GIVEN any base string up to 40 characters after truncation
- WHEN a slug is generated at any attempt
- THEN the resulting slug length is always at most 47 characters, within `SlugField(max_length=60)`

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
