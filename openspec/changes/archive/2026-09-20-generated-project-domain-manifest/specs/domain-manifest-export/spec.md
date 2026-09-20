# Domain Manifest Export Specification

## Purpose

Defines the Domain Manifest (spec section 28): a pure, deterministic JSON document derived from the `RelationalModel` (the same model the Spring generator consumes) that declares entities, attributes, relationships, enums and the CRUD operations actually generated. Lives in the Django app `apps.domain_manifest`, driven by a plain CLI. springdoc remains the sole OpenAPI producer; the manifest is not the API contract. Out of scope: section 33 `generation_metadata`, aliases, filtering/search API, frontend/mobile generation, assistant/AssistantCommand, auth, embedding the manifest in the Spring source tree, deriving it from OpenAPI, real-project CLI input.

Verification key: **[pytest]** = automated in the default suite (Docker-free, offline); **[manual]** = verified by a recorded gate run.

## Requirements

### Requirement: Manifest Derivation and Purity

The builder MUST be a pure function of a `RelationalModel` (model in, `dict` out). It MUST NOT import Django, models or migrations, MUST NOT read the clock, environment or filesystem, and MUST NOT emit timestamps or generated ids. Names, table names, columns and resource paths MUST come from `spring_generator.emit.naming`, so they cannot drift from the generator. **[pytest]**

#### Scenario: Same model, equal output

- GIVEN the sample model built twice
- WHEN the builder runs on each
- THEN both results are equal and contain no timestamp or id-like volatile key

#### Scenario: Names follow the generator

- GIVEN a table and column in the sample model
- WHEN the builder emits them
- THEN the entity name equals `pascal_case(table.name)`, the attribute name equals `camel_case(column.name)` and the resource path equals `/api/` + `resource_path_segment(table.name)`

### Requirement: Manifest Envelope and Schema Version

The top-level document MUST contain `schemaVersion` equal to integer `1`, `entities` and `enums`. The schema MUST evolve additively only: a later change MAY add keys but MUST NOT rename, remove or retype an existing key without a new `schemaVersion`. **[pytest]**

#### Scenario: Version and top-level keys

- GIVEN the sample manifest
- WHEN its top-level keys are inspected
- THEN `schemaVersion == 1` and `entities` and `enums` are lists

### Requirement: Entity Content

Each `entities[]` item MUST contain `name` (Pascal case), `table`, `resourcePath` (`/api/<segment>`), `operations[]`, `attributes[]`, `relationships[]` and `uniqueConstraints`, plus subtype information for inheritance hierarchies (subtypes listed on the root, parent reference on subclasses). Each `attributes[]` item MUST contain `name` (camelCase), `column`, `type`, `required` (true when the column is not nullable), `maxLength` (the declared VARCHAR length, otherwise null), `enum` (enum name or null) and `primaryKey`. Each `relationships[]` item MUST contain `field`, `kind`, `target` and `required`. Every value MUST reflect what the model declares or the generator emits today. **[pytest]**

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

### Requirement: CRUD Operations

For every entity that has a generated controller, `operations[]` MUST contain exactly these six items in this order, each with `name`, `method`, `path` and `successStatus` (DD125): `create` POST (201) `/api/<segment>`; `findById` GET `/api/<segment>/{id}`; `update` PUT `/api/<segment>/{id}`; `delete` DELETE `/api/<segment>/{id}`; `list` GET `/api/<segment>`; `count` GET `/api/<segment>/count`. For inheritance roots and subclasses, for which no controller is generated, `operations[]` MUST be empty. **[pytest]**

#### Scenario: Six ordered operations

- GIVEN the `Customer` entity of the sample model
- WHEN its `operations[]` is read
- THEN it has the six operations above, in that order, with the stated methods and paths

#### Scenario: Inheritance entities have no operations

- GIVEN the inheritance root entity of the sample hierarchy (subclasses share its table and are not separate entities, DD125/DD126)
- WHEN its `operations[]` and `resourcePath` are read
- THEN `operations[]` is an empty list and `resourcePath` is `null`

### Requirement: Enums

`enums[]` MUST list every enum type of the model as `{name, values}` where each value is `{value, label}` (`value` is the wire constant, `label` the model label; DD125), preserving the model's value order. **[pytest]**

#### Scenario: Sample enum

- GIVEN the sample model with one enum
- WHEN the manifest is built
- THEN `enums[]` contains that enum with its ordered values, and the attribute using it references it by name in `enum`

### Requirement: Declared-Facts-Only Exclusion

The manifest MUST NOT emit `searchable`, `sortable`, `defaultSort`, `auditable`, `readOnly` or `aliases`, at any level. The relational mapper does not carry section 33 `generation_metadata`, so these facts do not exist and MUST NOT be fabricated. Documentation MUST record the UML versus own-profile split that section 33 requires and the follow-up needed to add this metadata (mapper carrying `generation_metadata`). **[pytest]** for absence; **[manual]** for the documentation note.

#### Scenario: Excluded keys absent

- GIVEN the sample manifest
- WHEN it is scanned recursively
- THEN none of the six excluded keys appears at any depth

### Requirement: Deterministic Ordering and Serialization

Entities MUST be ordered by entity name (DD125), attributes by column order in the model, operations in the fixed order above, enums by name. The file MUST be produced by `json.dumps` with `indent=2`, `sort_keys=True`, `ensure_ascii=False`, followed by one trailing newline, and written with `newline="\n"`. Two runs MUST yield byte-identical files. **[pytest]**

#### Scenario: Byte-identical runs

- GIVEN the sample model
- WHEN the manifest is serialized and written twice
- THEN both files are byte-identical

#### Scenario: Serialization format

- GIVEN a written manifest file
- WHEN its bytes are inspected
- THEN it is UTF-8, contains no `\r`, ends with exactly one `\n`, and re-serializing the parsed content with the same options reproduces the bytes

### Requirement: Endpoint Drift Guard

A Docker-free test MUST assert that the set of resource paths and operation paths derived from the sample model equals the set of API paths in the committed fixture `backend/apps/postman_export/tests/fixtures/api-docs.json`, which the test MUST use read-only. **[pytest]**

#### Scenario: Paths match springdoc fixture

- GIVEN the sample manifest and the committed springdoc fixture
- WHEN both path sets are compared
- THEN they are equal

#### Scenario: Drift caught

- GIVEN a generator or manifest change that renames a resource path
- WHEN `pytest -q` runs offline
- THEN the drift-guard test fails

### Requirement: CLI Contract

`python -m apps.domain_manifest.cli --out-dir <dir>` MUST create `<dir>` if missing and write the fixed file name `domain-manifest.json` there, from the sample model only, without calling `django.setup()` and without requiring `POSTGRES_*` variables. It MUST exit 0 on success, 1 with a message on stderr when writing fails, and 2 on invalid arguments (argparse). No other output file name MUST be written. **[pytest]** via subprocess; **[manual]** inside the container.

#### Scenario: Success

- GIVEN a non-existent output directory
- WHEN the CLI runs with `--out-dir`
- THEN the exit code is 0 and `domain-manifest.json` exists in that directory

#### Scenario: Write failure

- GIVEN `--out-dir` pointing at an existing regular file
- WHEN the CLI runs
- THEN the exit code is 1 and stderr carries a message

#### Scenario: Missing argument

- GIVEN no `--out-dir`
- WHEN the CLI runs
- THEN the exit code is 2

#### Scenario: No Django bootstrap

- GIVEN the CLI module is run
- WHEN it completes
- THEN `django.setup` was never called

### Requirement: App Registration and Decoupling

`apps.domain_manifest` MUST be registered in `INSTALLED_APPS` immediately after `apps.postman_export`, with no models and no migrations. Its modules MUST NOT import Django or `apps.*` other than `spring_generator.emit.naming`; the CLI glue MAY additionally import `generation_runner.samples.sample_model`. No other app MAY import `domain_manifest`. springdoc MUST remain the only OpenAPI producer. **[pytest]**

#### Scenario: Import guard

- GIVEN every module in `apps.domain_manifest`
- WHEN a guard test scans their imports
- THEN the only cross-app imports are `spring_generator.emit.naming` and, in the CLI glue, `generation_runner.samples.sample_model`, and no Django import exists outside `apps.py`

#### Scenario: Nothing imports the manifest app

- GIVEN every module of every other app
- WHEN a guard test scans their imports
- THEN none imports `apps.domain_manifest`

#### Scenario: Registration

- GIVEN the Django settings
- WHEN `INSTALLED_APPS` is read
- THEN `apps.domain_manifest` follows `apps.postman_export` and the app has no models or migrations
