```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:68310bd00949bc0ff76c10b57ab88c4c096d1f16aa055a674f82ad3a08a75d7b
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 14/14
scenarios: 36/36
test_command: docker compose exec -T backend pytest -q apps/domain_manifest
test_exit_code: 0
test_output_hash: sha256:5c0b0b6749fd9ff6e890dd13443fa5ed5392dbefd7ed90af27f7b90972e1fae2
build_command: docker compose exec -T backend python -m compileall -q apps/domain_manifest
build_exit_code: 0
build_output_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Verification Report

**Change**: generated-project-domain-manifest
**Version**: N/A (delta specs `domain-manifest-export` new, `generated-project-verification` modified)
**Mode**: Strict TDD

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 31 |
| Tasks complete | 31 |
| Tasks incomplete | 0 |

### Build and Tests Execution
**Build**: passed. There is no compile step for the Python app; `compileall -q apps/domain_manifest` exits 0 with empty output. The Gradle gate (`MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh`, exit 0, BUILD SUCCESSFUL 45s, /v3/api-docs 200, PASS, wrote Postman files and `domain-manifest.json`) was re-run by the orchestrator and is not re-run here; it is recorded in `gate-evidence.md`.

**Tests**: 87 passed / 0 failed / 0 skipped for `apps/domain_manifest` (re-run here, 2 runs, exit 0). Full backend suite 987 passed (900 + 87) as re-run by the orchestrator.

**Coverage**: not available (no coverage tool configured; not a failure).

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD evidence reported | WARNING | apply-progress (Engram #721) is a prose summary with NO "TDD Cycle Evidence" table. `tasks.md` shows RED then GREEN task pairs (2.1/2.2 ... 8.1/8.2) all checked, and the session note says "RED/GREEN pairs", but per-task RED/GREEN/TRIANGULATE/SAFETY NET columns do not exist |
| All tasks have tests | OK | 6 test modules with tests plus `__init__`, one per code task group |
| RED confirmed (tests exist) | OK | all test files verified on disk |
| GREEN confirmed | OK | 87/87 pass on execution |
| Triangulation adequate | OK | parametrized tables with several expected values per behaviour (types, sample entities, oneToOne true/false, enum ordering, exit codes) |
| Safety net for modified files | OK | only `settings.py` (1 line), compose and script were modified; full suite 987 green |

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit / offline integration | 87 | 6 | pytest (CLI cases via subprocess) |
| E2E / manual | gate | 1 | `verify-generated-project.sh` (recorded) |

### Assertion Quality
| File | Line | Assertion | Issue | Severity |
|------|------|-----------|-------|----------|
| `test_manifest.py` | ~123 | `assert issubclass(ManifestError, ValueError)` | Class-level check that never runs the builder; the `pytest.raises(ValueError)` above it is the real assertion | WARNING (minor) |
| `test_determinism.py` | ~40 | `assert check(tmp_path) is True` over a lambda table | Real behaviour is exercised, but failures report only the id, not the differing values | SUGGESTION |
| `test_cli.py` | ~57 | out-dir `blocker/docs` | Spec scenario says `--out-dir` IS an existing regular file; the test uses a child of a file (the manual gate negative check also used a child). The literal scenario was run by hand here: `error: [Errno 17] File exists`, exit 1 | WARNING (minor) |

No tautologies, no ghost loops (the loop in `test_envelope_and_ordering` iterates an entities list already asserted to hold 6 names; `test_undeclared_facts_are_never_emitted` asserts `resourcePath` is present so the scan provably walked the tree), no smoke-only tests, no mocks.
**Assertion quality**: 0 CRITICAL, 2 WARNING (minor).

### Spec Compliance Matrix
Tags: [pytest] automated, [manual] recorded gate run.

**domain-manifest-export**
| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| Derivation and Purity | Same model, equal output | [pytest] `test_determinism.py > test_determinism_check[equal dicts / no volatile key]` | COMPLIANT |
| Derivation and Purity | Names follow the generator | [pytest] `test_manifest.py > test_sample_entity_header`, `test_attributes.py > test_sample_attribute` (names Customer, fullName, /api/customers come from `emit.naming`) | COMPLIANT |
| Envelope and Schema Version | Version and top-level keys | [pytest] `test_manifest.py > test_envelope_and_ordering` (schemaVersion int 1, key set) | COMPLIANT |
| Entity Content | Sample entity with attributes | [pytest] `test_manifest.py > test_customer_scenario`, `test_sample_entity_header` | COMPLIANT |
| Entity Content | Many-to-one and N:M | [pytest] `test_relationships.py > test_sample_relationships` (purchase, product_tag), `test_sample_entity_header[product_tag]` | COMPLIANT |
| Entity Content | Hierarchy subtypes | [pytest] `test_sample_entity_header[vehicle]` (Car/Truck + discriminator values), `test_sample_attribute[vehicle doors/payload]` (subtype tag) | COMPLIANT |
| CRUD Operations | Six ordered operations | [pytest] `test_manifest.py > test_operations_exist_exactly_when_the_entity_has_a_controller` | COMPLIANT |
| CRUD Operations | Inheritance entities have no operations | [pytest] same test, vehicle row (operations empty and resourcePath None biconditional). No separate subclass entity exists (DD125/DD126), see WARNING 4 | COMPLIANT |
| Enums | Sample enum | [pytest] `test_enums_are_sorted_by_name_and_keep_value_order_and_labels`, `test_the_enum_attribute_references_a_listed_enum` | COMPLIANT |
| Declared-Facts-Only | Excluded keys absent | [pytest] `test_undeclared_facts_are_never_emitted` x7 keys (six + generation_metadata) | COMPLIANT |
| Declared-Facts-Only | documentation note (requirement text) | [manual] DD131 in `docs/ai/DECISIONS_LOG.md` line 17 (UML vs own-profile split + follow-up), also `NEXT_STEPS.md` | COMPLIANT |
| Ordering and Serialization | Byte-identical runs | [pytest] `test_determinism_check[identical bytes]`, `test_cli.py > test_two_runs_produce_byte_identical_files` | COMPLIANT |
| Ordering and Serialization | Serialization format | [pytest] `[one trailing newline]`, `[no carriage return]`, `[reserialize reproduces]`, `test_serialization_is_sorted_indented_and_keeps_non_ascii` | COMPLIANT |
| Endpoint Drift Guard | Paths match springdoc fixture | [pytest] `test_manifest.py > test_computed_paths_equal_the_paths_springdoc_served` (fixture read-only, 15 paths, both directions via set equality, no vehicles) | COMPLIANT |
| Endpoint Drift Guard | Drift caught | [pytest] same test; verifier in-process mutation check (no file edit): baseline equal True, renamed customer segment equal False, extra served /api/vehicles equal False | COMPLIANT (mutation evidence lives only in this report) |
| CLI Contract | Success | [pytest] `test_cli.py > test_success_creates_the_out_dir_and_writes_only_the_manifest` | COMPLIANT |
| CLI Contract | Write failure | [pytest] `test_unwritable_out_dir_exits_one_with_a_message_and_writes_nothing` (child-of-file case) plus verifier manual run of the literal case (exit 1, error:) | COMPLIANT (see WARNING 5) |
| CLI Contract | Missing argument | [pytest] `test_missing_out_dir_exits_two_naming_the_argument` | COMPLIANT |
| CLI Contract | No Django bootstrap | [pytest] `test_django_setup_trap` (trap plus control) | COMPLIANT |
| App Registration and Decoupling | Import guard | [pytest] `test_builder_scanner_allows_only_the_naming_module` (8 cases), `test_builder_and_serializer_import_only_the_naming_module`, `test_cli_imports_only_its_own_app_and_the_sample_model`, `test_importing_the_builder_loads_neither_django_nor_jinja_nor_the_runner` | COMPLIANT |
| App Registration and Decoupling | Nothing imports the manifest app | [pytest] `test_no_other_app_imports_the_manifest_app` | COMPLIANT |
| App Registration and Decoupling | Registration | [pytest] `test_app_is_registered_right_after_postman_export_without_models_or_migrations` | COMPLIANT |

**generated-project-verification**
| Requirement | Scenario | Evidence | Result |
|-------------|----------|----------|--------|
| Compose Chain Contract | Default up unaffected | [manual] gate-evidence: default services mailpit redis db backend frontend unchanged; stanza has profiles jvm-verify (diff read) | COMPLIANT (manual only) |
| Compose Chain Contract | Failure propagates | [manual] negative check exit 1 recorded; script uses set -e (existing) | COMPLIANT (manual only) |
| Compose Chain Contract | Postman service shape | [manual] unchanged from the previous change; the diff shows no edit to that stanza | COMPLIANT (manual only) |
| Compose Chain Contract | Manifest service shape | [manual] diff read: profile, entrypoint empty, user root, mounts ./backend:/app:ro and generated_project:/generated, literal array, no env_file, no depends_on, no rm -rf | COMPLIANT (manual only) |
| Manual Gate Evidence | Evidence recorded | [manual] `gate-evidence.md`: command, exit 0, BUILD SUCCESSFUL, 201/200/204/404, postman and manifest results, negative exit 1 | COMPLIANT |
| Manual Gate Evidence | Manifest negative check recorded | [manual] `gate-evidence.md`: exit 1, revert with equal sha1; the green gate after revert rests on the orchestrator re-run | COMPLIANT (manual only) |
| Single Gate Command | Compile failure skips later steps | [manual] structural: set -euo pipefail, sequential steps; inherited, not re-executed | COMPLIANT (structural, inherited) |
| Single Gate Command | Smoke failure skips postman and manifest | [manual] structural, inherited | COMPLIANT (structural, inherited) |
| Single Gate Command | All four steps pass | [manual] gate-evidence plus orchestrator re-run exit 0 | COMPLIANT |
| Single Gate Command | Unhandled document shape | [manual] structural, inherited (postman negative B, previous change) | COMPLIANT (structural, inherited) |
| Single Gate Command | Manifest step failure | [manual] negative check exit 1 | COMPLIANT |
| Boot Change Isolation | Generated sources unchanged | [pytest] existing 41-file oracle tests pass in the 987 run; git diff under spring_generator, generation_runner, postman_export is empty | COMPLIANT |
| Boot Change Isolation | No version literal outside versions.py | [pytest] tag, but NO pytest scans domain_manifest (existing scan is postman_export only). Verifier rg 3.1.1 over domain_manifest, compose and scripts: no match | PARTIAL (see WARNING 3) |
| Boot Change Isolation | Default behavior unaffected | [pytest]/[manual] default suite offline (987 green), default services unchanged | COMPLIANT |
| Boot Change Isolation | One-way import boundary | [pytest] `test_no_other_app_imports_the_manifest_app` plus the import-guard tests | COMPLIANT |

**Compliance summary**: 36/36 scenarios have passing runtime or recorded manual evidence; 1 is PARTIAL (version-literal scan not automated for domain_manifest, checked manually). Counts from the spec headings: 14 requirements (10 + 4), 36 scenarios (21 + 15).

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|-------------|--------|-------|
| Builder purity | Implemented | builder and serialize.py import only `apps.spring_generator.emit.naming`; no Django, clock, env or filesystem; the type map is keyed on ColumnType member name, so no relational_mapping import |
| serialize duplicated, deterministic | Implemented | own serialize.py, indent=2, sort_keys=True, ensure_ascii=False, trailing newline, newline LF on open; no postman_export import |
| schemaVersion 1, fixed key set | Implemented | SCHEMA_VERSION = 1; entity keys pinned by ENTITY_KEYS; null never omitted |
| resourcePath null iff operations empty | Implemented | entities.py derives both from one resource_path value |
| Six operations | Implemented | create/findById/update/delete/list/count; POST 201, GET/PUT 200, DELETE 204, list 200, count 200 |
| No searchable/sortable/defaultSort/auditable/readOnly/aliases | Implemented | absent in builder source; keys asserted absent at any depth |
| CLI exit codes 0/1/2 | Implemented | main catches ValueError and OSError -> 1; argparse -> 2; no django.setup; only domain-manifest.json written |
| Registration | Implemented | settings.py adds it right after apps.postman_export; no models, no migrations |
| Compose and gate | Implemented | stanza and step 4 diff reviewed; EXIT trap untouched; no new exit code |
| Isolation | Implemented | empty git diff for spring_generator, generation_runner, postman_export; HEAD is 8bb9fd0; nothing committed; .pi/ untracked as at start |

### Coherence (Design DD121-DD131)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| DD121 new app after postman_export | Yes | |
| DD122 RelationalModel as source | Yes | |
| DD123 naming import only, local oneToOne | Yes | _is_one_to_one restated in 3 lines |
| DD124 serialize duplicated, cli glue | Yes | cli imports only sample_model |
| DD125 ordering, neutral types, subtypes | Yes, spec text differs | code and DD125 sort entities by NAME; the spec says table name (WARNING 1) |
| DD126 resourcePath null iff no operations | Yes | |
| DD127 determinism | Yes | |
| DD128 compose stanza and step 4 | Yes | |
| DD129 drift guard | Yes | fixture read-only; sensitive in both directions (mutation check above) |
| DD130 manual proof for compose/script | Yes | one negative check recorded in gate-evidence.md |
| DD131 declared facts only | Yes | note recorded in DECISIONS_LOG |

### Documentation (grep on disk, not the apply summary)
| Claim | Disk result |
|-------|-------------|
| Test count 987 (900 + 87) | present in CURRENT_STATE, HANDOFF, NEXT_STEPS, gate-evidence; true (87 verified now, 900 baseline) |
| Last commit 8bb9fd0 | HANDOFF line 59 and CURRENT_STATE; matches git log -1 |
| DD121-DD131 numbering | DECISIONS_LOG lines 7-17 (25 added lines), matches design |
| No line says the Domain Manifest is the next step | none found; NEXT_STEPS says Next: sdd-verify, archive, commit; item 16 applied, verify pending is correct now and becomes stale after archive |

### Issues Found
**CRITICAL**: None.

**WARNING**:
1. Spec vs design mismatch: the spec (Deterministic Ordering) says entities are ordered by TABLE name; DD125, `manifest.py` (sorted by `entity["name"]`), the tests and tasks 6.1 use `name`. The design wins, and the sample cannot tell them apart (customer, product, product_tag, purchase, tag, vehicle sorts identically either way). The merged spec at archive MUST be amended to "ordered by entity name".
2. Strict TDD evidence: apply-progress has no "TDD Cycle Evidence" table (strict-tdd-verify treats this as CRITICAL). Downgraded to WARNING because the tests are on disk, meaningful (mutation-sensitive drift guard, trap plus control, 87 green) and `tasks.md` records the RED/GREEN pairs; the gap is process evidence, not product behaviour. The orchestrator may append a short table to apply-progress before archive.
3. Boot Change Isolation, "No version literal outside versions.py": tagged [pytest] but no test scans `domain_manifest` (only `postman_export/tests/test_converter_decoupling.py` scans, and only `postman_export`). Checked manually now (no 3.1.1 in domain_manifest, compose, scripts). Add `domain_manifest` to that scan or retag as [manual].
4. Spec wording drift to fix at archive: the scenarios "Inheritance entities have no operations" and "Hierarchy subtypes" mention a subclass entity, but the model yields one root entity per hierarchy (subclasses are not entities, DD125/DD126); and the spec says enum `{name, values}` while `values` items are `{value, label}` objects (tasks 6.1).
5. Write-failure scenario: the spec says `--out-dir` is an existing regular file; pytest and the gate negative check both use a path UNDER a regular file. The literal case behaves correctly (verified by hand: exit 1, `error: [Errno 17] File exists`) but has no test.
6. Manual-only proof (DD101/DD120) of the compose stanza, script step 4 and default-services scenarios; the only negative-check evidence is `gate-evidence.md` (one check, reverted with equal sha1), and the green gate after the revert rests on the orchestrator re-run. The drift-guard mutation check was not recorded by apply; it is recorded here.
7. Authored size: slice 1 = 811 lines (259 non-test, 552 tests) plus slice 2, roughly 1000 total against the 800 budget; `size:exception` versus split is for the orchestrator at commit time.
8. Minor assertion issues: `issubclass(ManifestError, ValueError)` is class-level only; determinism lambdas report only ids on failure.

**SUGGESTION**:
- At archive, refresh `NEXT_STEPS.md` line 78 and `HANDOFF_LATEST.md` lines 109 and 273 ("applied, verify pending") to done.
- Add a one-line pytest for `--out-dir` equal to a regular file.
- `test_source_has_no_host_port_or_url_literal` regex could false-positive on name:1234 style strings; fine today.

### Verdict
PASS WITH WARNINGS
0 CRITICAL, 8 WARNING, 3 SUGGESTION. 31/31 tasks done, 87 domain_manifest tests and 987 total green, gate exit 0. Archive can proceed once the merged spec amendments (WARNING 1 and 4) are applied.
