# Delta for UML Document Persistence

## ADDED Requirements

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
