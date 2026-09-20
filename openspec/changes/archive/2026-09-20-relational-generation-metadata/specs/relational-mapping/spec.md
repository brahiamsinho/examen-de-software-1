# Relational Mapping Delta: Generation Profile Carry-Through

Delta against `openspec/specs/relational-mapping/spec.md`. Requirements not listed here are unchanged. Profile vocabulary, value objects and parse rules are specified in `generation-profile`.

Verification key: **[pytest]** = automated in the default suite (Docker-free, offline); **[manual]** = verified by a recorded gate run.

## MODIFIED Requirements

### Requirement: RelationalModel Domain Structure

The system MUST provide frozen, DB-free, framework-agnostic dataclasses: `Table`, `Column`, `PrimaryKey`, `ForeignKey`, `UniqueConstraint`, `Index`, `EnumType`, and `RelationalModel` (aggregating `tables` and `enum_types`). `Column` MUST expose an optional `profile: ColumnProfile | None` and `Table` MUST expose an optional `profile: TableProfile | None`, each appended as the last field and defaulting to `None` (undeclared), so that every existing construction site remains valid and structural equality remains intact (`Column` stays hashable; `Table` and `RelationalModel` were already unhashable because `discriminator_values` is a `MappingProxyType`, and that is unchanged). These MUST NOT import Django, any DB driver, or Java/Spring Boot code. **[pytest]**

#### Scenario: Domain module has zero framework imports
- GIVEN the `relational_mapping` domain module source
- WHEN its imports are inspected
- THEN no `django`, DB driver, or Java/Spring code is imported

#### Scenario: Profile fields default to None
- GIVEN a `Column` and a `Table` built without a `profile` argument
- WHEN `profile` is read
- THEN it is `None` on both (asserted in `test_column_defaults` and `test_table_defaults`)

#### Scenario: Profile-carrying values remain hashable
- GIVEN a `Column(..., profile=ColumnProfile(searchable=True))` and a `Table(..., profile=TableProfile(auditable=True))`
- WHEN each is compared with an equal separately built value, and the `Column` and the `Table.profile` are hashed
- THEN the `Column` and `Table.profile` hash successfully with equal hashes, and the `Table` values are `==` (a `Table` itself is not hashable)

### Requirement: Class-to-Table Mapping

Each `UmlClass` MUST map to exactly one `Table` named after the class, except a subclass in a Single Table hierarchy (see below), which contributes columns to its root ancestor's table instead of a new table. When the class (or, for a Single Table hierarchy, its root class) has a valid `"profile"` declared in `generation_metadata`, the resulting `Table.profile` MUST be the parsed `TableProfile`; otherwise `Table.profile` MUST be `None`. A class-level `"profile"` on a Single Table subclass MUST be validated but MUST NOT become a `Table.profile`. **[pytest]**

#### Scenario: Simple class becomes a table
- GIVEN a `CanonicalUmlModel` with one class `Order` and no generalization
- WHEN `map_to_relational(model)` is called
- THEN the result contains exactly one `Table` named `Order`

#### Scenario: Declared class profile reaches the table
- GIVEN class `Order` with `generation_metadata` `{"profile": {"auditable": True, "crud": ["read"]}}`
- WHEN mapped
- THEN the `Order` table has `profile == TableProfile(auditable=True, crud=(CrudOperation.READ,))` and every other field is `None`

#### Scenario: Undeclared class has no table profile
- GIVEN class `Order` with no `generation_metadata` entry
- WHEN mapped
- THEN `Table.profile is None`

#### Scenario: Single Table hierarchy takes the root class profile only
- GIVEN root `Vehicle` declaring `{"profile": {"auditable": True}}` and subclass `Car` declaring `{"profile": {"readOnly": True}}`
- WHEN mapped
- THEN the single `Vehicle` table has `profile == TableProfile(auditable=True)`, with `read_only is None`

#### Scenario: Subclass-only class profile sets no table profile
- GIVEN root `Vehicle` with no entry and subclass `Car` declaring `{"profile": {"auditable": True}}`
- WHEN mapped
- THEN the `Vehicle` table has `profile is None` and no error is raised

#### Scenario: Malformed subclass class profile still raises
- GIVEN subclass `Car` declaring `{"profile": {"auditable": 1}}`
- WHEN mapped
- THEN `InvalidGenerationProfileError` is raised for the `Car` element id with key `auditable`

### Requirement: Attribute-to-Column Mapping

Each `UmlAttribute` MUST map to one `Column` on its owning table, preserving name and a relational type derived from its `AttributeType` (primitive or `EnumerationRef`). When the attribute has a valid `"profile"` declared in `generation_metadata`, keyed by the attribute's own element id, the resulting `Column.profile` MUST be the parsed `ColumnProfile` for both primitive and enumeration-typed attributes; otherwise `Column.profile` MUST be `None`. **[pytest]**

#### Scenario: Primitive attribute becomes a typed column
- GIVEN a class with attribute `total: DECIMAL`
- WHEN mapped
- THEN the table has a `Column` named `total` with a decimal relational type

#### Scenario: Declared attribute profile reaches the column
- GIVEN attribute `total` with `generation_metadata` `{"profile": {"searchable": True, "sortable": True}}`
- WHEN mapped
- THEN the `total` column has `profile == ColumnProfile(searchable=True, sortable=True)` with `read_only is None`

#### Scenario: Enumeration-typed attribute carries its profile
- GIVEN an attribute typed `EnumerationRef` declaring `{"profile": {"searchable": True}}`
- WHEN mapped
- THEN its enum-referencing column has `profile == ColumnProfile(searchable=True)`

#### Scenario: Undeclared attribute has no column profile
- GIVEN an attribute with no `generation_metadata` entry
- WHEN mapped
- THEN its `Column.profile is None`

#### Scenario: Subclass-owned attribute column keeps its profile
- GIVEN subclass `Car` with attribute `horsepower` declaring `{"profile": {"sortable": True}}`
- WHEN mapped
- THEN the `horsepower` column on the `Vehicle` table has `profile == ColumnProfile(sortable=True)`
- AND its `owning_class_id` still equals the `Car` class id

### Requirement: Deterministic Mapping

`map_to_relational` MUST be a pure function: given the same `CanonicalUmlModel`, it MUST always produce a structurally identical `RelationalModel`, with tables, columns, and constraints in a stable, deterministic order. This MUST hold for models that carry profile metadata: two mappings MUST be equal (with equal hashes for their columns and table profiles), and the first offending profile entry, and therefore the raised message, MUST be stable because entries are parsed in the order of `generation_metadata`. **[pytest]**

#### Scenario: Repeated mapping is identical
- GIVEN a fixed `CanonicalUmlModel`
- WHEN `map_to_relational(model)` is called twice
- THEN both `RelationalModel` results are structurally equal

#### Scenario: Profile-carrying model maps equal and hashes equal
- GIVEN a model whose classes and attributes declare profiles
- WHEN `map_to_relational(model)` is called twice
- THEN both results are `==` and `hash()` of their columns and table profiles are equal (tables and the model are compared by equality only)

## ADDED Requirements

### Requirement: Profiles Are Collected Before Table Work

`map_to_relational` MUST read `generation_metadata` once, up front, before enumeration or table mapping, dispatching each entry by id kind: a class id is parsed with `parse_table_profile`, an attribute id with `parse_column_profile`, any other id is skipped (DD141). A malformed profile entry MUST therefore raise `InvalidGenerationProfileError` before any `Table` is produced, even when the entry belongs to an element that would otherwise be unvisited. **[pytest]**

#### Scenario: Malformed entry aborts mapping
- GIVEN a model with a valid class and an attribute whose profile is `{"searchable": "yes"}`
- WHEN `map_to_relational(model)` is called
- THEN `InvalidGenerationProfileError` is raised naming that attribute element id and key `searchable`, and no `RelationalModel` is returned

#### Scenario: Error is catchable as the mapper failure contract
- GIVEN the same malformed model
- WHEN the call is wrapped in `except UnmappableModelError`
- THEN the exception is caught

#### Scenario: First offending entry wins
- GIVEN two malformed entries in `generation_metadata` order `A` then `B`
- WHEN mapped twice
- THEN both calls raise for `A` with identical messages

#### Scenario: Unknown element ids and keys outside profile never raise
- GIVEN entries for unknown element ids (any value) and for known elements with malformed keys only outside `"profile"`
- WHEN mapped
- THEN mapping succeeds and no profile is attached from them

### Requirement: Synthetic Columns and Join Tables Carry No Profile

Every column not derived from a `UmlAttribute` MUST have `profile` equal to `None`, even when the owning class declares a profile: the synthetic `id` column, the Single Table discriminator `class_type` column, relationship foreign-key columns, and many-to-many join-table columns including the join-table `id`. Join tables MUST have `Table.profile` equal to `None`. **[pytest]**

#### Scenario: Synthetic id and discriminator have no profile
- GIVEN a Single Table hierarchy whose root class declares a full table profile
- WHEN mapped
- THEN the root table's `id` column and `class_type` column both have `profile is None`

#### Scenario: Foreign-key columns have no profile
- GIVEN a one-to-many association whose owning class and attributes declare profiles
- WHEN mapped
- THEN the relationship foreign-key column has `profile is None`

#### Scenario: Join table and its columns have no profile
- GIVEN a many-to-many association between classes that declare profiles
- WHEN mapped
- THEN the join table has `Table.profile is None` and its `id` and both foreign-key columns have `profile is None`

### Requirement: Profile Carry-Through Is Output-Neutral

No consumer reads `profile` in this change. When `generation_metadata` declares no profile, the 41-file Spring oracle and the Domain Manifest output MUST remain byte-identical to before this change, with zero edits to their expected values. `apps.domain_manifest`, `apps.spring_generator` and `apps.uml_modeling.domain.model` MUST remain unchanged. **[pytest]**

#### Scenario: Spring oracle unchanged
- GIVEN the existing sample model with no declared profile
- WHEN `apps/generation_runner/tests/test_sample_model.py` (`EXPECTED_FILE_COUNT = 41`, determinism) and `apps/spring_generator/tests/test_inheritance_backward_compatibility.py` (per-file sha256 goldens) run
- THEN both pass unchanged

#### Scenario: Domain Manifest unchanged
- GIVEN the same model
- WHEN `apps/domain_manifest` tests run, including `test_manifest.py::test_undeclared_facts_are_never_emitted` over `EXCLUDED_KEYS` (which keeps `aliases`) and `test_determinism.py`
- THEN all pass unchanged

#### Scenario: Declared profile does not change manifest or oracle output
- GIVEN a model that declares profiles but is otherwise the sample model
- WHEN the Domain Manifest and the Spring project are generated
- THEN their output is identical to the output for the same model without profiles

## Verification Commands

- `docker compose exec -T backend pytest -q apps/relational_mapping` **[pytest]**
- `docker compose exec -T backend pytest -q apps/generation_runner/tests/test_sample_model.py` **[pytest]**
- `docker compose exec -T backend pytest -q apps/spring_generator/tests/test_inheritance_backward_compatibility.py` **[pytest]**
- `docker compose exec -T backend pytest -q apps/domain_manifest` **[pytest]**
- `docker compose exec -T backend pytest -q` (full suite) **[pytest]**
