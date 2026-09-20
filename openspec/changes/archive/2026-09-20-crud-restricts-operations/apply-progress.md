# Apply Progress: crud-restricts-operations (slice 1)

Mode: Strict TDD. Store: hybrid. Status: 23/24 tasks complete; 9.1 is an archive-time reminder and stays unchecked until archive.
Commit state: nothing staged or committed; `.pi/` untouched.

## Test counts (`docker compose exec -T backend pytest -q`)

| Scope | Before | After |
|---|---|---|
| Full backend suite | 1214 passed | 1261 passed (+47) |
| `apps/relational_mapping` | 138 | 170 |
| `apps/domain_manifest` | 125 | 140 |
| `apps/spring_generator` + `apps/generation_runner` + the two above | n/a | 735 passed |

## TDD Cycle Evidence

| Task | RED evidence | GREEN evidence |
|---|---|---|
| 1.1 / 1.2 | `test_profile.py` collection error: `ImportError: cannot import name 'OPERATION_NAMES'` | `test_profile.py`: 9 -> 39 passed after `profile.py` gained `OPERATION_NAMES`, `_CRUD_TO_OPERATIONS`, `_READ_OPERATIONS`, `effective_operations` |
| 2.1 / 2.2 | `test_schema.py`: 2 failed (`AttributeError: type object 'Table' has no attribute 'effective_operations'`), 12 passed | `apps/relational_mapping`: 170 passed after the `Table.effective_operations` property |
| 3.1 / 3.2 | `test_manifest.py`: 8 failed for the right reason (`Left contains 3 more items, first extra item: ('delete', ...)`), 42 passed | `apps/domain_manifest` + `apps/relational_mapping`: 309 passed after `_operations(resource_path, names)` and the empty-set suppression |
| 4.1 | Passes on first run by design (anti-drift tripwire); proof is mutation M3/M5 | Included in the 309; M5 turns 7 tests red |
| 4.2 | n/a (read-only) | `test_builder_decoupling.py`: 14 passed, `git diff` on the file empty |
| 5.1 | n/a (read-only) | sample tripwires + attributes + determinism + cli: 37 passed; drift guard `test_computed_paths_equal_the_paths_springdoc_served`: passed, all unmodified |
| 6.1-6.5 | Mutations (below) | Each reverted; `cmp` against the backup identical; suites re-run green |
| 7.1-7.3 | n/a | 735 passed (four suites); full suite 1261 passed; `git diff --stat` empty for `apps/spring_generator`, `frontend/`, `docker-compose.yml`, `scripts/`, `test_builder_decoupling.py` |
| 8.1-8.6 | n/a (docs) | DD160-DD167 in `DECISIONS_LOG.md`, DD147 annotated in place, CURRENT_STATE, HANDOFF_LATEST, NEXT_STEPS, session note |

REFACTOR: none needed (functions are minimal and match the design text).

## Mutation results

| Mutant | Result (relational_mapping + domain_manifest) |
|---|---|
| M1 drop `read_only` intersection | 10 failed; reverted |
| M2 `crud == ()` treated as undeclared | 5 failed; reverted |
| M3 iterate `names` in `entities.py` | First run SURVIVED (309 passed): equivalent through `build_entity` because `effective_operations` already returns canonical order. Added `test_the_row_filter_orders_by_the_controller_table_whatever_the_caller_passes` (calls `_operations` with out-of-order names); re-run: 1 failed; reverted |
| M4 keep `resource_path` when `operations` empty | 2 failed; reverted |
| M5 drop `if name in names` | 7 failed; reverted |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command | `docker compose exec -T backend pytest -q apps/relational_mapping apps/domain_manifest` -> 310 passed |
| Runtime harness | Full suite `docker compose exec -T backend pytest -q` -> 1261 passed |
| Rollback boundary | `domain/profile.py`, `domain/schema.py`, `builder/entities.py`, the three test files, the change folder and `docs/ai`; independent of slice 2 |

## Deviations / findings

- M3 equivalence (above): the design says M3 is killed by the existing suite; it is not through `build_entity`. One extra direct unit test was added (about 6 lines).
- Task 3.1 name: `"bad$name"` verified to raise `InvalidResourcePathError` via `resource_path_segment`. For the inheritance not-newly-validated test `"bad$name"` cannot be used (`pascal_case` rejects it independently), so the test uses `"_order"` (legal Java name, invalid path segment).
- The tests dir `test_manifest.py` cross-imports `_OPERATIONS` and `_operations` from `builder.entities` (private names, tests only).
- Stale docs fixed: DECISIONS_LOG / CURRENT_STATE / HANDOFF_LATEST / NEXT_STEPS still called `uml-generation-profile-authoring` (07fb611), `uml-generation-profile-panel` (4b923aa) and `generated-spring-api-filtering-search` (20bf71c) uncommitted or verify pending; all three are archived and committed.
- Spec delta size is about 286 lines on disk versus the ~118 estimated in the forecast.

## Size vs 800 budget

`git diff --stat` on tracked files: 253 insertions, 26 deletions (backend 215/10 including tests; docs 38 added). Untracked: session note 22 lines, spec deltas 286 lines. Authored total about 561 added lines, under the 700 stop threshold and the 800 budget. No `size:exception` needed.
