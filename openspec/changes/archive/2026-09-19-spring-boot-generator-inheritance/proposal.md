# Proposal: Spring Boot Generator Inheritance

Change: `2026-09-19-spring-boot-generator-inheritance`
Artifact store: OpenSpec
Status: proposed

## Intent

Add the first bounded Spring Boot generator slice for discriminator-backed relational tables by generating JPA Single Table inheritance domain classes plus the root Spring Data repository.

This change lets the existing UML generalization mapping become visible in generated Java source without prematurely designing subtype-aware API behavior.

## Background

The relational mapper already represents UML generalization as a Single Table shape:

- one root table contains root and subclass attributes;
- `Table.discriminator_column` identifies the discriminator column, currently `class_type`;
- `Table.discriminator_values` maps UML class ids to discriminator labels;
- `Table.source_class_ids` records the hierarchy class ids;
- attribute-derived `Column` values now carry `owning_class_id`;
- synthetic id, discriminator, foreign key, and join-table columns keep `owning_class_id = None`.

The Spring generator currently rejects every discriminator-backed table before rendering. That is safe but blocks generated Java support for mapped UML inheritance.

## Scope

In scope:

1. Generate JPA Single Table domain classes for discriminator-backed tables.
2. Generate the root repository for the root entity only.
3. Preserve byte-identical six-file generation for non-discriminator tables.
4. Preserve safe typed rejection for malformed or unsupported inheritance shapes.
5. Add proposal/spec/design/tasks follow-up direction for tests proving deterministic output, annotation shape, field ownership partitioning, and rejection boundaries.

Out of scope:

- DTOs for inheritance tables.
- Services for inheritance tables.
- Controllers for inheritance tables.
- Subclass repositories.
- Generated Java compilation infrastructure.
- Generator configuration layer.
- OpenAPI generation.
- Postman generation.
- Domain Manifest generation.
- Whole-model orchestration or cross-artifact class-name collision detection.
- Bidirectional relationships, `@OneToMany`, `@ManyToMany`, or subclass-owned relationship fields.
- Production-code or test edits in this proposal phase.

## Proposed behavior

For a discriminator-backed table, `generate_table_sources(table, *, base_package=...)` should emit only:

1. root entity in `domain/`;
2. concrete subclass entities in `domain/`;
3. root repository in `persistence/`.

Recommended deterministic file order:

1. root entity;
2. subclass entities in `Table.source_class_ids` order, excluding the root class id;
3. root repository.

The root entity should render as a normal JPA entity with Single Table metadata, including:

- `@Entity`;
- `@Table(name = "...")`;
- `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`;
- `@DiscriminatorColumn(name = "class_type")` or the table's actual discriminator column name;
- `@DiscriminatorValue("...")` when a root discriminator value is present;
- the synthetic UUID primary key;
- root-owned scalar fields only.

Each subclass entity should render with:

- `@Entity`;
- `@DiscriminatorValue("...")`;
- `extends RootEntity`;
- only the scalar fields whose `owning_class_id` matches that subclass id;
- no duplicated id field;
- no duplicated root-owned fields;
- no normal Java field for the discriminator column.

The root repository should continue to be a Spring Data repository for the root entity type. It should be polymorphic by JPA behavior, not by additional generated subclass repositories.

## Resolved assumptions

1. The approved first slice is domain plus root repository only.
2. The root entity is generated as non-abstract unless future UML metadata explicitly exposes abstract class information.
3. The discriminator column is JPA metadata, not a normal entity property in this slice.
4. Attribute placement is driven by `Column.owning_class_id`.
5. Columns without `owning_class_id` are root-level only when they are supported structural columns such as the synthetic id; unsupported columns remain safely rejected.
6. Relationship ownership is not inferable for subclass relationships from the current metadata, so subclass-owned relationship fields are deferred.
7. The generator remains text-only; Java compilation proof remains a later SDD cycle.

## Affected areas

Primary affected code areas for later implementation:

- `backend/apps/spring_generator/emit/context.py` or a small sibling inheritance context module.
- `backend/apps/spring_generator/emit/renderer.py` discriminator-table branch.
- `backend/apps/spring_generator/emit/errors.py` rejection narrowing and new malformed-inheritance checks.
- `backend/apps/spring_generator/emit/templates/*.java.j2` for root and subclass entity rendering.
- `backend/apps/spring_generator/tests/` for deterministic output, annotations, field partitioning, and rejection behavior.

Unaffected areas by design:

- non-discriminator table output bytes;
- DTO/service/controller templates for existing non-discriminator tables;
- relational mapper production behavior;
- generated shared errors;
- enum generation;
- frontend, mobile, OpenAPI, Postman, Domain Manifest, and infrastructure.

## Acceptance direction

A later spec/design/tasks phase should turn this proposal into concrete checks. Acceptance should include at least:

1. A discriminator-backed root table emits root entity, subclass entities, and root repository only.
2. Root entity includes Single Table inheritance annotations.
3. Subclass entities include `extends RootEntity` and `@DiscriminatorValue`.
4. Root-owned attributes render only on the root entity.
5. Subclass-owned attributes render only on the matching subclass entity.
6. The discriminator column does not render as a normal Java field.
7. Non-discriminator tables still emit the exact existing six files byte-for-byte.
8. Malformed unsupported inheritance tables are rejected with typed errors before rendering.
9. No DTO, service, controller, subclass repository, config, OpenAPI, Postman, or Domain Manifest artifact is generated for discriminator-backed tables.
10. Output order is deterministic across repeated calls.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| JPA annotation mistakes | Generated source may be structurally wrong even if text tests pass. | Keep slice small, assert exact annotation/import lines, defer compilation to its own cycle. |
| Rejection gate too permissive | Unsupported discriminator shapes could generate misleading Java. | Narrow rejection deliberately and add typed malformed-inheritance checks before render. |
| Field partitioning bugs | Root/subclass attributes could duplicate or disappear. | Test partitioning with root-owned, subclass-owned, synthetic, and discriminator columns. |
| Relationship ownership ambiguity | Subclass relationships could be incorrectly placed. | Keep subclass-owned relationship fields out of scope until metadata supports endpoint ownership. |
| Review-size growth | Inheritance plus API behavior would exceed the review budget. | Keep approved first slice to domain classes plus root repository only. |
| Backward compatibility regression | Existing six-file generation could change unintentionally. | Add byte-identical regression coverage for non-discriminator tables. |

## Rollback

Rollback is straightforward because this slice is additive to the Spring generator boundary:

1. Restore the existing discriminator rejection path for all discriminator-backed tables.
2. Remove or disable the inheritance renderer branch and templates.
3. Keep non-discriminator generator behavior unchanged.
4. Retain relational mapper ownership metadata, because it is already a committed prerequisite and useful independent state.

## Success criteria

The change is successful when a supported discriminator-backed table can generate JPA Single Table domain source plus a root repository deterministically, while all existing non-discriminator generation remains byte-identical and unsupported inheritance/API shapes remain safely rejected.

## Non-goals

This proposal deliberately does not define polymorphic create/update/list behavior, subtype request contracts, validation rules by subtype, generated controller routes, OpenAPI schema shape, Postman examples, Domain Manifest capabilities, or Java compilation infrastructure.
