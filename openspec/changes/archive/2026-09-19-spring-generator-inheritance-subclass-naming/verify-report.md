```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:3dbcc602be0b301930e295d1aaa5e2fc193ea4fec6ba87d9766d71969ef3ea12
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 2/2
scenarios: 7/7
test_command: docker compose exec -T backend pytest -q
test_exit_code: 0
test_output_hash: sha256:18af2a12386d07b96a494fb78bacbbb3b848185fd00e4f7d0b384084a916aecf
build_command: bash scripts/verify-generated-project.sh
build_exit_code: 0
build_output_hash: sha256:e9523c214f5700a219f291296c434874ba0bb7e7f9d08a211275bb544635e1fc
```

## Verification Report

**Change**: spring-generator-inheritance-subclass-naming
**Version**: N/A (delta on spring-boot-generation)
**Mode**: Strict TDD

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 26 |
| Tasks complete | 26 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build** (manual compile gate, DD91): PASSED

    bash scripts/verify-generated-project.sh
    GRADLE_IMAGE=[gradle:9.7.1-jdk21]
    BUILD SUCCESSFUL in 43s  (5 actionable tasks: 5 executed)
    exit=0

Apply saw one transient Maven Central TLS handshake failure on its first run (exit 1, jackson-databind download); the immediate rerun and this verify run are green. Infrastructure flake, not a code failure.

**Tests**: 828 passed / 0 failed / 0 skipped

    docker compose exec -T backend pytest -q                        -> 828 passed (baseline 822, +6)
    docker compose exec -T backend pytest -q apps/spring_generator  -> 322 passed (baseline 317, +5)
    docker compose exec -T backend pytest -q apps/generation_runner -> 59 passed  (baseline 58, -2 +3)
    test_inheritance_backward_compatibility.py + test_no_concat_guard.py -> 3 passed

**Coverage**: Not available (no coverage tool configured for this run).

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD evidence reported | Pass | apply-progress (#688) records RED and GREEN evidence; free-form, not the tabular format |
| All tasks have tests | Pass | fix, fixtures and sample all covered by test files that exist |
| RED confirmed | Pass | 5 new tests: 4x InvalidJavaIdentifierError, 1x DID NOT RAISE; sample: 2 RED tests. Reasoned independently below |
| GREEN confirmed | Pass | all named tests pass on execution now |
| Triangulation adequate | Pass | uuid ids, id-independence, invalid value: three distinct behaviors |
| Safety net for modified files | Pass | 4 old fixtures failed as expected on CAR vs Car and were realigned; snapshot test untouched |

RED reasoning against the old code pascal_case(class_id): with digit-leading uuid ids every uuid test (context, generate_project_sources, generate_model_sources) raises InvalidJavaIdentifierError; the id-independence test raises on the uuid side; the Sports Car test never raises because the old code read the class id car, giving DID NOT RAISE. Each new test therefore fails on the old code and passes on the new one.

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Discriminator-Backed Single Table Domain Generation | Supported discriminator table yields root, subclasses, root repository | test_inheritance_rendering.py subclass/root-file tests; test_project_sources.py > test_uuid_id_hierarchy_emits_subclass_files_named_after_the_uml_class_names | COMPLIANT |
| Discriminator-Backed Single Table Domain Generation | Actual discriminator column name is used as metadata | test_inheritance_rendering.py custom-discriminator-column test (unchanged, passing) | COMPLIANT |
| Discriminator-Backed Single Table Domain Generation | Uuid-hex class ids generate subclasses named from the UML class name | test_inheritance_context.py > test_uuid_digit_leading_class_ids_yield_class_names_from_discriminator_values; test_project_sources.py and test_model_sources.py > test_uuid_id_hierarchy_emits_subclass_files_named_after_the_uml_class_names; test_sample_model.py > test_generated_hierarchy_files_are_named_after_the_uml_classes_not_their_ids; compile gate | COMPLIANT |
| Discriminator-Backed Single Table Domain Generation | Subclass name does not depend on the class id | test_inheritance_context.py > test_hierarchy_context_is_independent_of_the_class_id_scheme (context equality, not rendered bytes) | PARTIAL (see S1) |
| Discriminator-Backed Single Table Domain Generation | Class name that is not a valid Java identifier is rejected | test_inheritance_context.py > test_discriminator_value_that_is_not_a_java_identifier_is_rejected_with_its_source_name (Sports Car, asserts source_name) | COMPLIANT (builder level) |
| Root and Subclass JPA Inheritance Annotations | Root entity contains Single Table metadata | test_inheritance_rendering.py > test_root_entity_contains_single_table_metadata_and_is_concrete (DiscriminatorValue Vehicle) | COMPLIANT |
| Root and Subclass JPA Inheritance Annotations | Subclass entity extends the root and declares its discriminator value | test_inheritance_rendering.py > test_subclasses_extend_root_and_partition_fields (DiscriminatorValue Car, extends Vehicle, no id redeclared) | COMPLIANT |

**Compliance summary**: 6/7 fully compliant, 1 partial (no failing or untested scenario).

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Subclass name = pascal_case(Table.discriminator_values[class_id]) | Implemented | Sole production change, emit/inheritance_context.py:169; subscript, not .get; the diff is exactly one line |
| Root name stays pascal_case(Table.name) | Implemented | inheritance_context.py:137 untouched |
| InvalidJavaIdentifierError kept | Implemented | raised by pascal_case; pinned by test |
| No other place derives a Java name from a class id | Verified | grep of emit/: pascal_case call sites take table/column/enum/FK names; the only class_id uses are ownership partitioning and dictionary lookups |
| Fixture realignment did not weaken tests | Verified | git diff of tests shows only value/literal changes (CAR to Car etc.), one test rename, added tests; only the intended sample_model tests were removed |
| Sample model | Verified | 7 frozen uuid4-hex literals, vehicle/car/truck digit-leading, 41-file and determinism tests intact, workaround docstring gone |
| Backward-compat snapshot | Verified | empty git diff, passes |
| Working tree | Verified | only the 12 intended modified files plus the new session note and change folder; .pi/ untracked; no BOM in any edited .py or .md file |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| DD87 inline subscript fix at :169 | Yes | |
| DD88 fixtures use verbatim class names as discriminator values | Yes | test_rejections.py:59 realigned (task 3.3) |
| DD89 discriminating coverage in new uuid-id tests | Yes | old fixtures keep readable ids |
| DD90 frozen uuid4-hex literals in the sample | Yes | |
| DD91 manual compile gate as end-to-end evidence | Yes | re-run by verify: BUILD SUCCESSFUL, exit 0 |

### Docs accuracy (docs/ai)
Counts 828/322/59 match the executed results; DD87-DD91 present in DECISIONS_LOG; the known-defect section is removed from NEXT_STEPS; every doc and the session note state applied, NOT yet verified, archived or committed, which is true at verify time and claims nothing more. These statements will need updating after verify/archive.

### Issues Found
**CRITICAL**: None

**WARNING**:
- W1: test_rejections.py:146-179 keeps root-only VEHICLE fixtures. Verified intentional and harmless: those tests hit reject_out_of_scope malformed-table branches and never name a subclass. Mild inconsistency with DD88; reasonable to keep.
- W2: The compile gate first run in apply failed with a transient Maven Central TLS error. Not code-related; the gate depends on network availability.

**SUGGESTION**:
- S1: The id-independence and invalid-identifier scenarios name generate_table_sources in the spec, but the tests exercise build_inheritance_hierarchy_context (context equality and the builder raising). Equivalent in practice because generate_table_sources calls the builder; a public-API-level byte-equality test would match the spec text literally.
- S2: apply-progress reports TDD evidence as prose rather than the tabular TDD Cycle Evidence format; acceptable, but a table would make future verifies mechanical.

### Verdict
PASS WITH WARNINGS
Zero critical findings: all 26 tasks done, the one-line fix matches the spec and design exactly, 828/322/59 tests and the compile gate pass, and the new tests genuinely discriminate id from value.
