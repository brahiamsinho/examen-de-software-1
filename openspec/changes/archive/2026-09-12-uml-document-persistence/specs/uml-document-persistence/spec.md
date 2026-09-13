# UML Document Persistence Specification

## Purpose

Persist `ProjectDocument` as a tenant-scoped Django model and expose the
minimum HTTP surface (create, read, submit-command) so a real client can
create a document, mutate it through the `uml_commands` dispatcher, and
read back the result — without changing `apps.uml_modeling` or
`apps.uml_commands`.

## Requirements

### Requirement: Document Creation

`POST /orgs/{org_slug}/documents` MUST create a new `UmlDocument` scoped to
the resolved organization from an empty `CanonicalUmlModel` and
`DiagramLayout`, with `owner_id` set to `str(request.user.id)` and an
initial `revision` of 1. It MUST require role `EDITOR` or higher.

#### Scenario: Editor creates an empty document

- GIVEN an authenticated user with role `EDITOR` on organization `org`
- WHEN they `POST /orgs/{org_slug}/documents` with `{"name": "My Diagram"}`
- THEN a `UmlDocument` is persisted scoped to `org` with `owner_id` equal to `str(request.user.id)`
- AND the response returns `revision == 1`, an empty model, and an empty layout

#### Scenario: Viewer is denied creation

- GIVEN an authenticated user with role `VIEWER` on organization `org`
- WHEN they `POST /orgs/{org_slug}/documents`
- THEN the request is rejected and no `UmlDocument` is created

### Requirement: Document Read

`GET /orgs/{org_slug}/documents/{doc_id}` MUST return the full decoded
document (metadata, model, layout, revision) for any member of the
resolved organization, and MUST return 404 for a document belonging to a
different organization.

#### Scenario: Any member reads back the persisted document

- GIVEN a `UmlDocument` persisted under organization `org` with prior commands applied
- WHEN a member of `org` with role `VIEWER` or higher calls `GET .../documents/{doc_id}`
- THEN the response's model, layout, and revision exactly match what was persisted

#### Scenario: Cross-tenant read returns 404

- GIVEN a `UmlDocument` belonging to organization `A`
- WHEN a member of organization `B` calls `GET /orgs/B/documents/{doc_id}`
- THEN the response is 404, not 403, and no document content is returned

### Requirement: Command Submission

`POST /orgs/{org_slug}/documents/{doc_id}/commands` MUST accept one
`{type, payload}` body mapped to a `UmlCommand` subtype via a
discriminated-union schema, apply it through `dispatcher.apply()`, persist
the resulting document, and return the new `revision` plus validation
diagnostics. It MUST require role `EDITOR` or higher.

#### Scenario: Sequential commands persist across calls

- GIVEN an empty document owned by an `EDITOR`
- WHEN `AddClass` is submitted, then `AddAttribute` targeting the class just added is submitted in a second call
- THEN the second call's resulting document contains the class with the new attribute
- AND each call's returned `revision` increments by exactly 1 over the prior persisted revision

#### Scenario: Viewer is denied command submission

- GIVEN an authenticated user with role `VIEWER` on the document's organization
- WHEN they submit any command to `.../documents/{doc_id}/commands`
- THEN the request is rejected and the document is not modified

#### Scenario: Invalid result still persists with diagnostics

- GIVEN a document containing only class A
- WHEN `AddRelationship` is submitted with source A and a nonexistent target class id
- THEN the response is successful (not an error) and reflects the new revision containing the relationship
- AND the response's diagnostics are non-empty and include an `INVALID_RELATIONSHIP_ENDPOINT` entry
- AND the persisted document matches the returned state

### Requirement: Codec Round-Trip Correctness

The `codec` MUST losslessly round-trip any `CanonicalUmlModel` and
`DiagramLayout` value: encoding to JSON and decoding back MUST yield a
value equal to the original, including `ElementId`-keyed mappings and
nested tuples of frozen dataclasses.

#### Scenario: Non-trivial model and layout round-trip exactly

- GIVEN a `CanonicalUmlModel` fixture with multiple classes, attributes, relationships, and a non-empty `generation_metadata` mapping, plus a `DiagramLayout` with a non-empty `positions` mapping
- WHEN the fixture is encoded via `codec.to_json` and decoded via `codec.from_json`
- THEN the decoded `CanonicalUmlModel` and `DiagramLayout` are equal to the originals, including mapping keys and nested tuple structure

### Requirement: Tenant Scoping on Every Access

Every `uml_documents` handler MUST resolve the caller's organization via
`resolve_membership(request, org_slug)` before touching `UmlDocument`, and
MUST load documents only through `UmlDocument.objects.for_organization(org)`
— never through an unscoped default-manager lookup. A document created
under one organization MUST be unreachable, as a 404, through any other
organization's slug.

#### Scenario: A document is unreachable through another organization's slug

- GIVEN a `UmlDocument` created under organization `A`
- WHEN a member of organization `B` requests it via any of the three endpoints using `org_slug=B`
- THEN the response is 404
- AND no unscoped `UmlDocument.objects.get(id=...)` call is used to serve any handler

### Requirement: uml_documents Import Boundary

`apps/uml_documents` MUST depend only on `apps.uml_modeling`,
`apps.uml_commands`, `apps.organizations` (needed for `TenantScopedModel`,
`TenantScopedManager`, `resolve_membership`, `require_role`, and `Role` —
this is the same tenancy root every tenant-scoped app in this codebase
depends on, unlike the pure-domain `apps.uml_commands`), the Python
standard library, and Django/ninja/pydantic. It MUST NOT import
`apps.users` (the caller's identity reaches this app only as Django's
built-in `request.user`, never through the `apps.users` domain models). It
MUST NOT modify any file under `apps/uml_modeling/` or `apps/uml_commands/`.

#### Scenario: uml_modeling and uml_commands have zero diff

- GIVEN this change's complete diff
- WHEN files under `apps/uml_modeling/` and `apps/uml_commands/` are inspected
- THEN neither directory shows any modified, added, or removed file
