# Tasks: CRUD Declaration Restricts Operations (slice 1)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~473 (30 source, 132 test, ~286 spec delta, 25 docs; corrected at archive from ~305 / ~118 spec delta) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR (slice 2 `spring-generator-crud-restriction` is a separate later change) |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Shared function + Table property + manifest filtering + docs | PR 1 | `docker compose exec -T backend pytest -q apps/relational_mapping apps/domain_manifest` | Full suite `docker compose exec -T backend pytest -q` | Whole PR; independent of slice 2 |

Test command everywhere: `docker compose exec -T backend pytest -q <path>` (RED first, then GREEN).

## Phase 1: Shared derivation (DD160, DD161)

- [x] 1.1 RED: in `backend/apps/relational_mapping/tests/test_profile.py` add table-driven DD161 truth-table test (9 crud rows x read_only None/False/True; `profile=None` and `TableProfile()`), order/determinism test (`type is tuple`, `type(name) is str`, `(DELETE, CREATE, READ)` canonical), `OPERATION_NAMES` literal test. Fails on import.
- [x] 1.2 GREEN: in `backend/apps/relational_mapping/domain/profile.py` add `OPERATION_NAMES`, `_CRUD_TO_OPERATIONS`, `_READ_OPERATIONS`, `effective_operations()` exactly per DD160; no new imports.

## Phase 2: Table property (DD162)

- [x] 2.1 RED: in `backend/apps/relational_mapping/tests/test_schema.py` test `Table(profile=None).effective_operations == OPERATION_NAMES`, READ profile case, not in `dataclasses.fields(Table)`, equal tables compare `==` with equal fields and `repr` (Table is unhashable: dict-typed field), `repr` lacks it, `Column` unaffected.
- [x] 2.2 GREEN: in `backend/apps/relational_mapping/domain/schema.py` add the `@property effective_operations` on `Table` and import the function (not a dataclass field).

## Phase 3: Manifest filtering (DD163, DD164)

- [x] 3.1 RED: in `backend/apps/domain_manifest/tests/test_manifest.py` rename/invert `test_declaring_crud_does_not_filter_the_operations` (~:282) to `test_declaring_crud_restricts_the_operations` (`entity["profile"]["crud"] == ["read"]` still verbatim); add tests for crud subsets in canonical order, `crud=()` and `read_only=True`+`(CREATE,)` giving `operations == []` and `resourcePath is None`, readOnly intersection with `/api/purchases` paths, `read_only` False/None, undeclared (`TableProfile(auditable=True)`), biconditional `(resourcePath is None) == (operations == [])`, invalid table name (e.g. `"bad$name"`, verified to raise `InvalidResourcePathError`) still raising `ManifestError` with `crud=()` and non-empty, inheritance table with empty set not newly validated.
- [x] 3.2 GREEN: in `backend/apps/domain_manifest/builder/entities.py` change to `_operations(resource_path, names)` filtering `_OPERATIONS` in declared order; in `build_entity` read `table.effective_operations`, compute `resource_path` first, then set it to `None` when the set is empty. Do not touch `builder/profile.py`.

## Phase 4: Constant and guard tripwires (tests only)

- [x] 4.1 In `test_manifest.py` add anti-drift test `tuple(name for name, *_ in _OPERATIONS) == OPERATION_NAMES` (cross-app import allowed in tests; passes immediately, kill-checked by M3/M5).
- [x] 4.2 Run `backend/apps/domain_manifest/tests/test_builder_decoupling.py` (read-only) and confirm it passes UNCHANGED.

## Phase 5: Sample neutrality

- [x] 5.1 Run `test_sample_entity_header`, `test_operations_exist_exactly_when_the_entity_has_a_controller`, `test_attributes.py::test_sample_attribute`, `test_determinism.py`, `test_cli.py` and the drift guard vs `api-docs.json` (read-only); all pass unmodified.

## Phase 6: Mutation checks (apply, see red, revert, re-verify green)

- [x] 6.1 M1 drop the `read_only` intersection in `profile.py`.
- [x] 6.2 M2 treat `crud == ()` as undeclared (all six).
- [x] 6.3 M3 iterate `names` instead of `_OPERATIONS` in `entities.py` (order mutant).
- [x] 6.4 M4 keep `resource_path` when `operations` is empty.
- [x] 6.5 M5 drop the `if name in names` filter.

## Phase 7: Verification

- [x] 7.1 Run `apps/relational_mapping`, `apps/domain_manifest`, `apps/spring_generator`, `apps/generation_runner` suites; all green.
- [x] 7.2 Run the full backend suite `docker compose exec -T backend pytest -q`; green.
- [x] 7.3 `git diff --stat` empty for `backend/apps/spring_generator` (read-only), `frontend/` (read-only), `docker-compose.yml` (read-only), `scripts/` (read-only).

## Phase 8: Documentation (docs/ai memory)

- [x] 8.1 Add DD160-DD167 to `docs/ai/DECISIONS_LOG.md` (same text as `design.md`, which already holds them; confirm parity).
- [x] 8.2 Annotate DD147 in `docs/ai/DECISIONS_LOG.md` IN PLACE as "retired by DD167 (manifest) / slice 2 (generator)"; never delete; record DD166 divergence.
- [x] 8.3 Update `docs/ai/CURRENT_STATE.md`.
- [x] 8.4 Update `docs/ai/HANDOFF_LATEST.md`.
- [x] 8.5 Update `docs/ai/NEXT_STEPS.md` (next: slice 2 `spring-generator-crud-restriction`).
- [x] 8.6 Create `docs/ai/sessions/2026-09-20-agent-crud-restricts-operations.md`.

## Phase 9: Archive-time reminder

- [x] 9.1 At archive: delta has a RENAMED header (exact compose syntax `A → B` plus Reason line) and a MODIFIED `Declared-Facts-Only Emission` restating all 11 on-disk scenarios; main `generation-profile` gains one requirement (9 to 10); `domain-manifest-export` stays at 15 requirements (rename, no add); verify counts on disk after archive.

Total: 24 tasks (sequential within phases; 1-2 and 3 are dependent, 8.x docs may run parallel with Phase 6-7).
