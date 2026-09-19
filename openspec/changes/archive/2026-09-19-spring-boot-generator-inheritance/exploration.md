# Exploration: Spring Boot Generator Inheritance

Change: `2026-09-19-spring-boot-generator-inheritance`
Phase: explore
Artifact store: openspec

## Executive summary

The relational mapper already models UML generalization as discriminator-backed Single Table inheritance: one root table contains root attributes, subclass attributes, a `class_type` discriminator, `source_class_ids`, and `discriminator_values`. The recent ownership prerequisite is present: attribute-derived `Column` values carry `owning_class_id`, while synthetic/discriminator/FK/join columns do not. The Spring generator still intentionally rejects any table with `discriminator_column` or `discriminator_values` through `InheritanceUnsupportedError` before rendering. The next slice should not simply remove that rejection; it needs a designed inheritance source model because current `generate_table_sources(Table)` assumes exactly one entity/DTO/service/controller/repository per table.

## Current behavior

### Relational mapping

- `backend/apps/relational_mapping/domain/schema.py::Column` exposes `source_element_id` and `owning_class_id`.
- `backend/apps/relational_mapping/domain/schema.py::Table` exposes `source_class_ids`, `discriminator_column`, and `discriminator_values`.
- `backend/apps/relational_mapping/mapping/mapper.py::_map_table_for_root` collapses a hierarchy into the root table, adds `class_type`, records discriminator values by UML class id, and marks descendant attribute columns nullable.
- `backend/apps/relational_mapping/mapping/mapper.py::_map_attribute_column` sets `owning_class_id` only for UML attribute-derived columns.
- `backend/apps/relational_mapping/tests/test_map_inheritance.py` verifies root/subclass column flattening, discriminator values, descendant nullability, and ownership preservation.
- `backend/apps/relational_mapping/tests/test_map_attributes.py::test_attribute_named_class_type_is_disambiguated_from_discriminator` proves model attributes named `class_type` are renamed, avoiding collision with the discriminator.

### Spring generation

- `backend/apps/spring_generator/emit/renderer.py::generate_table_sources` validates package, calls `reject_out_of_scope`, then emits exactly six files for one `Table`: entity, repository, request DTO, response DTO, service, controller.
- `backend/apps/spring_generator/emit/errors.py::reject_out_of_scope` rejects in fixed order: PK shape, composite FK, discriminator/inheritance, unnamed enum.
- `backend/apps/spring_generator/emit/errors.py::InheritanceUnsupportedError` is the current typed rejection for discriminator-backed tables.
- `backend/apps/spring_generator/tests/test_rejections.py::test_discriminator_table_with_owned_attribute_column_is_still_rejected_before_rendering` locks the current boundary: ownership metadata is not inheritance support.
- `backend/apps/spring_generator/emit/context.py` assumes one Java entity class is derived from `pascal_case(table.name)` and one DTO/service/controller pair shares that class name.
- `backend/apps/spring_generator/emit/templates/Entity.java.j2` has no inheritance annotations (`@Inheritance`, `@DiscriminatorColumn`, `@DiscriminatorValue`) and no base/subclass distinction.

## Reusable abstractions

- Frozen dataclass context pattern in `backend/apps/spring_generator/emit/context.py` can be extended with inheritance-specific context objects while keeping templates data-driven.
- `_group_imports`, `pascal_case`, `camel_case`, `relationship_base_name`, and `package_path` are reusable for new inheritance files.
- Existing Jinja renderer setup in `backend/apps/spring_generator/emit/renderer.py` should remain the only Java text rendering mechanism.
- Existing templates for DTO getters/setters and field loops are reusable if inheritance DTOs are kept as POJOs with generated fields.
- `Table.source_class_ids` + `Table.discriminator_values` give the hierarchy class set and Java class names can be derived from discriminator labels.
- `Column.owning_class_id` is the discriminator-backed field partitioning hook for root vs subclass attributes.
- Existing `GeneratedSources`/`GeneratedFile` can carry more than six files without a new output type.

## Exact gaps

1. **Entry point contract gap:** `generate_table_sources(Table)` currently means one table -> one entity and API surface. Inheritance needs one table -> multiple domain classes and probably multiple DTO/API artifacts.
2. **Rejection gate gap:** `reject_out_of_scope` blocks every discriminator table, so no inheritance context can be built until the design changes this check safely.
3. **Class partitioning gap:** no helper groups `Column`s by `owning_class_id` and excludes synthetic/discriminator/FK columns from subclass-owned field sets.
4. **Root entity annotation gap:** no template/context emits `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)` or `@DiscriminatorColumn(name = "class_type")`.
5. **Subclass entity gap:** no source files exist for concrete subclass entities with `@DiscriminatorValue(...)`, `extends Root`, subclass-only fields, and inherited id/root fields omitted.
6. **DTO/API semantics gap:** current DTO/service/controller code assumes one request/response DTO and one CRUD resource for the root table, with no discriminator-aware create/update/list behavior.
7. **Repository typing gap:** current repository is for the root entity only; no decision exists on subclass repositories or root-polymorphic repository operations.
8. **FK relationship inheritance gap:** relationship FK columns carry no `owning_class_id`, so if a relationship endpoint involves a subclass, current metadata cannot assign that relationship field to a subclass entity without whole-model endpoint metadata.
9. **Compilation gap:** generated Java is still text-only; inheritance annotation correctness cannot be proven by `javac` in this slice.

## Product and technical decisions to make

1. **First-slice API shape:** either root-only polymorphic CRUD for the hierarchy table, or domain-only inheritance classes while preserving current API rejection. Recommended first slice: domain + repository only for discriminator tables, keep DTO/service/controller out of scope until API behavior is designed.
2. **Entity class layout:** recommended JPA Single Table layout is root `@Entity @Inheritance(SINGLE_TABLE) @DiscriminatorColumn`, concrete subclasses `@Entity @DiscriminatorValue`, all classes in the same `domain` package.
3. **Field ownership:** root class gets synthetic `id`, root-owned attributes, discriminator metadata annotation, and likely no Java field for `class_type`; each subclass gets only its owned attribute columns. Discriminator column should not become a normal field in any entity in first slice.
4. **Root abstractness:** decide whether the root entity is abstract. UML does not currently expose abstract class metadata in the relational table, so recommended default is non-abstract to preserve root rows as valid when `discriminator_values` includes the root class id.
5. **DTO/controller behavior:** defer until a later slice because create/update requires choosing a concrete subtype and validation rules differ by subtype.
6. **Relationship columns:** keep existing FK behavior only for non-inheritance tables in first slice; do not attempt subclass-owned relationships until relational metadata can identify endpoint ownership.
7. **Generated file count/order:** if first slice emits domain + root repository only, fixed order could be root entity, subclass entities in `source_class_ids` order, root repository. If future API files are emitted later, update the package/path spec then.
8. **Backwards compatibility:** scalar/non-discriminator tables must keep exactly the current six-file output and byte-identical contents.

## Risks

- Java/JPA correctness risk: Single Table annotation combinations are easy to render incorrectly and are not compile-tested today.
- Scope risk: full inheritance plus DTO/service/controller semantics likely exceeds the 400-line review budget.
- Metadata risk: `owning_class_id` solves attribute placement but not relationship endpoint placement.
- Behavioral ambiguity risk: root vs subtype CRUD endpoints and request discriminator contracts are product decisions, not just code mechanics.
- Regression risk: weakening `reject_out_of_scope` too broadly could accidentally allow malformed discriminator tables.
- Naming collision risk: discriminator values converted to Java class names may collide with root/enum names in a future whole-model orchestrator, but no orchestrator exists yet.

## Bounded first-slice scope

Recommended first SDD slice: **Generate JPA Single Table domain classes and the root repository for discriminator-backed tables; keep API/application DTO layers rejected or explicitly omitted for inheritance tables.**

In scope:

- Add inheritance-specific context builders under `backend/apps/spring_generator/emit/context.py` or a small sibling module.
- Add/extend templates for root and subclass entity rendering using JPA inheritance annotations.
- Add a dedicated renderer branch or new entry point for discriminator tables that emits domain classes and the root repository only.
- Preserve current six-file output byte-for-byte for non-discriminator tables.
- Tests for root `@Inheritance(SINGLE_TABLE)`, `@DiscriminatorColumn`, subclass `extends Root`, `@DiscriminatorValue`, root/subclass field partitioning by `owning_class_id`, deterministic file order, and continued rejection/omission of DTO/service/controller for inheritance tables.

Out of scope:

- No create/update/list subtype API behavior.
- No subclass repositories unless product decides they are needed.
- No bidirectional relationships, `@OneToMany`, or `@ManyToMany`.
- No generated Java compilation infrastructure.
- No config/OpenAPI/Postman/Domain Manifest work.

## Suggested next phase

Proceed to `sdd-propose` for `2026-09-19-spring-boot-generator-inheritance`, but pause on one product-risk question before detailed spec/design: should the first inheritance slice be domain+repository only, or should it also define polymorphic DTO/service/controller CRUD behavior now?
