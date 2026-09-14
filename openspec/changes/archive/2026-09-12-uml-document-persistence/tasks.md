# Tasks: UML Document Persistence + API

Strict TDD. Test command: `cd backend && pytest apps/uml_documents -q`
(verified convention, matching `uml_modeling`/`uml_commands`). Full-suite
regression: `cd backend && pytest -q`. Backend-only; `apps/uml_modeling/`
and `apps/uml_commands/` stay untouched.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1050-1300 (production: apps.py/init ~10, `models.py` ~40, migration ~50, `codec.py` ~170, `services.py` ~120, `schemas.py` ~140, `api.py` ~70, settings/router-mount ~3; tests: factories ~70, codec ~100, services ~150, schemas ~40, api ~150, import-boundary ~40, integration ~80) |
| 800-line budget risk | **High** — likely exceeds the session's fixed single-pr/800-line budget, unlike the prior `uml-command-bus` cycle (~650-750, Low) |
| Chained PRs recommended | **Yes** |
| Suggested split | PR 1 (skeleton+model+migration+codec) -> PR 2 (services+schemas) -> PR 3 (api+integration+structural+verification) |
| Delivery strategy | ask-on-risk (assumed default; not overridden by the requester) |
| Chain strategy | pending — user decision required |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
800-line budget risk: High

This cycle is larger than `uml-command-bus` by design: a Django model +
migration, a from-scratch codec, a first-of-its-kind discriminated-union
schema, a full REST API layer, and a Django test-client integration suite,
all new. Do not proceed with `sdd-apply` as a single PR until the user
picks `stacked-to-main`, `feature-branch-chain`, or `size:exception`.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Package skeleton, `UmlDocument` model, migration, `codec.py` round-trip | PR 1 | `cd backend && pytest apps/uml_documents/tests/test_apps.py apps/uml_documents/tests/test_models.py apps/uml_documents/tests/test_codec.py -q` | `cd backend && python manage.py migrate uml_documents` against test DB | Delete `backend/apps/uml_documents/` and its `INSTALLED_APPS` line — no other app touched |
| 2 | `services.py` (create/get/submit/command_from_payload) + `schemas.py` | PR 2 | `cd backend && pytest apps/uml_documents/tests/test_services.py apps/uml_documents/tests/test_schemas.py -q` | N/A — pure service/schema unit tests against test DB, no live HTTP harness needed | Revert PR 2's two files; PR 1's model/codec stay independently valid |
| 3 | `api.py`, router mount, import-boundary + integration tests, verification | PR 3 | `cd backend && pytest apps/uml_documents -q` | `cd backend && python manage.py runserver` + manual `POST /orgs/{slug}/documents` round trip | Revert `api.py`, the `config/api.py` router-mount line, and `config/settings.py` line — PR 1/2 remain functional as a library |

## Phase 1: Package Skeleton, Model & Migration

- [x] 1.1 Create `backend/apps/uml_documents/{__init__.py,apps.py}`
  (`UmlDocumentsConfig(AppConfig)`, `name = "apps.uml_documents"`, `label =
  "uml_documents"`), `tests/__init__.py`; add `"apps.uml_documents"` under
  the `# Local` marker in `INSTALLED_APPS` (`backend/config/settings.py`),
  alongside `apps.uml_commands`. [prerequisite for all requirements]
- [x] 1.2 RED: `tests/test_apps.py` — app registers with `label ==
  "uml_documents"`. GREEN: implement `apps.py`. [prerequisite]
- [x] 1.3 RED: `tests/test_models.py` — `UmlDocument` has `id` (UUID PK,
  default `uuid4`), `owner_id` (CharField), `revision` (PositiveIntegerField,
  default 1), `created_at`/`updated_at` (DateTimeField), `data` (JSONField,
  default dict); `objects` is `TenantScopedManager`, `all_objects` is the
  default `Manager`, `Meta.base_manager_name == "all_objects"`.
- [x] 1.4 GREEN: implement `backend/apps/uml_documents/models.py` —
  `UmlDocument(TenantScopedModel)` per design's Interfaces/Contracts block.
  [Document Creation infra, Tenant Scoping on Every Access; DD3, DD4]
- [x] 1.5 Generate `backend/apps/uml_documents/migrations/0001_initial.py`
  via `cd backend && python manage.py makemigrations uml_documents`
  (depends on `organizations`' latest migration); confirm it applies
  cleanly against the test DB.

## Phase 2: Codec (pure functions, testable standalone)

- [x] 2.1 Create `tests/factories.py` — `a_metadata`, `a_model` (multi-class,
  multi-enumeration, multi-relationship, non-empty `generation_metadata`),
  `a_layout` (non-empty `positions`) builders wrapping `uml_modeling`'s own
  domain constructors. Reused by codec, services, and integration tests.
- [x] 2.2 RED: `tests/test_codec.py` — `to_json(metadata, model, layout)` ->
  `from_json(data)` round-trips the non-trivial fixture exactly, including
  `ElementId`-keyed mapping keys and nested tuple structure; both
  `AttributeType` branches (`PrimitiveType` string, `EnumerationRef` tagged
  object) round-trip; empty collections round-trip too.
- [x] 2.3 GREEN: implement `backend/apps/uml_documents/codec.py` —
  `to_json`/`from_json` + `_encode_class`/`_decode_class`,
  `_encode_enumeration`/`_decode_enumeration`,
  `_encode_relationship`/`_decode_relationship`,
  `_encode_attribute_type`/`_decode_attribute_type`,
  `_encode_layout`/`_decode_layout`. [Codec Round-Trip Correctness; DD5,
  DD6, DD7]

## Phase 3: Services

- [x] 3.1 RED: `tests/test_services.py::test_create_document` —
  `create_document(organization, owner_id, name, now=...)` persists a
  `UmlDocument` scoped to `organization`, `owner_id` set, `revision == 1`,
  empty `CanonicalUmlModel`/`DiagramLayout` content in `data`.
- [x] 3.2 GREEN: implement `create_document` in `services.py`. [Document
  Creation; DD3]
- [x] 3.3 RED: extend `test_services.py::test_get_document` —
  `get_document(organization, doc_id)` returns the decoded document
  matching what was persisted; raises `Http404` for a `doc_id` belonging to
  a different organization; uses `.for_organization(...)` only.
- [x] 3.4 GREEN: implement `get_document`. [Document Read; Tenant Scoping
  on Every Access]
- [x] 3.5 RED: extend `test_services.py::test_command_from_payload` —
  `command_from_payload` maps each of the 7 `CommandIn` payload shapes to
  its matching `UmlCommand` dataclass.
- [x] 3.6 GREEN: implement `command_from_payload` (7-way dispatch on
  `payload.type`) in `services.py`. [Command Submission — schema->domain
  mapping; DD8]
- [x] 3.7 RED: extend `test_services.py::test_submit_command` —
  `submit_command(organization, doc_id, command, now=...)` loads the row,
  calls `dispatcher.apply`, persists the result, returns the unchanged
  `CommandResult`; two sequential calls each increment the persisted
  revision by exactly 1; a command producing `INVALID_RELATIONSHIP_ENDPOINT`
  diagnostics still persists (never gated on `is_blocking`).
- [x] 3.8 GREEN: implement `submit_command` in `services.py`. [Command
  Submission — Sequential commands persist, Invalid result still persists
  with diagnostics]

## Phase 4: Schemas

- [x] 4.1 RED: `tests/test_schemas.py` — `CommandIn` (discriminated union)
  parses each of the 7 `{type, ...}` shapes into its matching sub-schema
  by the `type` discriminator; `DocumentCreateIn` requires `name`;
  `DocumentOut`/`CommandResultOut`/`ValidationOut`/`DiagnosticOut`
  instantiate from services-shaped dicts without error.
- [x] 4.2 GREEN: implement `backend/apps/uml_documents/schemas.py` —
  `AddClassIn`..`RemoveRelationshipIn`, `CommandIn` union
  (`Field(discriminator="type")`), `DocumentCreateIn`, `MetadataOut`,
  `DocumentOut`, `DiagnosticOut`, `ValidationOut`, `CommandResultOut`.
  [Command Submission — discriminated-union schema; DD2]

## Phase 5: API

- [x] 5.1 RED: `tests/test_api.py::test_create_document` — `POST
  /orgs/{slug}/documents` as `EDITOR` returns 201 with `revision == 1`,
  empty model/layout; as `VIEWER` returns 403 and no `UmlDocument` is
  created.
- [x] 5.2 GREEN: implement `create_document_view` in
  `backend/apps/uml_documents/api.py` (`documents_router`,
  `resolve_membership` -> `require_role(OWNER, EDITOR)` ->
  `services.create_document` -> `DocumentOut`); mount `documents_router` in
  `backend/config/api.py`. [Document Creation scenarios; DD9]
- [x] 5.3 RED: extend `test_api.py::test_get_document` — `GET
  .../documents/{doc_id}` as `VIEWER` returns the persisted model/layout/
  revision exactly; a `doc_id` from a different org returns 404.
- [x] 5.4 GREEN: implement `get_document_view` (`resolve_membership` only,
  no `require_role`). [Document Read scenarios]
- [x] 5.5 RED: extend `test_api.py::test_submit_command` — `POST
  .../commands` as `EDITOR` with `AddClass` then `AddAttribute` in two
  sequential calls persists both, each response's `revision` increments by
  1; as `VIEWER` returns 403 and the document is unmodified;
  `AddRelationship` with a nonexistent target returns 200 with non-empty
  violations including `INVALID_RELATIONSHIP_ENDPOINT` and the new
  revision.
- [x] 5.6 GREEN: implement `submit_command_view` (`Body[CommandIn]` ->
  `services.command_from_payload` -> `services.submit_command` ->
  `CommandResultOut` dict). [Command Submission scenarios]

## Phase 6: Structural — Import Boundary

- [x] 6.1 Add `tests/test_import_boundary.py` — `ast.parse` each of
  `models.py`/`codec.py`/`services.py`/`schemas.py`; assert every
  non-stdlib import target starts with `apps.uml_modeling`,
  `apps.uml_commands`, `apps.organizations`, `apps.uml_documents`
  (self-package), `django`, `ninja`, or `pydantic`; assert no import target
  starts with `apps.users`. `api.py` is excluded from the scoped file set
  (its `resolve_membership`/`require_role`/`Role` imports are the same
  `apps.organizations` dependency already allowed for `models.py`, not a
  separate concern — mirrors `uml_commands`' own precedent of excluding
  `apps.py` from its boundary test). `apps.organizations` is allowed, not
  forbidden: `uml_documents` is a real persisted, tenant-scoped Django app
  (like `apps/organizations` itself), not a pure-domain app like
  `uml_commands` — `TenantScopedModel`/`TenantScopedManager`/
  `resolve_membership`/`require_role`/`Role` all live only in
  `apps.organizations`, so this dependency is required, not a violation
  (spec.md's Import Boundary requirement corrected accordingly). Expected
  to pass immediately against Phases 1-5's source. [uml_documents Import
  Boundary; DD1]

## Phase 7: Integration

- [x] 7.1 RED: `tests/test_integration.py` — composed scenario: create ->
  `AddClass` -> `AddAttribute` -> `get`, asserting the final `GET` reflects
  both commands and the correct cumulative revision; a second
  organization's member requesting the same `doc_id` via all three
  endpoints gets 404 on each.
- [x] 7.2 GREEN: no new production code expected; fix any handler/service/
  api gap the composed scenario surfaces. [Tenant Scoping on Every Access —
  end-to-end confirmation]

## Phase 8: Verification

- [x] 8.1 Run `cd backend && pytest apps/uml_documents -q`; confirm all 6
  requirements' 10 scenarios and both structural tests pass.
- [x] 8.2 Run `cd backend && pytest -q`; confirm zero regressions.
- [x] 8.3 Confirm `apps/uml_modeling/` and `apps/uml_commands/` have zero
  diff: `git diff --stat backend/apps/uml_modeling backend/apps/uml_commands`
  returns empty.
