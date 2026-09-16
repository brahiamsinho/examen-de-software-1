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
diagnostics. It MUST require role `EDITOR` or higher. Command application
for a given document MUST be serialized: the server MUST hold a row lock on
the target `UmlDocument` for the duration of the read-apply-persist
sequence, so that two commands submitted concurrently against the same
document can never both read the same starting revision and race to save.
Each command MUST still apply incrementally against the latest persisted
revision at the time it acquires the lock.

(Previously: command application read the `UmlDocument` row without any
lock, so two concurrent submissions against the same document could both
read the same starting revision and one persisted result could silently
overwrite the other — a lost update.)

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

#### Scenario: Concurrent commands against the same document do not lose an update

- GIVEN an existing document at revision N
- WHEN two `AddClass` commands are submitted concurrently against that
  document, both starting before either has persisted
- THEN both commands persist successfully, one serialized after the other
- AND the document's final revision is exactly N + 2
- AND both classes are present in the final persisted document
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
### Requirement: Document List

`GET /orgs/{org_slug}/documents` MUST return every `UmlDocument` scoped to
the resolved organization, ordered newest-updated-first
(`.order_by("-updated_at")`), gated exactly like `GET
/orgs/{org_slug}/documents/{doc_id}` (`resolve_membership` only, no
`require_role` — any member, `OWNER`/`EDITOR`/`VIEWER`, may read). Each item
in the response MUST be a lightweight summary (`id`, `name`, `revision`,
`updated_at`), not the full decoded model and layout.

#### Scenario: Viewer lists documents for their organization

- GIVEN two `UmlDocument`s persisted under organization `org`, the second
  updated more recently than the first
- WHEN an authenticated user with role `VIEWER` on `org` calls
  `GET /orgs/{org_slug}/documents`
- THEN the response returns both documents ordered with the more recently
  updated one first
- AND each item exposes only `id`, `name`, `revision`, and `updated_at`

#### Scenario: Owner and Editor can also list

- GIVEN a `UmlDocument` persisted under organization `org`
- WHEN a member with role `OWNER` or role `EDITOR` on `org` calls
  `GET /orgs/{org_slug}/documents`
- THEN the request succeeds and the document appears in the response

#### Scenario: Cross-tenant documents are absent, not 404

- GIVEN a `UmlDocument` belonging to organization `A` and none belonging to
  organization `B`
- WHEN a member of organization `B` calls `GET /orgs/B/documents`
- THEN the response is successful and does not include organization `A`'s
  document
- AND no unscoped `UmlDocument.objects.get`/`.all()` call is used to serve
  the list

#### Scenario: Empty organization returns an empty list

- GIVEN organization `org` has zero `UmlDocument`s
- WHEN a member of `org` calls `GET /orgs/{org_slug}/documents`
- THEN the response is successful and returns an empty list
### Requirement: Layout Persistence via Non-Command Path

The system MUST provide a service function, sibling to `submit_command`,
that persists a `DiagramLayout` update by calling
`ProjectDocument.with_layout()` under the same `@transaction.atomic` +
`select_for_update()` guarantee already used for command persistence, then
broadcasts the result via `broadcast_document`. This path MUST NOT route
through `dispatcher.apply()` or any `UmlCommand` variant, and the
`UmlCommand` union and its dispatcher MUST remain unmodified as a result of
this path's existence.

#### Scenario: Layout write persists and broadcasts without a command

- GIVEN an existing document at revision N
- WHEN the layout-write service function is called with a new final
  position for a class
- THEN the resulting `UmlDocument.layout` is persisted and the updated
  document is broadcast to the document's group, with no `UmlCommand`
  submitted

#### Scenario: UmlCommand union has zero diff

- GIVEN this change's complete diff
- WHEN the `UmlCommand` union and its dispatcher are inspected
- THEN neither shows any modified, added, or removed variant or dispatch
  branch

### Requirement: Revision Bumps Only on Persisted Position Release

`UmlDocument.revision` MUST increment by exactly 1 when a position release
is persisted via the layout write path, and MUST NOT increment for a claim
or for any `position_update`, since neither reaches this persistence path.

#### Scenario: Release increments revision by exactly 1

- GIVEN a document at revision N
- WHEN a position release is persisted via the layout write path
- THEN the document's revision becomes exactly N + 1

#### Scenario: Live position updates never touch revision

- GIVEN a document at revision N
- WHEN any number of `position_update` messages are processed for that
  document without a release
- THEN the document's revision remains N

### Requirement: Absent Class Ids Are Pruned From Persisted Layout

When persisting a layout update, an entry referencing a class id no longer
present in the document's current `CanonicalUmlModel` MUST be dropped
rather than persisted or causing an error.

#### Scenario: Persisting a position for a since-removed class is a no-op

- GIVEN a class was removed from the document after a drag on it began
- WHEN the layout-write service function is called with that now-absent
  class id
- THEN the entry is dropped without error and the persisted layout contains
  no entry for that class id
