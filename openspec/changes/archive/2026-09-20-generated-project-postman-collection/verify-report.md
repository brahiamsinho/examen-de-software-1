```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:30c8ef963b29d0e50f120602174ce98c7f955c0d24a0c72c445404e751e35dbb
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 16/16
scenarios: 36/36
test_command: docker compose exec -T backend pytest -q apps/postman_export
test_exit_code: 0
test_output_hash: sha256:3d3f65ac19825dc1bda59d2f70d976cc95a856f5444cd0776969d1ebff977c3e
build_command: MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh
build_exit_code: 0
build_output_hash: sha256:30c8ef963b29d0e50f120602174ce98c7f955c0d24a0c72c445404e751e35dbb
```

## Verification Report

**Change**: generated-project-postman-collection
**Version**: N/A (delta specs: postman-collection-export NEW, generated-project-verification MODIFIED)
**Mode**: Strict TDD (runner `docker compose exec -T backend pytest -q`)

Note on evidence hashes: `test_output_hash` is the sha256 of the captured output of the focused pytest run executed by this verifier. `build_output_hash` and `evidence_revision` are the sha256 of `gate-evidence.md` (the recorded gate proof); the gate itself (exit 0, BUILD SUCCESSFUL 43s, /v3/api-docs 200, PASS, both Postman files written) was re-run by the orchestrator and not re-run here by design.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 31 |
| Tasks complete | 31 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build (gate)**: Passed (orchestrator re-run: exit 0, BUILD SUCCESSFUL, PASS; gate-evidence.md records the same, plus negative A exit 8 and negative B exit 1)

**Tests**: 60 passed / 0 failed / 0 skipped in `apps/postman_export` (verifier run, exit 0). Full backend suite: 900 passed (verifier re-ran `pytest -q`, 900 passed in 74.76s; equals the orchestrator run; 840 before + 60 new).

**Coverage**: Not available (no coverage tool configured); skipped, not a failure.

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD evidence reported | Yes | apply-progress (Engram #713) has a per-task cycle list with RED/GREEN notes |
| All tasks have tests | Yes | every converter/CLI/guard task in phases 2 and 3 has a test module; phases 1 and 4 are gate-proven by design (DD101) |
| RED confirmed (tests exist) | Yes | 7 test modules exist on disk |
| GREEN confirmed | Yes | 60/60 pass on execution |
| Triangulation adequate | Yes | regex guard triangulation, django.setup trap plus control test, several status codes |
| Safety net for modified files | N/A | only 1 line modified in settings.py; full suite 900 green |

Per-module test counts reported by apply (10+9+8+10+5+6+12 = 60) match the executed total of 60.

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 32 | 4 (examples, requests, environment, determinism) | pytest |
| Integration (offline, real fixture / subprocess) | 28 | 3 (collection_from_real_fixture, cli, converter_decoupling) | pytest + subprocess |
| E2E | 0 | 0 | not applicable (gate is manual, DD101) |
| **Total** | **60** | **7** | |

### Assertion Quality
Reviewed test_cli, test_converter_decoupling and test_collection_from_real_fixture in full and the test name lists of the other four. No tautologies. The one loop over a collection (`test_no_script_sets_variables...`) is guarded by `assert lines`; `test_each_request_has_exactly_one_status_test` asserts `len(requests) == 30` before looping. The django.setup trap is proven live by a control test. **Assertion quality**: 0 CRITICAL, 0 WARNING.

### Spec Compliance Matrix

Tag: [pytest] = passing automated test; [manual] = recorded gate evidence (allowed by the spec for these items).

**postman-collection-export**
| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| Pure Deterministic Converter | Same input, same bytes | [pytest] test_determinism `test_two_conversions_of_the_same_input_are_equal`, `test_serialized_files_are_byte_identical_across_runs`; test_cli `test_two_runs_produce_byte_identical_files` | COMPLIANT |
| Pure Deterministic Converter | No volatile fields | [pytest] test_determinism `test_no_volatile_fields_anywhere`; fixture test `test_no_script_sets_variables_and_no_generated_ids_exist` | COMPLIANT |
| Real Captured Fixture | Fixture drives the suite | [pytest] test_collection_from_real_fixture loads `tests/fixtures/api-docs.json`; offline; docstring carries springdoc 3.1.1 + 2026-09-20 | COMPLIANT |
| Collection Envelope | Envelope fields | [pytest] `test_envelope_has_the_v21_schema_the_document_title_and_no_auth`, `test_the_schema_url_literal_lives_in_exactly_one_place` | COMPLIANT |
| Request URL and Naming | Path variable and base URL | [pytest] test_requests `test_path_variable_becomes_colon_id_with_a_variable_entry`, `test_servers_are_ignored` | COMPLIANT |
| Request URL and Naming | Name is method plus path | [pytest] `test_name_is_method_plus_path_and_ignores_operation_id`; fixture test items sorted and named | COMPLIANT |
| Folders and Ordering | Tag folder | [pytest] `test_one_sorted_folder_per_controller_tag` | COMPLIANT |
| Folders and Ordering | Untagged operation and order | [pytest] `test_untagged_operations_land_in_the_default_folder...`, `test_order_does_not_depend_on_the_input_order` | COMPLIANT |
| Body Example Generation | Body from schema | [pytest] `test_post_bodies_and_path_variables_come_from_the_real_schemas` (fullName string), test_examples scalar/format/enum/array/object/ref | COMPLIANT |
| Body Example Generation | Cyclic schema terminates | [pytest] test_examples `test_self_referencing_schema_terminates_at_the_depth_limit` | COMPLIANT |
| Pageable Expansion | Pageable expanded | [pytest] `test_paged_lists_expand_pageable_and_other_requests_have_no_query`, test_requests `test_pageable_ref_parameter_is_expanded...` | COMPLIANT |
| Status-Code Test | Test per request | [pytest] `test_each_request_has_exactly_one_status_test_on_its_lowest_2xx_code` (30 requests, 200/201/204) | COMPLIANT |
| Status-Code Test | No chaining | [pytest] `test_no_script_sets_variables_and_no_generated_ids_exist` | COMPLIANT |
| Environment File | Default empty | [pytest] test_environment `test_base_url_is_the_only_variable_and_is_empty_by_default` | COMPLIANT |
| Environment File | Value supplied | [pytest] `test_base_url_carries_the_supplied_value`, `test_the_collection_never_carries_the_base_url_value`, test_cli `test_base_url_lands_only_in_the_environment_file` | COMPLIANT |
| Environment File | No literals in source | [pytest] test_converter_decoupling `test_source_has_no_host_port_or_url_literal_besides_the_schema_url` plus pattern triangulation | COMPLIANT |
| CLI Contract | Success | [pytest] test_cli `test_success_writes_both_files_and_creates_the_out_dir` | COMPLIANT |
| CLI Contract | Bad input | [pytest] missing file, non-JSON, no paths, non-object JSON, odd shape, unwritable out-dir: all exit 1, stderr message, no traceback, no output | COMPLIANT |
| CLI Contract | Usage error | [pytest] `test_missing_arguments_exit_two_naming_the_argument` | COMPLIANT |
| CLI Contract | No Django bootstrap | [pytest] `test_cli_never_calls_django_setup` (+ control test), env stripped of POSTGRES_* | COMPLIANT |
| App Registration and Decoupling | Import guard | [pytest] test_converter_decoupling (AST scan, sys.modules subprocess, no importer, INSTALLED_APPS) | COMPLIANT |

**generated-project-verification**
| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| Boot Smoke Execution | Plain jar not used | [manual] pre-existing behaviour, unchanged by the diff; gate exit 0 boots the bootJar | COMPLIANT (manual) |
| Boot Smoke Execution | Document exported | [manual] gate-evidence: docs/openapi.json 14408 B written, exit 0; smoke diff read | COMPLIANT (manual) |
| Boot Smoke Execution | Export failure | [manual] negative A: exit 8, no PASS; sha1 revert proven | COMPLIANT (manual) |
| Boot Smoke Execution | Export ordering | [manual] diff read: mkdir and cp are the last statements before the PASS log, after both needle case checks, no _http call between (pytest cannot reach scripts, DD101) | COMPLIANT (manual) |
| Compose Chain Contract | Default up unaffected | [manual] gate-evidence: default services = backend db frontend mailpit redis | COMPLIANT (manual) |
| Compose Chain Contract | Failure propagates | [manual] negatives A and B2 exit non-zero; set -e | COMPLIANT (manual) |
| Compose Chain Contract | Postman service shape | [manual] compose diff read: profile jvm-verify, entrypoint [], no env_file, no depends_on, no rm -rf, literal command array | COMPLIANT (manual) |
| Single Gate Command | Compile failure skips smoke | [manual] set -e and three sequential run --rm lines (diff read); compile path pre-existing | COMPLIANT (manual) |
| Single Gate Command | Smoke failure skips postman | [manual] negative A (smoke exit 8) stops the gate before generate-postman | COMPLIANT (manual) |
| Single Gate Command | All three steps pass | [manual] orchestrator re-run exit 0, both files written | COMPLIANT (manual) |
| Single Gate Command | Unhandled document shape | [manual] negative B2: gate exit 1 from the third step; also [pytest] odd-shape CLI test exit 1 | COMPLIANT |
| Manual Gate Evidence | Evidence recorded | [manual] gate-evidence.md has command, exit 0, BUILD SUCCESSFUL, 201/200/204/404, export, generate-postman result and names, negatives 8 and 1, provenance | COMPLIANT (manual) |
| Boot Change Isolation | Generated sources unchanged | git status/diff: nothing under backend/apps/spring_generator or generation_runner touched; existing suites green (900) | COMPLIANT |
| Boot Change Isolation | No version literal outside versions.py | [pytest] `test_source_never_restates_the_springdoc_version` for postman_export; rg for 3.1.1 over generation_runner source, docker-compose.yml, scripts: no match (only an existing generated build.gradle assertion inside a generation_runner test) | COMPLIANT |
| Boot Change Isolation | Default behavior unaffected | pytest runs offline with no JVM or network; compose default services unchanged | COMPLIANT |

**Compliance summary**: 36/36 scenarios compliant (21 pytest-backed for postman-collection-export; 15 for generated-project-verification, of which 11 rely on recorded manual gate evidence as the spec allows via [manual] tags).

### Correctness (Static Evidence)
| Item | Status | Notes |
|------|--------|-------|
| Converter purity, stdlib only | Yes | imports limited to json, re, argparse, sys, pathlib, collections.abc; no random, uuid, datetime or time usage (rg clean) |
| Determinism recipe | Yes | json.dumps with indent 2, sort_keys, ensure_ascii False plus trailing newline; open with newline set to LF; folders and items sorted; no ids |
| Schema URL single constant | Yes | only converter/collection.py line 9; enforced by a test |
| No host/port/URL literal | Yes | guarded; environment default is empty string |
| baseUrl only from --base-url | Yes | environment.py only; collection references the variable |
| CLI exit codes | Yes | 0 / 1 (_InputError, OSError) / 2 (argparse); no django.setup; no django import |
| App registered | Yes | settings.py +1 line after apps.generation_runner |
| compose generate-postman | Yes | no depends_on, no rm -rf, literal command array, profile jvm-verify, no env_file |
| Smoke export | Yes | last statement before PASS, die 8 on both mkdir and cp, header row 8 added |
| Gate script | Yes | third run --rm generate-postman; cleanup and EXIT trap unchanged |
| Generator sources unchanged | Yes | no diff in backend/apps/spring_generator or generation_runner; DD72 scan target clean |
| .pi/ untouched, nothing committed | Yes | .pi/ untracked as at start, nothing staged, HEAD still a834ca2 |
| Fixture provenance | Yes | springdoc 3.1.1 + 2026-09-20 in test_collection_from_real_fixture docstring only; not in scanned emit source |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| DD108 relative export path, last before PASS | Yes | |
| DD109 new app, no models | Yes | |
| DD110 stdlib only | Yes | |
| DD111 fixed filenames | Yes | |
| DD112 determinism recipe | Yes | |
| DD113 no depends_on / rm -rf | Yes | |
| DD114 fixture-first | Yes | recorded in apply-progress and design apply-time section |
| DD115 one status test, no chaining | Yes | see WARNING 6 on DD119 |
| DD116-DD118 | Yes | pageable ref resolved; page=0, size=20 constant; fixture untrimmed |
| DD119 no numeric 2xx means no test event | Yes (code + test) | deviates from spec wording, see WARNING 6 |
| DD120 pytest scope | Yes | |

### Issues Found

**CRITICAL**: None.

**WARNING**:
1. Authored size is about 1246 lines (source 363, tests 845, scripts/compose/settings about 38) against the 800-line review budget; the design and tasks forecast of about 670 undercounted tests. Needs a size:exception acceptance or a split before commit (orchestrator to ask the user).
2. The collection was never imported into the real Postman application (recorded as Not run in gate-evidence); v2.1.0 conformance is by shape only.
3. Path-level parameters (defined on the path item, not the operation) are not merged into requests. The sample springdoc document does not use them, so no test and no gate observes the gap; a document that declares path variables there would lose the variable entries.
4. sort_keys orders the event key before name inside items. Valid JSON and tolerated by Postman, but unusual to read; a documented consequence of DD112.
5. Both negative checks (exit 8 on an unwritable export path, exit 1 on a corrupted export) are gate-evidence only; there is no automated guard for the smoke export ordering, die 8 or the compose stanza (accepted by DD101 and DD120).
6. Spec wording vs DD119: the Status-Code Test requirement says each request MUST carry one test event, while DD119 (code plus a synthetic test) emits none when no numeric 2xx is documented. The design records the deviation but the spec text was not amended; fix the wording at archive.
7. Minor doc staleness: docs say about 1220 authored lines while the measured total is about 1246 (apply-progress says about 1244); docs/ai/NEXT_STEPS.md line 74 still says 822 backend tests (pre-existing text about an older slice, not this change).

**SUGGESTION**:
1. The CLI writes the collection before the environment: if the second write fails, a lone collection file remains. Consider serializing both in memory first, or removing the first file on failure.
2. The _convert wrapper catches AttributeError, KeyError, TypeError and ValueError broadly; acceptable for the exit-1 contract (the exception type is reported), but add a malformed-shape test per branch if the converter grows.
3. Add a schema validation or Postman import step as a follow-up to close warning 2.
4. Docs cross-checks that passed on disk: DD108-DD120 present in DECISIONS_LOG; last commit a834ca2 is correct; tests 900 = 840 + 60 correct; DD numbering consistent (DD103-DD107 springdoc, DD108-DD120 this change).

### Verdict
PASS WITH WARNINGS

All 31 tasks complete, 60 focused tests and the 900-test full suite green, converter and gate wiring match spec and design; no CRITICAL findings. Warnings: size budget (needs size:exception), no real Postman import, path-level parameters not merged, key ordering, gate-only negative checks, DD119 vs spec wording, minor doc staleness.
