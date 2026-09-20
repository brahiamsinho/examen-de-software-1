# Tasks: Inheritance Subclass Java Class Naming

Design decisions DD87-DD91. Tests run only in Docker from `/app` (= `backend/`): `docker compose exec -T backend pytest -q <path>` (container paths start `apps/`).

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~170 (source 1, tests ~90, sample ~30, docs ~40, spec delta already written) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR, 4 work units in order |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | RED tests + line-169 fix | PR 1 | `docker compose exec -T backend pytest -q apps/spring_generator/tests/test_inheritance_context.py apps/spring_generator/tests/test_project_sources.py apps/spring_generator/tests/test_model_sources.py` | N/A: pure Python | `inheritance_context.py` + new tests |
| 2 | Fixture realignment | PR 1 | `docker compose exec -T backend pytest -q apps/spring_generator` | N/A: pure Python | test files only |
| 3 | Sample model + compile gate | PR 1 | `docker compose exec -T backend pytest -q apps/generation_runner` | `bash scripts/verify-generated-project.sh` | `samples/`, `test_sample_model.py` |
| 4 | Regression + docs | PR 1 | `docker compose exec -T backend pytest -q` | N/A: full suite | `docs/ai/*` |

Baseline: backend 822, spring_generator 317, generation_runner 58.

## Phase 1: RED tests, then the fix (Unit 1)

- [x] 1.1 RED: `backend/apps/spring_generator/tests/test_inheritance_context.py`: `build_inheritance_hierarchy_context` with uuid-hex class ids (digit-leading) and values `Vehicle/Car/Truck` yields subclass names `Car`/`Truck`.
- [x] 1.2 RED: same file: id-independence; same table with readable vs uuid ids gives equal contexts.
- [x] 1.3 RED: same file: value `"Sports Car"` raises `InvalidJavaIdentifierError`; assert `source_name` (limitation pinned).
- [x] 1.4 RED: `backend/apps/spring_generator/tests/test_project_sources.py`: uuid hierarchy through `generate_project_sources` includes `domain/Car.java` and `domain/Truck.java`.
- [x] 1.5 RED: `backend/apps/spring_generator/tests/test_model_sources.py`: same uuid hierarchy through `generate_model_sources`.
- [x] 1.6 Run the four files: 1.1, 1.2, 1.4, 1.5 fail with `InvalidJavaIdentifierError` (right reason), 1.3 fails with "DID NOT RAISE"; record output.

## Phase 2: GREEN fix (Unit 1)

- [x] 2.1 GREEN: `backend/apps/spring_generator/emit/inheritance_context.py:169` -> `class_name=pascal_case(table.discriminator_values[class_id])` (subscript, not `.get`; DD87).
- [x] 2.2 Rerun 1.6 files: all new tests pass; existing readable-fixture tests may fail on `CAR.java` (expected coupling, fixed in Phase 3).

## Phase 3: Fixture realignment (Unit 2, DD88/DD89)

- [x] 3.1 `test_inheritance_context.py`: values `VEHICLE/CAR/TRUCK/PICKUP_TRUCK` -> `Vehicle/Car/Truck/PickupTruck`; rename `test_subclass_class_names_use_pascal_case_class_id_order` -> `test_subclass_class_names_use_pascal_case_discriminator_value_in_class_id_order`; no assertion weakened.
- [x] 3.2 `test_inheritance_rendering.py`: values at `:20`; `@DiscriminatorValue("CAR")`/`("VEHICLE")` literals -> `("Car")`/`("Vehicle")`.
- [x] 3.3 `test_model_sources.py:48`, `test_project_sources.py:37`, `test_rejections.py:59`: values -> class names; exact paths still `Car.java`/`Truck.java`.
- [x] 3.4 Run `apps/spring_generator`: all green (317 + new).
- [x] 3.5 Confirm `backend/apps/spring_generator/tests/test_inheritance_backward_compatibility.py` (read-only) is unmodified (`git diff` empty) and its SHA-256 snapshot test passes.

## Phase 4: Sample model (Unit 3, DD90)

- [x] 4.1 RED: `backend/apps/generation_runner/tests/test_sample_model.py`: replace `:86` readable-id test with frozen uuid-hex + at least one digit-leading per hierarchy class; delete `:95` docstring test; fails against current sample.
- [x] 4.2 GREEN: `backend/apps/generation_runner/samples/sample_model.py`: frozen uuid4-hex class-id literals (digit-leading for vehicle/car/truck); drop defect docstring; keep 41 files and determinism.
- [x] 4.3 Run `apps/generation_runner`: all green.

## Phase 5: Compile gate (Unit 3, DD91, MANUAL)

- [x] 5.1 Run `bash scripts/verify-generated-project.sh` (read-only): expect `BUILD SUCCESSFUL`, exit 0.
- [x] 5.2 Record command, resolved `GRADLE_IMAGE`, status line, exit code in `openspec/changes/spring-generator-inheritance-subclass-naming/gate-evidence.md` and the verify report.

## Phase 6: Regression (Unit 4)

- [x] 6.1 `pytest -q apps/spring_generator`; report exact total.
- [x] 6.2 `pytest -q apps/generation_runner`; report exact total.
- [x] 6.3 `pytest -q` full backend; report exact new total vs 822.

## Phase 7: Docs (Unit 4)

- [x] 7.1 `docs/ai/NEXT_STEPS.md`: remove the known-defect entry.
- [x] 7.2 `docs/ai/CURRENT_STATE.md`: defect fixed, sample uses uuid ids, accurate counts.
- [x] 7.3 `docs/ai/HANDOFF_LATEST.md`: gate evidence, DD range to DD91, counts.
- [x] 7.4 `docs/ai/DECISIONS_LOG.md`: DD87-DD91.
- [x] 7.5 Create `docs/ai/sessions/2026-09-19-agent-spring-generator-inheritance-subclass-naming.md`.

## Spec coverage

Uuid-hex scenario: 1.1, 1.4, 1.5, 5.1. Id-independence: 1.2. Invalid identifier: 1.3. Annotation scenarios: 3.2. Non-regression: 3.5.

Total: 26 tasks (P1 6, P2 2, P3 5, P4 3, P5 2, P6 3, P7 5). Sequential; RED before GREEN is mandatory.
