# Domain Manifest Export Delta: CRUD Declaration Restricts Operations

Delta against `openspec/specs/domain-manifest-export/spec.md`. Requirements not listed here (Manifest Derivation and Purity, Manifest Envelope and Schema Version, Entity Content, Enums, Deterministic Ordering and Serialization, Endpoint Drift Guard, CLI Contract, App Registration and Decoupling, Default Sort Attribute Resolution, ManifestError Location and Re-export, Profile Builder Decoupling, Profile Emission Determinism and Sample Neutrality) are unchanged and remain true: the sample model declares no profile, so its output is byte-identical (DD164, DD165). The effective operation set is specified in `generation-profile` (*Effective Operations Derivation*); this delta specifies how the manifest consumes it. Design decisions: DD160-DD167 (`design.md`).

Verification key: **[pytest]** = automated in the default suite (Docker-free, offline); **[manual]** = verified by a recorded gate run.

## RENAMED Requirements

### Requirement: CRUD Declaration Does Not Filter Operations → CRUD Declaration Restricts Operations
(Reason: DD147 is retired — the declared crud now restricts operations[]; the old heading asserts the opposite of the shipped behaviour.)

## MODIFIED Requirements

### Requirement: CRUD Operations

For every entity that has a generated controller, `operations[]` MUST contain exactly the entity's **effective operations** (see `generation-profile` *Effective Operations Derivation*), in this canonical order, each with `name`, `method`, `path` and `successStatus` (DD125): `create` POST (201) `/api/<segment>`; `findById` GET `/api/<segment>/{id}`; `update` PUT `/api/<segment>/{id}`; `delete` DELETE `/api/<segment>/{id}`; `list` GET `/api/<segment>`; `count` GET `/api/<segment>/count`. When the profile is undeclared (`Table.profile is None`, `TableProfile()`, or no `crud` and no `readOnly: true`), the effective operations are all six rows above and `operations[]` contains exactly those six items in that order. The row attributes (`method`, path suffix, `successStatus`) come from the single `_OPERATIONS` table and are never altered by filtering; only membership is filtered and order is never changed.

An entity has no generated controller when it is an inheritance root or subclass (DD126) or when its effective operation set is empty (DD163). For such an entity `operations[]` MUST be empty and `resourcePath` MUST be `null`. Stated once, here, as the single owner of the coupling: **`resourcePath` is `null` if and only if `operations[]` is empty.** The resource path segment MUST still be computed and validated (through `resource_path_segment`, whose `InvalidResourcePathError` surfaces as `ManifestError`) for every non-inheritance table before the empty-set suppression, so segment validation is unchanged and only emission is suppressed; inheritance tables keep their existing short-circuit and are not newly validated. **[pytest]**

#### Scenario: Six ordered operations

- GIVEN the `Customer` entity of the sample model, which declares no profile
- WHEN its `operations[]` is read
- THEN it has the six operations above, in that order, with the stated methods and paths

#### Scenario: Undeclared profile keeps the six operations

- GIVEN tables whose profile is `None`, `TableProfile()` and `TableProfile(auditable=True)`
- WHEN each entity is built
- THEN each `operations[]` has exactly the six ordered rows (`create`, `findById`, `update`, `delete`, `list`, `count`) with `resourcePath == "/api/<segment>"` **[pytest]**

#### Scenario: Restricted entity lists only its effective operations

- GIVEN a non-inheritance table `purchase` whose profile declares `crud=(CrudOperation.CREATE, CrudOperation.READ)`
- WHEN the entity is built
- THEN `operations[]` names are exactly `["create", "findById", "list", "count"]` in that order, each row equals its literal counterpart (for example `create` is POST `/api/purchases` with `successStatus` 201 and `count` is GET `/api/purchases/count`), and `resourcePath == "/api/purchases"` **[pytest]**

#### Scenario: Each crud subset yields its rows in canonical order

- GIVEN table profiles declaring `crud` equal to `(READ,)`, `(UPDATE,)`, `(DELETE,)` and `(DELETE, CREATE, READ)`
- WHEN each entity is built
- THEN the `operations[]` names are `["findById", "list", "count"]`, `["update"]`, `["delete"]` and `["create", "findById", "delete", "list", "count"]` respectively, never reordered to the declared order **[pytest]**

#### Scenario: Empty effective set drops the controller and the resource path

- GIVEN a table declaring `crud=()`, and separately a table declaring `read_only=True` with `crud=(CrudOperation.CREATE,)`
- WHEN each entity is built
- THEN `operations == []` and `resourcePath is None` for both (the same shape as an inheritance entity: entity and repository only), and neither raises **[pytest]**

#### Scenario: readOnly true keeps only the read operations

- GIVEN table profiles declaring `read_only=True` with `crud=None`, with `crud=(CREATE, READ)` and with `crud=(CREATE,)`
- WHEN each entity is built
- THEN the first two have `operations[]` names `["findById", "list", "count"]` with paths `/api/purchases/{id}`, `/api/purchases` and `/api/purchases/count`, and `resourcePath == "/api/purchases"`, and the third has `operations == []` and `resourcePath is None` **[pytest]**

#### Scenario: readOnly false or None lets crud decide

- GIVEN a table declaring `crud=(CREATE, UPDATE)` with `read_only=False`, and the same with `read_only=None`
- WHEN each entity is built
- THEN both have `operations[]` names `["create", "update"]` and `resourcePath == "/api/<segment>"` **[pytest]**

#### Scenario: resourcePath is null if and only if operations is empty

- GIVEN every entity of the sample manifest plus the restricted, empty-set and read-only entities of the scenarios above
- WHEN each entity's `operations` and `resourcePath` are read
- THEN for every entity `(entity["resourcePath"] is None) == (entity["operations"] == [])` **[pytest]**

#### Scenario: Resource path is validated before empty-set suppression

- GIVEN a non-inheritance table whose name makes `resource_path_segment` raise `InvalidResourcePathError`, once with an empty effective set (`crud=()`) and once with a non-empty one
- WHEN `build_entity` (and `build_manifest`) runs
- THEN both raise `ManifestError` exactly as before this change, because the segment is computed before the suppression, and an inheritance table with an empty effective set is not newly validated **[pytest]**

#### Scenario: Inheritance entities have no operations

- GIVEN the inheritance root entity of the sample hierarchy (subclasses share its table and are not separate entities, DD125/DD126)
- WHEN its `operations[]` and `resourcePath` are read
- THEN `operations[]` is an empty list and `resourcePath` is `null`

### Requirement: CRUD Declaration Restricts Operations

The declared `crud` list and `readOnly: true` MUST restrict `operations[]`: the manifest MUST build `operations[]` from `effective_operations` (read as `table.effective_operations`, a property of the mapped `Table` that the builder duck-types without importing `apps.relational_mapping`, DD162) and MUST NOT reorder the surviving rows (order comes from the fixed `_OPERATIONS` table, never from the declared `crud`). `crud` and `readOnly` MUST still be emitted verbatim under `entity["profile"]` (`build_table_profile` is untouched), so authoring intent stays visible next to its effect. DD147 (declared `crud` does not filter `operations[]`) is retired for the manifest by DD160-DD163 and DD167; its entry in `docs/ai/DECISIONS_LOG.md` MUST be annotated as retired in place and never deleted. The sample model declares no profile, so its manifest, `docs/domain-manifest.json` and the unedited tripwire tests are unchanged. **[pytest]** for behaviour; **[manual]** for the log annotation.

#### Scenario: Declaring crud restricts the operations

- GIVEN a table with a controller whose profile declares `crud: ["read"]`
- WHEN the entity is built
- THEN `operations[]` names are exactly `["findById", "list", "count"]` and `entity["profile"]["crud"] == ["read"]` **[pytest]**

#### Scenario: Declared crud and readOnly are still emitted verbatim

- GIVEN a table whose profile declares `crud=()` and `read_only=True`
- WHEN the entity is built
- THEN `operations == []`, `resourcePath is None`, and `entity["profile"] == {"crud": [], "readOnly": True}` (the declared facts are emitted, not dropped, even though they suppress the controller) **[pytest]**

#### Scenario: Restriction is derived from the shared function, not re-implemented

- GIVEN the manifest builder
- WHEN the source of `builder/entities.py` is inspected and the manifest of a restricted model is compared with `table.effective_operations`
- THEN `operations[]` names equal `table.effective_operations` filtered through `_OPERATIONS` order, the builder reads the property without any `apps.relational_mapping` import, and `tuple(name for name, *_ in _OPERATIONS) == OPERATION_NAMES` **[pytest]**

#### Scenario: Sample-model output is byte-identical

- GIVEN the sample model, which declares no profile
- WHEN the manifest is built after this change
- THEN it is byte-identical to the pre-change output, pinned by the unedited `test_manifest.py::test_sample_entity_header`, `test_manifest.py::test_operations_exist_exactly_when_the_entity_has_a_controller`, `test_attributes.py::test_sample_attribute`, `test_determinism.py`, `test_cli.py` and the committed `docs/domain-manifest.json` **[pytest]**

#### Scenario: Decoupling guard is unchanged

- GIVEN `entities.py` now reading `table.effective_operations`
- WHEN `tests/test_builder_decoupling.py` runs with zero edits
- THEN it passes, the only cross-app import found in `builder/**` remains `spring_generator.emit.naming`, and `cli.py` still imports only `apps.domain_manifest` and `apps.generation_runner.samples.sample_model` **[pytest]**

#### Scenario: DD147 log entry is annotated as retired, not deleted

- GIVEN the change is complete
- WHEN `docs/ai/DECISIONS_LOG.md` is read
- THEN the original DD147 text is still present with an annotation "retired by DD167 (manifest) / slice 2 (generator)", DD160-DD167 are recorded, and the transient manifest/generator divergence between slice 1 and slice 2 is recorded **[manual]**

### Requirement: Declared-Facts-Only Emission

The manifest MUST emit a section 33 generation-profile fact if, and only if, the model declares it, and MUST NOT fabricate any undeclared fact. Emission is limited to the following keys, all inside a `profile` object:

- Entity-level `entities[].profile` (from `Table.profile`): `auditable` (boolean), `readOnly` (boolean), `crud` (array of lowercase strings) and `defaultSort` (`{attribute, direction}`).
- Attribute-level `attributes[].profile` (from `Column.profile`): `searchable` (boolean), `sortable` (boolean) and `readOnly` (boolean).

Boolean values MUST be passed through untouched (a declared `false` is emitted as `false`, never dropped). The manifest MUST NEVER emit `aliases` (not modelled, DD138), `entity` (semantics deferred, DD139) or `generation_metadata`, at any level, even when the table profile declares `entity`. The guard list `EXCLUDED_KEYS` in `tests/test_manifest.py` MUST be narrowed to exactly `["aliases", "entity", "generation_metadata"]` (DD148); the five newly legal keys are covered by positive emission tests instead of an absence test. The builder MUST shape profiles through the pure module `builder/profile.py` (`build_column_profile`, `build_table_profile`), which MUST read the profile object duck-typed with `getattr(profile, "<snake_name>", None)` and MUST NOT import `apps.relational_mapping` (DD142). Documentation MUST record the supersession of DD131 and the deferred items (`entity`, `aliases`). **[pytest]** for emission and exclusion; **[manual]** for the documentation note.

#### Scenario: Never-emitted keys absent

- GIVEN the sample manifest
- WHEN it is scanned recursively
- THEN none of `aliases`, `entity` and `generation_metadata` appears at any depth, and `EXCLUDED_KEYS == ["aliases", "entity", "generation_metadata"]`

#### Scenario: Entity flag not emitted even when declared

- GIVEN a table whose profile is `TableProfile(auditable=True, entity=True)`
- WHEN the manifest is built
- THEN the entity `profile` is `{"auditable": true}` and the key `entity` appears nowhere in the manifest

#### Scenario: Each entity-level key is emitted when declared

- GIVEN a table with profile `TableProfile(auditable=True, read_only=False, crud=(CrudOperation.CREATE, CrudOperation.READ), default_sort=DefaultSort(attribute_id="<id of total>", direction=SortDirection.DESC))`
- WHEN the entity is built
- THEN `entity["profile"] == {"auditable": True, "readOnly": False, "crud": ["create", "read"], "defaultSort": {"attribute": "total", "direction": "desc"}}` **[pytest]**

#### Scenario: Each attribute-level key is emitted when declared

- GIVEN three columns whose profiles declare only `searchable`, only `sortable` and only `read_only` respectively (one case each), plus one column declaring all three
- WHEN their attributes are built
- THEN each `profile` contains exactly the declared key(s) mapped to `searchable`, `sortable` and `readOnly` (snake_case `read_only` becomes camelCase `readOnly`), with the declared boolean values **[pytest]**

#### Scenario: Declared false is still emitted

- GIVEN a column with `ColumnProfile(searchable=False)` and a table with `TableProfile(read_only=False)`
- WHEN the profiles are built
- THEN the column profile is `{"searchable": false}` and the table profile is `{"readOnly": false}` (the omission test is `is not None`, not truthiness) **[pytest]**

#### Scenario: Undeclared keys are omitted, never null

- GIVEN a table profile declaring only `auditable=True` and a column profile declaring only `sortable=True`
- WHEN the profiles are built
- THEN the entity profile is `{"auditable": true}` and the attribute profile is `{"sortable": true}`; no key with a `null` value appears in either **[pytest]**

#### Scenario: Empty or absent profile emits no profile key

- GIVEN a `Table.profile` that is `None`, a profile object whose emittable fields are all `None`, and a `SimpleNamespace` object with no profile fields at all (same three cases for `Column.profile`)
- WHEN the entity and attribute are built
- THEN `build_table_profile` and `build_column_profile` return `None`, no `profile` key is present (not `{}`), and no `AttributeError` is raised **[pytest]**

#### Scenario: crud is an ordered list of plain strings

- GIVEN a table profile whose `crud` is the canonical tuple `(CrudOperation.CREATE, CrudOperation.READ)`
- WHEN the entity profile is built
- THEN `crud == ["create", "read"]`, it is a `list` (not a `tuple` or `set`), it keeps the mapper's canonical order without re-sorting, and every item satisfies `type(item) is str` **[pytest]**

#### Scenario: defaultSort direction is a plain lowercase string

- GIVEN table profiles declaring `default_sort` with `SortDirection.ASC` and with `SortDirection.DESC`
- WHEN the entity profile is built
- THEN `defaultSort["direction"]` is exactly `"asc"` and exactly `"desc"` respectively, `type(direction) is str`, and `defaultSort` has exactly the two keys `attribute` and `direction` (never `attributeId`) **[pytest]**

#### Scenario: Serialization is alphabetical regardless of insertion order

- GIVEN an entity with a declared table profile
- WHEN the manifest is serialized with `write_json`
- THEN the `profile` keys appear in alphabetical order (`auditable`, `crud`, `defaultSort`, `readOnly`) and re-serializing the parsed content reproduces the bytes **[pytest]**

#### Scenario: Schema version unchanged

- GIVEN a manifest built from a model that declares profiles
- WHEN its top-level keys are inspected
- THEN `schemaVersion == 1`, and `entities` and `enums` are lists **[pytest]**
