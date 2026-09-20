# Apply Progress: uml-generation-profile-authoring (backend)

Mode: Strict TDD. Store: hybrid. Status: DONE, 31/31 tasks (Phases 1-6); applied, verify pending. `size:exception` accepted by the orchestrator (standing user choice; see Size).

## Counts

| Scope | Before | After |
|-------|--------|-------|
| Backend full suite | 1107 passed | 1184 passed (+77) |
| `apps/uml_commands` | n/a | 86 passed |
| `apps/uml_documents` | n/a | 134 passed |
| `relational_mapping` + `domain_manifest` + `spring_generator` | n/a | 588 passed |

## TDD Cycle Evidence

| Task | RED evidence | GREEN evidence | Refactor |
|------|--------------|----------------|----------|
| 1.1 | `rg` sweep found 3 pinned counts (test_commands, test_dispatcher, uml_documents test_schemas); re-swept after edits, no others | n/a | none |
| 1.2 / 1.3 | `ImportError: cannot import name 'SetGenerationProfile'` (collection error) | `test_commands.py` 22 passed | none |
| 1.4 / 1.5 | `ModuleNotFoundError: ...handlers.generation_profile` | 14 passed | none |
| 1.6 / 1.7 | `ImportError: cannot import name 'prune_generation_metadata'` | `apps/uml_commands` 85 passed | none |
| 1.8 / 1.9 | `KeyError: SetGenerationProfile` + registry pin 9 != 10 (2 failed, 12 passed) | `apps/uml_commands` 86 passed | none |
| 2.1 / 2.2 | `AttributeError: schemas has no SetGenerationProfileIn` | `test_schemas.py` 23 passed | none |
| 2.3 / 2.4 | 6 failed (NameError on `_ALLOWED_EXACT_MODULES` / helper) | `test_import_boundary.py` 7 passed; exact-match `return` sits before both assertions (R3) | assertions extracted into `_assert_import_allowed` |
| 2.5 / 2.6 | 3 failed (`Unknown command payload type`) | 3 passed | none |
| 2.7 / 2.8 | 14 failed, `DID NOT RAISE` (6 characterization cases passed) | `apps/uml_documents` + `apps/uml_commands` 208 passed | none |
| 2.9 | characterization (passes at once, R5); proven by mutation S1 | 8 passed | none |
| 3.1 | characterization (passes at once, R5); proven by mutation S3 | `test_api.py` 21 passed | none |
| 3.2 | characterization (passes at once, R5); proven by mutations S3/M5 | 3 passed | none |
| 4.1 / 4.2 | see mutation table | all mutants killed, every file restored (`cmp` clean), affected apps re-run green | none |
| 5.1 | n/a | see Counts | none |
| 5.2 | n/a | `git diff --stat` empty for `frontend/`, `apps/uml_modeling`, `apps/relational_mapping`, `apps/spring_generator`, `apps/domain_manifest`, `docker-compose.yml`, `scripts/` | none |

Note: cascade tests in task 1.6 shared the collection-error RED with the prune tests; they were not individually red before 1.7. Mutation M5 proves them.

## Mutation checks (all reverted)

| Mutant | Killed by |
|--------|-----------|
| M1 sibling replace | 5 handler table cases (`set-preserves-sibling-keys`, ...) |
| M2 `is not None` | `empty-mapping-removes-only-profile` |
| M3 no pruning | `clear-prunes-the-entry-when-it-becomes-empty`, `test_clearing_an_absent_profile_returns_the_same_model` |
| M4 DD155 inverted | `test_unknown_element_id_is_rejected_even_when_clearing[None]`, `[{}]` |
| M5 DD158 narrowed | `test_remove_class_clears_a_foreign_root_default_sort_on_a_removed_descendant_attribute` |
| M6 DD157 widened | 3 `test_default_sort_rejects_attributes_outside_the_allowed_set` cases |
| M7 DD157 narrowed | `[root-child_attr]` resolves case and `[root-other_attr]` message case |
| M8 validate after apply | `test_a_rejected_profile_is_validated_before_apply_runs` (spy on `apply`; added because `transaction.atomic` rolls the row back either way) |
| M9 generic message | 8 parser-message cases + API 422 case |
| M10 handler raises | 3 `test_unknown_element_id_returns_the_model_unchanged...` cases |
| S1 `def remove_class` in schemas.py | `test_command_semantics_stay_in_uml_commands` |
| S2 `mapper` import in services.py | `test_no_disallowed_imports_exist` |
| S3 gate removed from `submit_command` | API 422 + unknown-id cases |

Equivalent variant: the "outside the lock" half of design mutation 8 cannot be observed single-threaded; only the "after apply" half is testable.

## Size (authored, additions + deletions)

| Bucket | Lines |
|--------|-------|
| Modified tracked files | 620 added + 22 deleted = 642 |
| New: `handlers/generation_profile.py` | 99 |
| New: `tests/test_generation_profile.py` | 305 |
| New: `tests/test_generation_profile_integration.py` | 162 |
| **Total code (without docs)** | **~1208** (source ~221, tests ~987) |
| Phase 6 docs (`docs/ai` x5 incl. new session note, `design.md` patch, tasks, this file) | ~75 (dense lines) |
| **Total including docs** | **~1283** |

Design estimate was ~525 and the change budget 800. Overrun is almost entirely tests (design estimated ~310 test lines). Largest overruns: `test_generation_profile.py` 305 vs ~110, `test_services.py` +206 vs ~70, integration 162 vs ~60, `test_api.py` +119 vs ~40, `test_import_boundary.py` +103 vs ~12. Tests were not trimmed to fit (never compress tests for budget). `size:exception` was accepted by the orchestrator (confirmed standing user choice), Phase 6 then ran.

## Deviations / findings

- R1 applied: services import only `apps.relational_mapping.mapping.profile_parser` (incl. `InvalidGenerationProfileError`); design snippet importing `mapping.errors` is superseded (task 6.2 done: the design snippet now imports `InvalidGenerationProfileError` from `profile_parser`).
- `test_import_boundary.py`: the loop body was extracted into `_assert_import_allowed(source_name, target)` so the synthetic-target tests can reuse it (design showed a loop `continue`; semantics identical, the exact-match return precedes both assertions).
- `_validate_generation_profile`: the wrapped `try` also covers the column-level `parse_column_profile` early return (design listed it inline); behavior identical.
- Tooling: host has no `python`/`sd`/`rg` in Git Bash; edits done with the Edit tool and perl.

## Remaining

- [x] 6.1 DECISIONS_LOG DD151-DD159
- [x] 6.2 design.md R1 patch + DD confirmation (DD151-DD159 present in both the log and design.md)
- [x] 6.3 CURRENT_STATE
- [x] 6.4 HANDOFF_LATEST
- [x] 6.5 NEXT_STEPS
- [x] 6.6 session note (`docs/ai/sessions/2026-09-20-agent-uml-generation-profile-authoring.md`)
- [x] 6.7 archive reminder (already covered by tasks.md text; no code)

Nothing remains for apply; next is `sdd-verify`.
