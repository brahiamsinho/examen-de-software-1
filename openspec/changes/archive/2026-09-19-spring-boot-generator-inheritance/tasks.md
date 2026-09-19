# Tasks: Spring Boot Generator Inheritance

Change: `2026-09-19-spring-boot-generator-inheritance`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 420-650 changed lines |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: validation + inheritance context tests/implementation → PR 2: renderer/template + deterministic/backward-compatibility tests |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

## Resolved Scope and Decisions

- Approved output for discriminator-backed tables is JPA Single Table domain entities plus the root Spring Data repository only.
- Subclass Java names are derived with `pascal_case(class_id)`; the root Java name remains `pascal_case(table.name)`.
- The root entity is concrete, not abstract.
- The discriminator column is JPA metadata only and must not render as a normal Java field.
- Field ownership is driven by `Column.owning_class_id`.
- Root-owned and unowned single-column FK fields are supported on the root boundary as designed; subclass-owned FK fields are rejected.
- Malformed inheritance shapes use typed errors before rendering.
- Non-discriminator table generation must remain byte-identical.
- No inheritance DTO, service, controller, subclass repository, Java compilation, OpenAPI, Postman, or Domain Manifest work is in scope.

## Strict-TDD Implementation Tasks

- [x] 1. RED — Add inheritance fixture builders and typed validation expectations in `backend/apps/spring_generator/tests/factories.py` and `backend/apps/spring_generator/tests/test_rejections.py`.
  - Dependencies: existing `Table`, `Column`, `ForeignKey`, `PrimaryKey`, and `ColumnType` factories.
  - Cover missing/empty `source_class_ids`, missing discriminator value, missing discriminator column in `columns`, owner outside hierarchy, unowned scalar, subclass-owned FK, composite FK first, and unnamed enum first.
  - Evidence: `cd backend && pytest backend/apps/spring_generator/tests/test_rejections.py` fails only because inheritance validation/types are not implemented.
  - Acceptance check: failures mention absent `MalformedInheritanceTableError` or current blanket `InheritanceUnsupportedError`, not fixture construction errors.

- [x] 2. GREEN — Implement typed inheritance rejection in `backend/apps/spring_generator/emit/errors.py` without rendering changes.
  - Add `MalformedInheritanceTableError(table_name, reason, class_id=None, column_name=None)` as a subclass of `UngeneratableTableError`.
  - Change `reject_out_of_scope(table)` order to primary key → composite FK → unnamed enum → inheritance shape checks.
  - Accept supported discriminator metadata instead of blanket-rejecting it, while rejecting malformed shapes with stable reasons from `design.md`.
  - Preserve existing non-inheritance rejection types and first-offender behavior.
  - Evidence: `cd backend && pytest backend/apps/spring_generator/tests/test_rejections.py` passes.
  - Rollback boundary: restore the old discriminator blanket rejection and remove the new error class/tests.

- [x] 3. TRIANGULATE — Add context-level partitioning tests in a new `backend/apps/spring_generator/tests/test_inheritance_context.py`.
  - Dependencies: Task 2 passing typed validation.
  - Target discovery: decide whether to add `backend/apps/spring_generator/emit/inheritance_context.py` or keep small helpers in `backend/apps/spring_generator/emit/context.py`.
  - Assert root context gets PK, root-owned scalar, root-owned/unowned FK, and root-owned enum fields.
  - Assert subclass contexts get only matching subclass-owned scalar/enum fields, no PK, no discriminator, no root fields, no sibling subclass fields.
  - Assert subclass class names use `pascal_case(class_id)` for ids such as `car`, `pickup_truck`, and `truck`.
  - Evidence: `cd backend && pytest backend/apps/spring_generator/tests/test_inheritance_context.py` fails because inheritance context builders do not exist.

- [x] 4. GREEN — Build inheritance context structures and field partitioning in `backend/apps/spring_generator/emit/context.py` or `backend/apps/spring_generator/emit/inheritance_context.py`.
  - Add frozen `InheritanceEntityContext` and `InheritanceHierarchyContext` structures.
  - Reuse existing `FieldContext`, `_group_imports`, relationship field logic, enum field logic, and scalar field logic where safe.
  - Keep field order as `table.columns` filtered by structural role/owner.
  - Compute root imports with Single Table JPA metadata imports and field imports; compute subclass imports per class without importing the root same-package class.
  - Evidence: `cd backend && pytest backend/apps/spring_generator/tests/test_inheritance_context.py backend/apps/spring_generator/tests/test_rejections.py` passes.
  - Rollback boundary: remove the new context module/helpers and restore validation-only state from Task 2.

- [x] 5. RED — Add renderer output tests in `backend/apps/spring_generator/tests/test_inheritance_rendering.py`.
  - Dependencies: Task 4 passing context tests.
  - Assert `generate_table_sources` emits exactly `domain/Vehicle.java`, `domain/Car.java`, `domain/Truck.java`, and `persistence/VehicleRepository.java` for a supported hierarchy.
  - Assert deterministic order is root, subclasses in `Table.source_class_ids[1:]`, then root repository, with byte-identical repeated output.
  - Assert root annotations include `@Entity`, `@Table`, `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, `@DiscriminatorColumn(name = "class_type")`, and root `@DiscriminatorValue`.
  - Assert alternate discriminator column `kind` is metadata only and no generated entity declares a `kind` field.
  - Assert subclasses extend `Vehicle`, declare their own `@DiscriminatorValue`, omit id/root/sibling fields, and use `pascal_case(class_id)` names.
  - Assert no path is under `application/`, `application/dto/`, `api/`, `errors/`, `validation/`, or `config/`, and no subclass repository exists.
  - Evidence: `cd backend && pytest backend/apps/spring_generator/tests/test_inheritance_rendering.py` fails because renderer/template support does not exist.

- [x] 6. GREEN — Add inheritance rendering in `backend/apps/spring_generator/emit/renderer.py` and a focused template under `backend/apps/spring_generator/emit/templates/InheritanceEntity.java.j2`.
  - Dependencies: Task 5 RED evidence.
  - Route discriminator-backed tables to the inheritance branch only after `_validate_base_package`, `reject_out_of_scope`, and `reject_invalid_resource_path`.
  - Render root/subclass entities from the inheritance template and reuse `Repository.java.j2` for the root repository.
  - Return only root entity, subclass entities, and root repository in the required deterministic order.
  - Do not edit DTO, service, controller, shared error, enum, OpenAPI, Postman, Domain Manifest, validation, or config generation.
  - Evidence: `cd backend && pytest backend/apps/spring_generator/tests/test_inheritance_rendering.py backend/apps/spring_generator/tests/test_inheritance_context.py backend/apps/spring_generator/tests/test_rejections.py` passes.
  - Rollback boundary: remove the renderer branch/template and keep validation/context code isolated for review.

- [x] 7. RED — Add explicit backward-compatibility coverage for non-discriminator generation in `backend/apps/spring_generator/tests/test_inheritance_backward_compatibility.py` or extend `backend/apps/spring_generator/tests/test_determinism.py` narrowly.
  - Dependencies: Task 6 passing inheritance rendering.
  - Capture a representative non-discriminator `Product` table with scalar, named enum, and single-column FK fields.
  - Assert exactly the existing six file paths and order: domain, repository, request DTO, response DTO, service, controller.
  - Assert emitted contents are byte-identical to an approved inline fixture/golden snapshot representing pre-inheritance output.
  - Evidence: the new test initially fails until the fixture is aligned with current non-discriminator output or any accidental drift is fixed.

- [x] 8. GREEN — Protect non-discriminator byte identity across `backend/apps/spring_generator/emit/renderer.py`, `context.py`, and `emit/templates/*.java.j2`.
  - Dependencies: Task 7 RED evidence.
  - Keep the existing non-discriminator path's context keys, templates, whitespace, file order, and file paths unchanged.
  - If shared helpers were extracted, prove they preserve existing bytes for entity/repository/DTO/service/controller output.
  - Evidence: `cd backend && pytest backend/apps/spring_generator/tests/test_inheritance_backward_compatibility.py backend/apps/spring_generator/tests/test_determinism.py` passes.
  - Rollback boundary: revert helper extraction/template edits that affect non-discriminator bytes.

- [x] 9. TRIANGULATE — Run focused and full backend generator checks.
  - Dependencies: Tasks 1-8 passing.
  - Run focused command: `cd backend && pytest backend/apps/spring_generator/tests`.
  - Run configured backend command: `cd backend && pytest`.
  - Do not add Java compilation tooling; this slice is text-only.
  - Acceptance check: all Spring generator tests pass, existing backend tests pass, and no frontend/mobile/infrastructure files are required for this change.

- [x] 10. REFACTOR — Minimize review surface and confirm boundaries before apply/PR split.
  - Dependencies: full focused checks from Task 9.
  - Inspect changed files with review budget in mind; if implementation exceeds or is likely to exceed 400 changed lines, pause under `ask-on-risk` and request the chaining decision before proceeding.
  - Ensure touched production files are limited to concrete targets: `backend/apps/spring_generator/emit/errors.py`, `backend/apps/spring_generator/emit/context.py` or `emit/inheritance_context.py`, `backend/apps/spring_generator/emit/renderer.py`, and `backend/apps/spring_generator/emit/templates/InheritanceEntity.java.j2`.
  - Ensure touched tests are limited to concrete targets under `backend/apps/spring_generator/tests/`.
  - Acceptance check: no production/test edits introduce inheritance DTOs, services, controllers, subclass repositories, Java compilation, OpenAPI, Postman, Domain Manifest, validation, or config generation.
