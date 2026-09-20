# Apply Progress: manifest-generation-profile

Mode: Strict TDD, hybrid store, tests run in Docker (`docker compose exec -T backend pytest -q ...`). Status: 23/24 tasks done; 11.4 is archive-time and stays pending. Applied, verify pending; nothing committed or staged.

## Test counts

| Scope | Before | After |
|---|---|---|
| `apps/domain_manifest` | 88 | 125 (+37) |
| backend full suite | 1070 | 1107 (+37) |
| `apps/relational_mapping` + `apps/generation_runner` | n/a | 208 passed |
| tripwires + decoupling (`test_sample_entity_header`, `test_sample_attribute`, `test_determinism`, `test_builder_decoupling`) | green | 39 passed, unedited |

## TDD Cycle Evidence

| Task | RED evidence | GREEN evidence | Refactor |
|---|---|---|---|
| 1.1 / 1.2 | `test_manifest_error_lives_in_errors_and_is_re_exported`: `ImportError: cannot import name 'errors'` | `errors.py` created, `manifest.py` imports it; domain_manifest 89 passed | Dropped the DD131 claim from the `manifest.py` docstring |
| 2.1 / 2.2 | `test_profile.py`: `ModuleNotFoundError: ...builder.profile` (collection error) | `profile.py` created; 22 passed | None |
| 3.1 / 3.2 | `test_attributes.py`: `ImportError: cannot import name 'attribute_name'` (collection error) | `attribute_name` + column profile attached; domain_manifest all green except the DD131-era neutrality test (retargeted in 6.1) | None |
| 4.1 / 4.2 | 8 failed (`KeyError: 'profile'`, no `ManifestError` raised) | `_resolver` + table profile attached; 123 passed except the neutrality test | None |
| 5.1 | Passes by construction (guard narrowed, sort_keys already alphabetical, schemaVersion already 1); RED proof = mutation M9 | 34 passed in `test_manifest.py` | None |
| 6.1 | Passes by construction after 4.2 (the old assertion failed once emission landed: `AssertionError` at `test_profile_output_neutral.py:30`); RED proof = M1/M2/M9 | 123 passed | Dropped the private-helper import in favour of `to_json_text` |
| 7.1 | Passes by construction (nothing wires `crud` into `_operations`); RED proof = M10 (`test_declaring_crud_does_not_filter_the_operations` fails) | 125 passed | None |
| 8.1 | Passes by construction; determinism guarded by the no-`id` and byte-equality assertions | 125 passed | None |

## Phase 9: mutation checks (each reverted, `apps/domain_manifest` re-run green: 125 passed)

| Mutant | Result | Caught by |
|---|---|---|
| M1 truthiness instead of `is not None` | 9 failed | `test_a_declared_false_is_still_emitted`, `test_build_column_profile[false cases]`, entity profile tests |
| M2 `or None` dropped | 6 failed | `test_an_absent_or_empty_column_profile_adds_no_key`, `test_build_*_profile` empty cases |
| M3 `profile is None` guard dropped | 125 passed (survives) | Equivalent mutant: `getattr(None, field, None)` already yields `None`, so the guard is redundant in both builders. Kept verbatim as pinned by the design |
| M4 `_text` returns the member | 3 failed | `test_crud_is_a_list_of_plain_strings_in_declared_order`, `test_default_sort_shape_and_plain_string_direction[asc/desc]` |
| M5 `crud` re-sorted | 1 failed | `test_crud_is_not_re_sorted` |
| M6 resolver returns `column.name` | 1 failed | `test_default_sort_resolves_to_the_emitted_camel_case_attribute_name` |
| M7 `raise` replaced by `return None` | 4 failed | `test_an_unresolvable_default_sort_id_raises_the_exact_error[*]`, `test_a_synthetic_column_id_is_unknown` |
| M8 discriminator exclusion dropped | 1 failed | `...raises_the_exact_error[a-class-type]` |
| M9 `entity` added to `_TABLE_FLAGS` | 3 failed | `test_the_entity_flag_is_never_emitted_even_when_declared`, `test_build_table_profile_flags` |
| M10 `crud` wired into `operations[]` | 1 failed | `test_declaring_crud_does_not_filter_the_operations` |

## Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and result | `docker compose exec -T backend pytest -q apps/domain_manifest` -> 125 passed |
| Runtime harness | N/A: pure in-process dict shaping, no gate (DD150) |
| Rollback boundary | Revert the PR: delete `builder/profile.py`, `builder/errors.py`, `tests/test_profile.py`; restore `manifest.py`, `attributes.py`, `entities.py` and three test modules |

## Read-only boundaries

`git diff --stat -- backend/apps/relational_mapping backend/apps/spring_generator docker-compose.yml scripts` is empty. `.pi/` never touched.

## Size

`git diff --stat` (tracked): 6 files, 261 insertions, 20 deletions. New files: `errors.py` 9, `profile.py` 47, `tests/test_profile.py` 102 = 158 lines. Authored total ~419 added lines (~281 tracked changes + 158 new), roughly 70 production and ~350 test; well inside the 800-line budget, above the ~260-350 forecast because of the triangulated parametrized cases and mutation-proof tests. Docs under `docs/ai/` are extra.

## Deviations and mismatches

- The proposal is stale on `EXCLUDED_KEYS`; DD148 and the spec win (`["aliases", "entity", "generation_metadata"]`).
- M3 is an equivalent mutant (see above); design mutation-check 3 cannot be caught by any test because `getattr` on `None` is already safe.
- Task 11.4 (main spec heading rename and Purpose fix) is archive-time and was not applied: renaming the heading now would leave the old body under the new name until the delta merges.
