# Domain Manifest Export Delta: Declared Generation Profile Emission

Delta against `openspec/specs/domain-manifest-export/spec.md`. Requirements not listed here (Manifest Derivation and Purity, Manifest Envelope and Schema Version, CRUD Operations, Enums, Deterministic Ordering and Serialization, Endpoint Drift Guard, CLI Contract, App Registration and Decoupling) are unchanged. Profile vocabulary, value objects and parse rules are specified in `generation-profile`; carry-through into `Column.profile` / `Table.profile` is specified in `relational-mapping`. Design decisions: DD142-DD150 (`design.md`).

Verification key: **[pytest]** = automated in the default suite (Docker-free, offline); **[manual]** = verified by a recorded gate run.

## RENAMED Requirements

### Requirement: Declared-Facts-Only Exclusion → Declared-Facts-Only Emission
(Reason: the requirement no longer excludes the section 33 profile facts; it now emits the declared ones and forbids only `aliases`, `entity` and `generation_metadata`.)

## MODIFIED Requirements

### Requirement: Entity Content

Each `entities[]` item MUST contain `name` (Pascal case), `table`, `resourcePath` (`/api/<segment>`), `operations[]`, `attributes[]`, `relationships[]` and `uniqueConstraints`, plus subtype information for inheritance hierarchies (subtypes listed on the root, parent reference on subclasses). Each `attributes[]` item MUST contain `name` (camelCase), `column`, `type`, `required` (true when the column is not nullable), `maxLength` (the declared VARCHAR length, otherwise null), `enum` (enum name or null) and `primaryKey`. Each `relationships[]` item MUST contain `field`, `kind`, `target` and `required`. Every value MUST reflect what the model declares or the generator emits today.

In addition, an `entities[]` item MAY contain an optional `profile` object and an `attributes[]` item MAY contain an optional `profile` object, each present only when the corresponding `Table.profile` / `Column.profile` declares at least one emittable key (see *Declared-Facts-Only Emission*). The pre-existing keys keep their fixed-key rule (an absent `maxLength` or `enum` is still emitted as `null`); the `profile` objects are an additive exception whose undeclared keys are omitted, never `null`. When present, the entity `profile` MUST be the last key added to the entity and the attribute `profile` the last key added to the attribute (serialized order remains alphabetical through `sort_keys=True`). **[pytest]**

#### Scenario: Sample entity with attributes

- GIVEN the sample model
- WHEN the `Customer` entity is read from the manifest
- THEN it has resource path `/api/customers`, an attribute `fullName` with its column, type, `required` and `maxLength`, and exactly one attribute with `primaryKey` true

#### Scenario: Many-to-one and N:M relationships

- GIVEN the sample model with a many-to-one and an N:M join table
- WHEN the manifest is built
- THEN the many-to-one appears in `relationships[]` with `field`, `kind`, `target` and `required`, and the join table appears as its own entity

#### Scenario: Hierarchy subtypes

- GIVEN the sample Single Table hierarchy
- WHEN the manifest is built
- THEN the single root entity lists its subtypes (name and discriminator value) and the attributes owned by a subclass carry that subclass name in `subtype` (subclasses share the root table, so they are not separate entities; DD125)

#### Scenario: Sample entities and attributes carry no profile key

- GIVEN the sample model, whose tables and columns declare no profile
- WHEN every `entities[]` item and every `attributes[]` item is inspected
- THEN `set(entity) == ENTITY_KEYS` for all six sample tables (`test_manifest.py::test_sample_entity_header`), each sample attribute equals its expected full dict with no `profile` key (`test_attributes.py::test_sample_attribute`), and no `profile` key exists at any depth **[pytest]**

#### Scenario: Attribute profile appears alongside the fixed keys

- GIVEN a column `total` whose `profile` is `ColumnProfile(searchable=True, sortable=True, read_only=False)`
- WHEN its `attributes[]` item is built
- THEN it contains the existing keys unchanged plus `"profile": {"readOnly": false, "searchable": true, "sortable": true}` and no other new key **[pytest]**

### Requirement: Declared-Facts-Only Emission

The manifest MUST emit a section 33 generation-profile fact if, and only if, the model declares it, and MUST NOT fabricate any undeclared fact. Emission is limited to the following keys, all inside a `profile` object:

- Entity-level `entities[].profile` (from `Table.profile`): `auditable` (boolean), `readOnly` (boolean), `crud` (array of lowercase strings) and `defaultSort` (`{attribute, direction}`).
- Attribute-level `attributes[].profile` (from `Column.profile`): `searchable` (boolean), `sortable` (boolean) and `readOnly` (boolean).

Boolean values MUST be passed through untouched (a declared `false` is emitted as `false`, never dropped). The manifest MUST NEVER emit `aliases` (not modelled, DD138), `entity` (semantics deferred, DD139) or `generation_metadata`, at any level, even when the table profile declares `entity`. The guard list `EXCLUDED_KEYS` in `tests/test_manifest.py` MUST be narrowed to exactly `["aliases", "entity", "generation_metadata"]` (DD148); the five newly legal keys are covered by positive emission tests instead of an absence test. The builder MUST shape profiles through the pure module `builder/profile.py` (`build_column_profile`, `build_table_profile`), which MUST read the profile object duck-typed with `getattr(profile, "<snake_name>", None)` and MUST NOT import `apps.relational_mapping` (DD142). Documentation MUST record the supersession of DD131 and the deferred items (`entity`, `aliases`, `crud` filtering of `operations[]`). **[pytest]** for emission and exclusion; **[manual]** for the documentation note.

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

## ADDED Requirements

### Requirement: Default Sort Attribute Resolution

`defaultSort.attribute` MUST be the manifest attribute name of the column whose `source_element_id` equals the declared `attribute_id`, resolved in `entities.py` over the entity's own table columns and computed through the single shared `attributes.attribute_name(column)` (`camel_case(column.name)`), so that it equals the emitted `attributes[].name` by construction (DD144). The discriminator column MUST be excluded from the search, because the attributes builder does not emit it. In a Single Table hierarchy, an `attribute_id` belonging to a subclass-owned attribute MUST resolve on the root entity. When the id matches no column, matches a synthetic column (`id`, `class_type`, foreign keys, all with `source_element_id is None`) or belongs to another table, the builder MUST raise `ManifestError` with exactly the message `table '<table.name>' declares defaultSort on unknown attribute id '<attribute_id>'` (built with `!r` on both values, e.g. `table 'vehicle' declares defaultSort on unknown attribute id 'attr-x'`) during `build_entity`, so `build_manifest` fails before returning a partial document. The resolver MUST be invoked only when `default_sort` is declared. **[pytest]**

#### Scenario: defaultSort resolves to the emitted attribute name

- GIVEN a table with a column `full_name` (`source_element_id="a-1"`) and `defaultSort` declared on `"a-1"`
- WHEN the entity is built
- THEN `defaultSort.attribute == "fullName"` (not `full_name`) and it is a member of the entity's own `[a["name"] for a in attributes]`

#### Scenario: Subtype-owned attribute resolves on the root entity

- GIVEN a Single Table root table whose column is owned by a subclass (`owning_class_id` is the subclass) and whose `defaultSort.attribute_id` is that column's `source_element_id`
- WHEN the root entity is built
- THEN `defaultSort.attribute` equals that column's camelCase name and equals the `name` of an emitted attribute whose `subtype` is the subclass name

#### Scenario: Unknown attribute id raises the exact error

- GIVEN a table `vehicle` with `defaultSort.attribute_id == "attr-x"` matching no column
- WHEN `build_entity` (and `build_manifest`) runs
- THEN `ManifestError("table 'vehicle' declares defaultSort on unknown attribute id 'attr-x'")` is raised, the message equals that string exactly, and no partial manifest is returned

#### Scenario: Synthetic and foreign ids are unknown

- GIVEN a `defaultSort.attribute_id` that matches only a synthetic column (`source_element_id is None`: `id`, the `class_type` discriminator or a foreign key), or that belongs to a column of another table
- WHEN the entity is built
- THEN `ManifestError` is raised with the same message format, naming this table and that id (never returning a name absent from `attributes[]`)

#### Scenario: Resolver not called without a declared default sort

- GIVEN a table profile that declares no `default_sort`
- WHEN `build_table_profile` runs with a `resolve_attribute` spy
- THEN the spy is never called and no `defaultSort` key is emitted

### Requirement: ManifestError Location and Re-export

`ManifestError` MUST be defined in `builder/errors.py` as `ManifestError(ValueError)` (DD143), imported by `manifest.py` (`from .errors import ManifestError`) and by `entities.py`, and MUST remain importable as `from apps.domain_manifest.builder import ManifestError`, with `builder/__init__.py` unchanged. **[pytest]**

#### Scenario: Re-export keeps existing imports working

- GIVEN `tests/test_manifest.py` and the CLI, which import `ManifestError` from `apps.domain_manifest.builder`
- WHEN they run
- THEN the import succeeds and the class is the same object as `apps.domain_manifest.builder.errors.ManifestError`, a subclass of `ValueError`

### Requirement: Profile Builder Decoupling

The new builder modules `builder/profile.py` and `builder/errors.py` MUST comply with *App Registration and Decoupling*: no Django import and no `apps.*` import other than `apps.spring_generator.emit.naming`. In particular, `profile.py` MUST NOT import `ColumnProfile`, `TableProfile` or any other `apps.relational_mapping` name, and MUST read enum members through `getattr(value, "value", value)` (DD146). The existing guard test `tests/test_builder_decoupling.py` MUST pass unchanged, because it globs `builder/**` and therefore scans both new files automatically. **[pytest]**

#### Scenario: Decoupling guard still passes

- GIVEN `builder/profile.py` and `builder/errors.py` added to the app
- WHEN `tests/test_builder_decoupling.py` runs with no edits
- THEN it passes, the only cross-app import found in `builder/**` remains `spring_generator.emit.naming`, and both new files were included in the scan

### Requirement: CRUD Declaration Does Not Filter Operations

The declared `crud` list is documentation of authoring intent only. It MUST NOT filter, reorder or otherwise alter `operations[]`, which continues to describe exactly the endpoints the generated controller serves (DD147, recorded as tech debt in `docs/ai/DECISIONS_LOG.md`). **[pytest]**

#### Scenario: Declaring crud keeps the six operations

- GIVEN a table with a controller whose profile declares `crud: ["read"]`
- WHEN the entity is built
- THEN `operations[]` still contains exactly the six ordered operations of *CRUD Operations* and `entity["profile"]["crud"] == ["read"]`

### Requirement: Profile Emission Determinism and Sample Neutrality

Profile emission MUST introduce no unordered or volatile output: the key tuples are literals, `crud` preserves the mapper's canonical order, the resolver returns the first match scanning `table.columns` in order, and every emitted value is a `bool`, `str`, `list[str]` or a two-key dict. Two builds and serializations of the same profile-carrying model MUST be byte-identical. The sample UML model declares no profile, so `docs/domain-manifest.json` and the gate output MUST remain byte-identical to their pre-change form without a gate run, no new golden, and no change to `docker-compose.yml` or `scripts/verify-generated-project.sh` (DD150). A model whose `generation_metadata` is `{}` MUST produce the same manifest as one with no metadata, while a profile-carrying model MUST produce a different manifest that contains a `profile` key (DD149). **[pytest]**

#### Scenario: Two runs equal bytes with a profile

- GIVEN a model whose tables and columns declare profiles (including `crud` and `defaultSort`)
- WHEN the manifest is built and serialized twice
- THEN both outputs are byte-identical, contain no timestamp or id-like volatile key (the key `id` never appears at any depth, which is why `defaultSort` uses `attribute`, not `attributeId`), and `tests/test_determinism.py` passes unchanged

#### Scenario: Sample-model manifest unchanged

- GIVEN the sample model
- WHEN the manifest is built after this change
- THEN it is byte-identical to the pre-change output, pinned by the existing tripwire tests `tests/test_manifest.py::test_sample_entity_header` (`set(entity) == ENTITY_KEYS` for all six sample tables), `tests/test_attributes.py::test_sample_attribute` (full-dict equality per sample attribute) and `tests/test_determinism.py`, none of whose expected values are edited

#### Scenario: Profile-carrying model changes the manifest, empty metadata does not

- GIVEN (a) the sample model, (b) the same model with every `generation_metadata` equal to `{}`, and (c) a model with a declared table profile (`test_profile_output_neutral.py`, retargeted)
- WHEN the manifests of (a), (b) and (c) are compared
- THEN manifest (a) equals manifest (b), and manifest (c) is not equal to (a) and contains a `profile` key **[pytest]**

#### Scenario: Regression suites untouched

- GIVEN `tests/test_cli.py`, `generation_runner/tests/test_sample_model.py`, `relational_mapping` tests and the `spring_generator` goldens
- WHEN `pytest -q` runs
- THEN they pass with zero edits to expected values **[pytest]**

#### Scenario: Decision log records supersession and debt

- GIVEN the change is complete
- WHEN `docs/ai/DECISIONS_LOG.md` is read
- THEN it records DD142-DD150, the supersession of DD131, and the DD147 tech-debt entry (`crud` does not filter `operations[]`) **[manual]**
