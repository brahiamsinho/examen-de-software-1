# Tenant Isolation Specification

## Purpose

State and enforce the cross-cutting rule that every tenant-scoped row is bound to exactly one
`organization_id`, that scoping is explicit rather than implicit, and that non-members can
never observe the existence of an organization they do not belong to.

## Requirements

### Requirement: Tenant-Scoped Model Base

Every tenant-scoped model MUST inherit an abstract `TenantScopedModel` carrying a non-null
`organization` foreign key. Its manager MUST expose `for_organization(org)` as the normal
access path, and MUST expose a deliberately explicit `.unscoped()` escape hatch for any access
outside a single organization's boundary.

#### Scenario: Scoped query returns only that organization's rows

- GIVEN tenant-scoped rows exist across two different organizations
- WHEN a query is made through `for_organization(org_a)`
- THEN only rows belonging to `org_a` are returned

#### Scenario: Unscoped access requires the explicit escape hatch

- GIVEN tenant-scoped rows exist across multiple organizations
- WHEN code needs to read across organizations
- THEN it MUST call `.unscoped()` explicitly
- AND no default manager method returns cross-organization rows implicitly

### Requirement: Tenant Key in the URL Path

Tenant-scoped routes MUST carry the tenant key as an explicit URL path segment
(`/orgs/{org_slug}/...`). The system MUST NOT treat any session-stored organization value as
authoritative for authorization; a session MAY store a "last used organization" only as a UI
convenience default.

#### Scenario: Authorization never relies on session state

- GIVEN a user has a session-stored "last used organization" different from the one in the
  request path
- WHEN a tenant-scoped request is made against a path-specified organization
- THEN authorization is evaluated against the path's organization, not the session value

### Requirement: Per-Request Membership Resolution

The system MUST resolve the caller's `Membership` for the organization named in the URL path
on every tenant-scoped request, via a shared resolver, before any tenant-scoped work proceeds.

#### Scenario: Valid member resolves and proceeds

- GIVEN an authenticated user who is a member of the organization named by the path slug
- WHEN a tenant-scoped endpoint is called
- THEN the resolver returns that user's `Membership`
- AND the endpoint proceeds using the resolved organization

#### Scenario: Unknown slug resolves to not-found

- GIVEN a path slug that matches no organization
- WHEN a tenant-scoped endpoint is called
- THEN the request is rejected with `404`

### Requirement: Non-Member Response Contract

A caller who is authenticated but is not a member of the organization named in the path MUST
receive `404`, not `403`, so that organization existence is never leaked to non-members.

#### Scenario: Non-member request on an existing organization

- GIVEN an authenticated user who is not a member of an organization that exists
- WHEN that user requests a tenant-scoped route for that organization
- THEN the response is `404`
- AND the response is indistinguishable from requesting a slug that does not exist at all

### Requirement: Unscoped-Reachability Test Coverage

The system MUST include an automated test that enumerates every concrete `TenantScopedModel`
subclass and asserts none of them is reachable through a default, unscoped path without the
explicit `.unscoped()` call.

#### Scenario: Test enumerates and asserts scoped-only reachability

- GIVEN the set of concrete `TenantScopedModel` subclasses in the codebase
- WHEN the isolation test suite runs
- THEN each subclass is confirmed reachable only via `for_organization()` or the explicit
  `.unscoped()` call
- AND the test fails if a new subclass is added without satisfying this contract
