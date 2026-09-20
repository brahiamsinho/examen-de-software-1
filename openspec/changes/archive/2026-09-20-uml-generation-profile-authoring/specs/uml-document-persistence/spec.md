# UML Document Persistence Delta: Generation Profile Authoring

Delta against `openspec/specs/uml-document-persistence/spec.md`. Requirements not listed here (Document Creation, Document Read, Command Submission, Codec Round-Trip Correctness, Tenant Scoping on Every Access, Document List, Layout Persistence via Non-Command Path, Revision Bumps Only on Persisted Position Release, Absent Class Ids Are Pruned From Persisted Layout) are unchanged. The `SetGenerationProfile` command semantics live in `uml-command-bus`; the profile vocabulary and strict parse rules live in `generation-profile` and are reused verbatim at write time. Design decisions: DD151-DD159 (`design.md`).

Verification key: **[pytest]** = automated in the default suite; **[manual]** = verified by a recorded gate run.

## ADDED Requirements

### Requirement: Generation Profile Command Submission

`POST /orgs/{org_slug}/documents/{doc_id}/commands` MUST accept `{"type": "SetGenerationProfile", "element_id": <str>, "profile": <object | null>}`. `apps/uml_documents/schemas.py` MUST define `SetGenerationProfileIn(Schema)` with `type: Literal["SetGenerationProfile"]`, `element_id: str` and `profile: dict | None = None` (absent, `null`, and `{}` all mean "clear"), appended as the LAST member of the `CommandIn` discriminated union (discriminator `"type"` unchanged). `services._command_from_payload` MUST map it to `commands.SetGenerationProfile(element_id=ElementId(payload.element_id), profile=payload.profile)`. The nested `crud` list and `defaultSort` object MUST survive as plain JSON. **[pytest]**

The server MUST infer the level from the model (DD151): an `element_id` that is a class id is table level; one that is an attribute id is column level. The client MUST NOT supply a level.

Semantic validation MUST run in `services.submit_command` inside the existing `@transaction.atomic` + `select_for_update()` block, after the document is decoded and BEFORE `dispatcher.apply(...)` (DD153), via `_validate_generation_profile(model, command)`, only when the command is a `SetGenerationProfile`. In order:

1. Level inference always runs (DD155): an `element_id` matching neither a class id nor an attribute id of the document raises `InvalidCommandPayloadError(f"Unknown element id {command.element_id!r}: not a class or attribute of this document")`, even when `profile` is `None` or `{}` (a clear).
2. If `profile` is `None` or `{}`, validation returns (a clear needs no parse).
3. Otherwise the body is validated as `{"profile": <body>}` by the already-shipped strict parser: `parse_table_profile(element_id, entry)` for a class id, `parse_column_profile(element_id, entry)` for an attribute id. An `InvalidGenerationProfileError` MUST be re-raised as `InvalidCommandPayloadError(str(exc))` with the parser's message preserved **verbatim** (including its `element_id`/`key` framing). The service MUST NOT duplicate any section 33 rule.
4. For a class-level profile whose parsed `default_sort` is not `None`, `defaultSort.attribute` MUST resolve (DD157) against the allowed id set: the class's own attribute ids, plus, when the class is an **inheritance root** (no outgoing `GENERALIZATION` relationship where it is `source`), the attribute ids of its transitive descendants (BFS over `GENERALIZATION` relationships whose `target.class_id` is the current class). An id outside that set MUST raise `InvalidCommandPayloadError` with exactly:
   - class is not an inheritance root, or has no descendants: `Invalid generation profile for element {element_id!r}, key 'defaultSort.attribute': {attribute_id!r} is not an attribute of this class`
   - class is an inheritance root **with** at least one descendant: `Invalid generation profile for element {element_id!r}, key 'defaultSort.attribute': {attribute_id!r} is not an attribute of this class or its descendants`

Every `InvalidCommandPayloadError` above MUST be served as HTTP **422** with body `{"detail": <message>, "code": "invalid_command_payload"}` by the existing `api.register_exception_handlers`; `api.py` MUST NOT change. Because validation runs before `apply` inside the lock, a 422 MUST leave the persisted document row (including `revision`) unmodified and MUST broadcast nothing. Authorization MUST be unchanged: the existing `require_role(OWNER, EDITOR)` gate covers the command, a VIEWER is rejected with 403 and the document is not modified, and a document of another organization is 404. On success the response, the `revision` bump (+1, via `dispatcher.apply`), the after-commit `broadcast_document`, `DocumentOut`, and `codec.to_json`/`codec.from_json` (which already round-trip `generation_metadata` verbatim) MUST be unchanged. **[pytest]**

#### Scenario: Schema discriminates SetGenerationProfile

- GIVEN a payload `{"type": "SetGenerationProfile", "element_id": "c1", "profile": {"crud": ["create", "read"], "defaultSort": {"attribute": "a1", "direction": "asc"}}}`
- WHEN it is validated with `TypeAdapter(CommandIn)`
- THEN it parses to `SetGenerationProfileIn` with `crud` and `defaultSort` intact as plain JSON **[pytest]**

#### Scenario: Profile absent, null, and empty all parse as a clear

- GIVEN three payloads with `profile` omitted, `null`, and `{}` respectively
- WHEN each is validated with `TypeAdapter(CommandIn)`
- THEN each parses to `SetGenerationProfileIn`, and the mapped command's `profile` is falsy (`None` or `{}`) **[pytest]**

#### Scenario: Editor authors a table profile

- GIVEN a document at revision N with class C, and an authenticated `EDITOR`
- WHEN they submit `{"type": "SetGenerationProfile", "element_id": C.id, "profile": {"auditable": true}}`
- THEN the response is 200 with `revision == N + 1` and diagnostics
- AND the persisted `model.generation_metadata[C.id]["profile"] == {"auditable": true}` **[pytest]**

#### Scenario: Owner authors a column profile

- GIVEN a document with class C owning attribute A, and an authenticated `OWNER`
- WHEN they submit `SetGenerationProfile` with `element_id == A.id` and `profile == {"searchable": true, "sortable": true}`
- THEN the response is 200 and `generation_metadata[A.id]["profile"] == {"searchable": true, "sortable": true}` **[pytest]**

#### Scenario: Viewer is denied

- GIVEN an authenticated user with role `VIEWER` on the document's organization
- WHEN they submit a valid `SetGenerationProfile`
- THEN the response is 403 and the persisted document (revision and model) is unmodified **[pytest]**

#### Scenario: Cross-organization document is 404

- GIVEN a document belonging to organization `A`
- WHEN a member of organization `B` submits `SetGenerationProfile` via `org_slug=B`
- THEN the response is 404 and nothing is modified **[pytest]**

#### Scenario: Unknown element id is rejected with the exact message

- GIVEN a document with no class or attribute matching id X
- WHEN `SetGenerationProfile(X, {"auditable": true})` is submitted
- THEN the response is 422 with `code == "invalid_command_payload"` and `detail == "Unknown element id 'X': not a class or attribute of this document"`
- AND the persisted revision is unchanged **[pytest]**

#### Scenario: Clearing an unknown element id is still a 422

- GIVEN a document with no element matching id X
- WHEN `SetGenerationProfile(X, None)` and `SetGenerationProfile(X, {})` are each submitted
- THEN each response is 422 with the same "Unknown element id" message, not a silent 200 (DD155)
- AND the persisted revision is unchanged **[pytest]**

#### Scenario: Each parser rule violation is a 422 with the parser's verbatim message

- GIVEN a class id C and profile bodies violating each rule: an unknown key, a non-boolean `auditable`, a `crud` member outside the vocabulary, a duplicate `crud` member, and an invalid `defaultSort.direction`
- WHEN each is submitted for C
- THEN each response is 422 with `code == "invalid_command_payload"` and `detail` identical to `str(InvalidGenerationProfileError)` raised by `parse_table_profile` for the same input
- AND the persisted revision is unchanged **[pytest]**

#### Scenario: Wrong-level keys are rejected

- GIVEN class C owning attribute A
- WHEN a table-only key (for example `crud`) is submitted for `A.id`, and a column-only key (for example `searchable`) is submitted for `C.id`
- THEN each response is 422 with the strict parser's message and nothing is persisted **[pytest]**

#### Scenario: defaultSort on an own attribute is accepted

- GIVEN class C owning attribute A
- WHEN `SetGenerationProfile(C.id, {"defaultSort": {"attribute": A.id, "direction": "asc"}})` is submitted
- THEN the response is 200 and the profile is persisted **[pytest]**

#### Scenario: A root may sort by a descendant's attribute

- GIVEN inheritance root R (no outgoing `GENERALIZATION`) and class S with `GENERALIZATION` from S to R (transitively, also a grandchild T under S), S owning attribute SA
- WHEN `SetGenerationProfile(R.id, {"defaultSort": {"attribute": SA.id, "direction": "desc"}})` is submitted
- THEN the response is 200 and the profile is persisted, and the same holds for an attribute owned by the transitive descendant T **[pytest]**

#### Scenario: A non-root class cannot sort by another class's attribute

- GIVEN non-root class S (it has an outgoing `GENERALIZATION`) and attribute RA owned by its parent R
- WHEN `SetGenerationProfile(S.id, {"defaultSort": {"attribute": RA.id, "direction": "asc"}})` is submitted
- THEN the response is 422 with `detail == "Invalid generation profile for element 'S-id', key 'defaultSort.attribute': 'RA-id' is not an attribute of this class"` (with the real ids substituted via `!r`)
- AND nothing is persisted **[pytest]**

#### Scenario: An unrelated class's attribute is rejected for a root with descendants

- GIVEN inheritance root R with at least one descendant, and attribute XA owned by an unrelated class X
- WHEN `SetGenerationProfile(R.id, {"defaultSort": {"attribute": XA.id, "direction": "asc"}})` is submitted
- THEN the response is 422 with `detail == "Invalid generation profile for element 'R-id', key 'defaultSort.attribute': 'XA-id' is not an attribute of this class or its descendants"` (with the real ids substituted via `!r`)
- AND nothing is persisted **[pytest]**

#### Scenario: A standalone class with no descendants uses the short message

- GIVEN class C that is an inheritance root (no outgoing `GENERALIZATION`) with no descendants, and an attribute XA owned by another class
- WHEN `SetGenerationProfile(C.id, {"defaultSort": {"attribute": XA.id, "direction": "asc"}})` is submitted
- THEN the response is 422 with the `... is not an attribute of this class` message (without "or its descendants") **[pytest]**

#### Scenario: Validation runs inside the lock and before apply

- GIVEN any 422 rejection above
- WHEN the document row is re-read
- THEN `revision`, `data`, and `updated_at` are unchanged and no broadcast was scheduled, because `_validate_generation_profile` runs after `_to_project_document` and before `apply(...)` inside the `@transaction.atomic` + `select_for_update()` block **[pytest]**

#### Scenario: A cleared profile persists and broadcasts like any command

- GIVEN a document whose class C has a persisted profile, at revision N
- WHEN `SetGenerationProfile(C.id, null)` is submitted by an `EDITOR`
- THEN the response is 200 with `revision == N + 1` and the persisted `generation_metadata` has no entry for C
- AND the after-commit `broadcast_document` is invoked exactly as for any other command **[pytest]**

#### Scenario: A profile survives the codec round-trip

- GIVEN a model with `generation_metadata[C.id] == {"source": "ai", "profile": {"auditable": true, "crud": ["read"], "defaultSort": {"attribute": "a1", "direction": "asc"}}}`
- WHEN it is encoded via `codec.to_json` and decoded via `codec.from_json`
- THEN the decoded `generation_metadata` equals the original, including the sibling `source` key and the nested `crud` list and `defaultSort` object **[pytest]**

#### Scenario: An authored profile reaches Table.profile and Column.profile through map_to_relational

- GIVEN a real document row with a class C and an attribute A, and both `SetGenerationProfile(C.id, {"entity": true, "auditable": true, "crud": ["create", "read"], "defaultSort": {"attribute": A.id, "direction": "asc"}})` and `SetGenerationProfile(A.id, {"searchable": true})` submitted through the endpoint
- WHEN the document is reloaded, decoded via `codec.from_json`, and passed to `map_to_relational`
- THEN the resulting `Table.profile == TableProfile(entity=True, auditable=True, crud=(CREATE, READ), default_sort=DefaultSort(...))` and the resulting `Column.profile == ColumnProfile(searchable=True, ...)` **[pytest]**

#### Scenario: Clearing the profile maps back to an undeclared table

- GIVEN the document of the previous scenario
- WHEN `SetGenerationProfile(C.id, null)` is submitted, and the document is reloaded and mapped again
- THEN `Table.profile is None` for C's table **[pytest]**

#### Scenario: A root's defaultSort on a descendant attribute survives the round trip

- GIVEN a Single Table hierarchy with root R and descendant S owning attribute SA, and `SetGenerationProfile(R.id, {"defaultSort": {"attribute": SA.id, "direction": "asc"}})` submitted
- WHEN the document is reloaded, decoded, and passed to `map_to_relational`
- THEN the root's table (the single STI table) carries a `Table.profile` whose `default_sort.attribute_id == SA.id` and mapping does not fail **[pytest]**

## MODIFIED Requirements

### Requirement: uml_documents Import Boundary

`apps/uml_documents` MUST depend only on `apps.uml_modeling`,
`apps.uml_commands`, `apps.organizations` (needed for `TenantScopedModel`,
`TenantScopedManager`, `resolve_membership`, `require_role`, and `Role` —
this is the same tenancy root every tenant-scoped app in this codebase
depends on, unlike the pure-domain `apps.uml_commands`), the Python
standard library, and Django/ninja/pydantic. It MUST NOT import
`apps.users` (the caller's identity reaches this app only as Django's
built-in `request.user`, never through the `apps.users` domain models).

The single named exception (DD154): `services.py` MAY import
`apps.relational_mapping.mapping.profile_parser` (to call
`parse_table_profile` / `parse_column_profile` at write time), and no other
`apps.relational_mapping` module. The allowance MUST be an exact module match, never a prefix: every other
`apps.relational_mapping.*` target MUST remain disallowed and fail the guard
loudly (`mapper`, `schema`, and the rest of the app stay unreachable).
`apps/uml_commands`' own import guard is unchanged and stays pure.

`apps/uml_modeling/` MUST remain unmodified for this capability.
`apps.uml_documents` MUST NOT own UML mutation semantics: every command
dataclass, handler, and dispatcher registration MUST live under
`apps/uml_commands/`; `uml_documents` MUST only construct
`apps.uml_commands.commands` values and call `dispatcher.apply`.
(Previously: "It MUST NOT modify any file under `apps/uml_modeling/` or
`apps/uml_commands/`", a change-local freeze of `apps/uml_commands/` that this
capability supersedes with the standing dependency-direction rule above; the
`apps.relational_mapping` exception is new.)

#### Scenario: uml_modeling has zero diff

- GIVEN this change's complete diff
- WHEN files under `apps/uml_modeling/` are inspected
- THEN the directory shows no modified, added, or removed file **[manual]**

#### Scenario: command semantics stay in uml_commands

- GIVEN the `apps/uml_documents` source files `models`, `codec`, `services`, `schemas`, and `errors`
- WHEN they are statically inspected
- THEN none defines a command dataclass, a handler function, or a dispatcher registration; `services.py` only constructs `apps.uml_commands.commands` values and calls `dispatcher.apply` **[pytest]**

#### Scenario: exactly one relational_mapping module is importable

- GIVEN the `uml_documents` package source
- WHEN its imports are statically inspected by `test_no_disallowed_imports_exist`
- THEN the only `apps.relational_mapping` import target permitted is exactly `apps.relational_mapping.mapping.profile_parser`
- AND `_ALLOWED_EXACT_MODULES == ("apps.relational_mapping.mapping.profile_parser",)` is pinned by `test_relational_mapping_exception_is_exactly_one_module`
- AND a synthetic import of any other `apps.relational_mapping.*` module (for example `apps.relational_mapping.mapping.mapper`) still fails the guard, as does any `apps.users` import **[pytest]**

### Requirement: Layout Persistence via Non-Command Path

The system MUST provide a service function, sibling to `submit_command`,
that persists a `DiagramLayout` update by calling
`ProjectDocument.with_layout()` under the same `@transaction.atomic` +
`select_for_update()` guarantee already used for command persistence, then
broadcasts the result via `broadcast_document`. This path MUST NOT route
through `dispatcher.apply()` or any `UmlCommand` variant, and the existence
of this path MUST NOT add any `UmlCommand` variant or dispatch branch.
(Previously: "the `UmlCommand` union and its dispatcher MUST remain
unmodified as a result of this path's existence", which read as a standing
freeze of the union rather than a statement about the layout path; the
`SetGenerationProfile` command is added by an unrelated change.) **[pytest]**

#### Scenario: Layout write persists and broadcasts without a command

- GIVEN an existing document at revision N
- WHEN the layout-write service function is called with a new final
  position for a class
- THEN the resulting `UmlDocument.layout` is persisted and the updated
  document is broadcast to the document's group, with no `UmlCommand`
  submitted

#### Scenario: The layout path adds no command variant

- GIVEN the layout-write service function and its callers
- WHEN they are inspected
- THEN none of them constructs a `UmlCommand`, calls `dispatcher.apply()`,
  or registers a variant or dispatch branch, whichever other commands the
  union contains
