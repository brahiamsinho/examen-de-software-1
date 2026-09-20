# Apply Progress: relational-generation-metadata

Mode: Strict TDD, hybrid store. 34/34 tasks complete (all `[x]` in `tasks.md`). Verify pending. Not committed, not staged.
Test command: `docker compose exec -T backend pytest -q <path>`.

## TDD Cycle Evidence

| Task | Test file | RED evidence | GREEN evidence |
|------|-----------|--------------|----------------|
| 1.1 / 1.2 | `relational_mapping/tests/test_profile.py` | collection error `ModuleNotFoundError: domain.profile` | 7 passed |
| 2.1 / 2.2 | `test_profile_parser.py` (error tests) | `ImportError: InvalidGenerationProfileError` | 3 passed |
| 3.1 / 3.2 / 3.3 | `test_profile_parser.py` | collection error (`profile_parser` missing) | 54 passed (60 with `test_profile.py`); extra `["asc"]` case pins the unhashable-direction path; two-fault test pins numeric rule order (resolution C) |
| 4.1 / 4.2 | `test_schema.py` | 4 failed, 8 passed (`AttributeError`/`TypeError`, no `profile` field) | `apps/relational_mapping` 121 passed |
| 5.1 | `test_map_profiles.py` | 10 failed, 3 passed (3 pass trivially: undeclared, subclass-only entry, synthetic columns; protected by mutations 2 and 5) | see 5.2-5.4 |
| 5.2 / 5.3 / 5.4 | `test_map_profiles.py` | (5.1) | `apps/relational_mapping` 134 passed |
| 5.5 | `test_determinism.py` | characterization test, passes by construction (resolution D); protected by mutation 3 (fails) | 5 passed |
| 6.1 | `test_profile.py` (AST guard) | passes by construction; proven able to fail: `import django` in `profile.py` + `domain.model` import in `parser` -> 2 failed, 135 passed; reverted | 9 passed |
| 7.1-7.7 | mutation checks | M1 (bool check weakened): rule-4 cases + 3 mapper tests red. M2 (STI any-class): 2 red. M3 (empty instance not `None`): 12+ red. M4 (no crud canonical order): 2 red. M5 (profile on `id`, `class_type`, FK column): 1 red each. M6a (raise outside `profile`): 4 red; M6b (ignore unknown inside): rule-3 cases red. M7a/M7b (drop element id / key from message): 3 and 5+ red | all reverted; `apps/relational_mapping` 137 passed |
| 8.1 | `generation_runner/tests/test_profile_output_neutral.py` + `domain_manifest/tests/test_profile_output_neutral.py` | characterization (passes by construction); non-vacuous: asserts profiles are present on tables/columns | 3 + 1 passed |

Final verification (8.2-8.7):

- `apps/relational_mapping`: 137 passed
- `generation_runner/tests/test_sample_model.py`: 8 passed (41 files, unchanged)
- `spring_generator/tests/test_inheritance_backward_compatibility.py`: 1 passed (sha256 goldens unchanged)
- `apps/domain_manifest`: 88 passed including its neutrality test file (the Spring half lives in `apps/generation_runner`; no expectation edited)
- Full backend suite: **987 passed before, 1069 passed after** (+82 new tests)
- `git diff --stat`: no change in `domain_manifest/`, `spring_generator/`, `uml_modeling/` sources; no oracle test file edited.

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `pytest -q apps/relational_mapping` -> 137 passed |
| Runtime harness | sample model mapped with and without profiles; Spring sources and manifest identical (neutrality tests) |
| Rollback boundary | delete `profile.py`, `profile_parser.py`, the new test files; revert `schema.py`, `errors.py`, `mapper.py` and the two edited tests |

## Authored size (budget 800; over budget)

| Part | Lines |
|---|---|
| Modified tracked files (`git diff --numstat`, backend) | 129 |
| New files (backend, `wc -l`) | 827 |
| Backend code + tests total | 956 |
| of which non-test source | 265 (`profile.py` 58, `profile_parser.py` 139, `mapper.py` 48, `errors.py` 17, `schema.py` 3) |
| of which tests | ~691 |
| Docs (`docs/ai` + session note + design note) | ~47 |

Exceeds the 800 budget and the ~600 stop threshold. Cause: triangulated table-driven tests (54 parser cases, mapper scenarios) mandated by Strict TDD. Not compressed to fit. Recommend `size:exception`.

## Deviations from design / findings

1. `Table` is unhashable (pre-existing `discriminator_values` is a `MappingProxyType`), so tasks 4.1 / 5.5 hash `Column` and `Table.profile` instead of `Table`.
2. Task 8.1: a guard (`domain_manifest/tests/test_builder_decoupling.py`) forbids any other app importing `apps.domain_manifest`, so the manifest neutrality test lives in `domain_manifest/tests/test_profile_output_neutral.py`; the Spring half is at the confirmed runner path.
3. `InvalidGenerationProfileError` is not imported into `mapper.py` (design wiring table lists it, but the mapper never references it).
4. `_collect_profiles` takes `attribute_owner_by_id` (resolution A); numeric rule order note added to `design.md` (resolution C).
