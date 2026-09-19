# Implementation Tasks: Relational Column Ownership

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 90-160 additions/deletions |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Tasks

- [x] 1. RED: Add focused relational-mapping ownership tests and confirm they fail for the missing `Column.owning_class_id` contract.
  - Files: `backend/apps/relational_mapping/tests/test_schema.py`, `backend/apps/relational_mapping/tests/test_map_attributes.py`, `backend/apps/relational_mapping/tests/test_map_inheritance.py`, `backend/apps/relational_mapping/tests/test_map_relationships.py`.
  - Cover: default `Column(...).owning_class_id is None`; root attribute columns preserve root class id; subclass attributes flattened into the root Single Table preserve subclass class id; synthetic `id`, discriminator `class_type`, relationship FK columns, join-table `id`, and join-table FK columns keep `None`.
  - Verification: run `docker compose exec -T backend pytest -q backend/apps/relational_mapping/tests/test_schema.py backend/apps/relational_mapping/tests/test_map_attributes.py backend/apps/relational_mapping/tests/test_map_inheritance.py backend/apps/relational_mapping/tests/test_map_relationships.py` and record the expected RED failure caused by absent ownership metadata.

- [x] 2. RED: Add Spring generator regression coverage proving ownership metadata does not enable inheritance generation.
  - Files: `backend/apps/spring_generator/tests/test_rejections.py`; optionally `backend/apps/spring_generator/tests/factories.py` only if a helper parameter reduces noisy setup.
  - Cover: a `Table` with `discriminator_column` and at least one attribute-derived `Column` with non-`None` `owning_class_id` still raises the existing typed unsupported-table-shape error and emits no Java inheritance source.
  - Verification: run `docker compose exec -T backend pytest -q backend/apps/spring_generator/tests/test_rejections.py` and record the expected RED failure if `Column` does not yet accept `owning_class_id`.

- [x] 3. GREEN: Add the ownership field to the relational domain model without changing non-attribute constructors.
  - File: `backend/apps/relational_mapping/domain/schema.py`.
  - Implement: add `owning_class_id: ElementId | None = None` to the frozen `Column` dataclass immediately after `source_element_id`.
  - Verification: rerun `docker compose exec -T backend pytest -q backend/apps/relational_mapping/tests/test_schema.py` and confirm the schema/default test passes.

- [x] 4. GREEN: Thread UML class ownership through attribute-column mapping only.
  - File: `backend/apps/relational_mapping/mapping/mapper.py`.
  - Implement: make `_map_attribute_column(...)` accept required keyword-only `owning_class_id: ElementId`; set both `source_element_id=attribute.id` and `owning_class_id=owning_class_id` on primitive and enum attribute columns; pass the currently iterated `class_id` from `_map_table_for_root(...)` for root and descendant attributes.
  - Preserve: leave synthetic `id`, `class_type`, relationship FK, and join-table `Column(...)` calls unchanged so they keep the default `None`.
  - Verification: run `docker compose exec -T backend pytest -q backend/apps/relational_mapping/tests/test_map_attributes.py backend/apps/relational_mapping/tests/test_map_inheritance.py backend/apps/relational_mapping/tests/test_map_relationships.py`.

- [x] 5. TRIANGULATE: Prove source attribute identity and owning class identity are independent facts across inheritance and relationships.
  - Files: same tests from tasks 1-2; add only minimal assertions if an edge case is still unproven.
  - Cover: at least one attribute-derived column asserts both `source_element_id == UmlAttribute.id` and `owning_class_id == UmlClass.id`; at least one FK/join-column asserts `source_element_id` behavior is not reused as ownership.
  - Verification: run the focused suite `docker compose exec -T backend pytest -q backend/apps/relational_mapping/tests/test_schema.py backend/apps/relational_mapping/tests/test_map_attributes.py backend/apps/relational_mapping/tests/test_map_inheritance.py backend/apps/relational_mapping/tests/test_map_relationships.py backend/apps/spring_generator/tests/test_rejections.py`.

- [x] 6. REFACTOR: Keep the implementation small and reviewable without Spring production changes.
  - Files: `backend/apps/relational_mapping/domain/schema.py`, `backend/apps/relational_mapping/mapping/mapper.py`, touched test files only.
  - Check: no edits under `backend/apps/spring_generator/emit/`; no generator template changes; no generated Java inheritance support added; no unrelated formatting churn.
  - Verification: inspect the diff and keep changed lines within the forecasted single-PR budget.

- [x] 7. Full verification: run the strict backend gate after focused tests are green.
  - Command: `docker compose exec -T backend pytest -q`.
  - Expected: full backend pytest remains green from the parent baseline; if failures appear outside this change, document them separately with file paths and failure names.
