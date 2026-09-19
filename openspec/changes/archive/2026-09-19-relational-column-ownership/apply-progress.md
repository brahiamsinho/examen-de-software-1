# Apply Progress: Relational Column Ownership

## Structured Status Consumed

- Native status schema: `gentle-ai.sdd-status` v2.
- Change: `relational-column-ownership`.
- Artifact store: `openspec`.
- `nextRecommended`: `apply`.
- `dependencies.apply`: `ready`.
- Workspace root: `C:\Users\brahi\OneDrive\Escritorio\Examen-1-Software`.
- Allowed edit roots: `C:\Users\brahi\OneDrive\Escritorio\Examen-1-Software`.
- Action context warning: none; repo-local workspace matched the requested workspace.
- Apply-progress locator was unresolved in native status, so this file was created at `openspec/changes/relational-column-ownership/apply-progress.md`.

## Workload / PR Boundary

- Delivery strategy: ask-on-risk.
- Review forecast: Low risk, single PR, no decision needed before apply.
- Actual changed-line forecast from `git diff --stat`: 106 insertions, 3 deletions across 7 source/test files before SDD artifact updates; within the 400-line review budget.
- PR boundary: single cohesive relational-mapping metadata change plus Spring rejection regression coverage.

## Completed Tasks and Persisted Checkbox Updates

- [x] 1. RED relational-mapping ownership tests added and failed for missing `Column.owning_class_id`.
- [x] 2. RED Spring generator rejection coverage added and failed because `Column` did not yet accept `owning_class_id`.
- [x] 3. GREEN `Column.owning_class_id` added with default `None`.
- [x] 4. GREEN mapper now threads owning UML class id only through attribute-derived columns.
- [x] 5. TRIANGULATE tests prove source attribute id and owning class id are independent facts, and relationship/join columns do not reuse source identity as ownership.
- [x] 6. REFACTOR diff inspected; no edits under `backend/apps/spring_generator/emit/`, no Java inheritance generation enabled, no template changes.
- [x] 7. Full backend strict pytest gate passed.

Persisted checkbox updates were applied in `openspec/changes/relational-column-ownership/tasks.md`.

## Files Changed

- `backend/apps/relational_mapping/domain/schema.py`
- `backend/apps/relational_mapping/mapping/mapper.py`
- `backend/apps/relational_mapping/tests/test_schema.py`
- `backend/apps/relational_mapping/tests/test_map_attributes.py`
- `backend/apps/relational_mapping/tests/test_map_inheritance.py`
- `backend/apps/relational_mapping/tests/test_map_relationships.py`
- `backend/apps/spring_generator/tests/test_rejections.py`
- `openspec/changes/relational-column-ownership/tasks.md`
- `openspec/changes/relational-column-ownership/apply-progress.md`

## TDD Cycle Evidence

| Cycle | Phase | Command | Result | Evidence |
|---|---|---|---|---|
| 1 | RED | `docker compose exec -T backend pytest -q backend/apps/relational_mapping/tests/test_schema.py backend/apps/relational_mapping/tests/test_map_attributes.py backend/apps/relational_mapping/tests/test_map_inheritance.py backend/apps/relational_mapping/tests/test_map_relationships.py backend/apps/spring_generator/tests/test_rejections.py` | Infrastructure/path mismatch | Backend container working directory is already the backend root, so the parent-style `backend/apps/...` paths produced `ERROR: file or directory not found`. |
| 1 | RED | `docker compose exec -T backend pytest -q apps/relational_mapping/tests/test_schema.py apps/relational_mapping/tests/test_map_attributes.py apps/relational_mapping/tests/test_map_inheritance.py apps/relational_mapping/tests/test_map_relationships.py apps/spring_generator/tests/test_rejections.py` | Expected failure | 8 failed, 36 passed. Failures were missing `owning_class_id` attribute or unexpected keyword argument. |
| 2 | GREEN | `docker compose exec -T backend pytest -q apps/relational_mapping/tests/test_schema.py` | Passed | 10 passed. |
| 3 | GREEN | `docker compose exec -T backend pytest -q apps/relational_mapping/tests/test_map_attributes.py apps/relational_mapping/tests/test_map_inheritance.py apps/relational_mapping/tests/test_map_relationships.py` | Passed | 21 passed. |
| 4 | TRIANGULATE | `docker compose exec -T backend pytest -q apps/relational_mapping/tests/test_schema.py apps/relational_mapping/tests/test_map_attributes.py apps/relational_mapping/tests/test_map_inheritance.py apps/relational_mapping/tests/test_map_relationships.py apps/spring_generator/tests/test_rejections.py` | Passed | 44 passed. |
| 5 | REFACTOR / full gate | `docker compose exec -T backend pytest -q` | Passed | 636 passed in 59.62s. |

## Test Commands Run

- `docker compose exec -T backend pytest -q backend/apps/relational_mapping/tests/test_schema.py backend/apps/relational_mapping/tests/test_map_attributes.py backend/apps/relational_mapping/tests/test_map_inheritance.py backend/apps/relational_mapping/tests/test_map_relationships.py backend/apps/spring_generator/tests/test_rejections.py` — path mismatch, no tests collected.
- `docker compose exec -T backend pytest -q apps/relational_mapping/tests/test_schema.py apps/relational_mapping/tests/test_map_attributes.py apps/relational_mapping/tests/test_map_inheritance.py apps/relational_mapping/tests/test_map_relationships.py apps/spring_generator/tests/test_rejections.py` — RED: 8 failed, 36 passed.
- `docker compose exec -T backend pytest -q apps/relational_mapping/tests/test_schema.py` — GREEN: 10 passed.
- `docker compose exec -T backend pytest -q apps/relational_mapping/tests/test_map_attributes.py apps/relational_mapping/tests/test_map_inheritance.py apps/relational_mapping/tests/test_map_relationships.py` — GREEN: 21 passed.
- `docker compose exec -T backend pytest -q apps/relational_mapping/tests/test_schema.py apps/relational_mapping/tests/test_map_attributes.py apps/relational_mapping/tests/test_map_inheritance.py apps/relational_mapping/tests/test_map_relationships.py apps/spring_generator/tests/test_rejections.py` — TRIANGULATE: 44 passed.
- `docker compose exec -T backend pytest -q` — full strict backend gate: 636 passed.

## Deviations from Design

- No production files under `backend/apps/spring_generator/emit/` were touched.
- No Java inheritance generation was enabled.
- `backend/apps/spring_generator/tests/factories.py` was not changed because direct `Column(...)` construction kept the regression test clear and small.
- The parent-provided path form with `backend/apps/...` did not resolve inside the backend container; equivalent `apps/...` paths were used for real pytest execution.

## Remaining Tasks

None. All implementation tasks in `tasks.md` are visibly marked `- [x]`.

## Produced Status

- Apply implementation is complete for the approved task set.
- Recommended next native phase: `verify` is optional when requested; otherwise the status engine may recommend `archive` after it observes all tasks complete.
