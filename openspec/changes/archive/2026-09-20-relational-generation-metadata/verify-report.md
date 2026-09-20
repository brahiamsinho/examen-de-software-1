```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:ac5d349a8d7beb79727ce553155cf7a4f591f3a34d024e66d95da5b4bcc1194b
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 16/16
scenarios: 59/59
test_command: docker compose exec -T backend pytest -q
test_exit_code: 0
test_output_hash: sha256:c84520466abe62a882e7e53b484f156206faa102fb44c32458874bea33adf3b0
build_command: docker compose exec -T backend python manage.py check
build_exit_code: 0
build_output_hash: sha256:1e3e63f221bde88816c4a4ef7367691607b20cc1d194028a02ec9ae0586cf9b1
```

## Verification Report

**Change**: relational-generation-metadata
**Version**: N/A (delta specs: `generation-profile` new, `relational-mapping` delta)
**Mode**: Strict TDD, hybrid store

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 34 |
| Tasks complete | 34 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build** (Django system check; the project has no compiled build): passed, `System check identified no issues (0 silenced).`

**Tests**: 1069 passed / 0 failed / 0 skipped (full suite, 86.6 s, exit 0). Independent re-runs, all in Docker:

| Command | Result | Apply claim |
|---|---|---|
| `pytest -q` (full) | 1069 passed | 1069 (match) |
| `pytest -q apps/relational_mapping` | 137 passed | 137 (match) |
| `pytest -q apps/generation_runner/tests/test_sample_model.py` | 8 passed (41-file oracle, determinism) | 8 (match) |
| `pytest -q apps/spring_generator/tests/test_inheritance_backward_compatibility.py` | 1 passed | 1 (match) |
| `pytest -q apps/domain_manifest` | 88 passed | 90 (MISMATCH, see WARNING 4) |

**Coverage**: not available (no coverage tool run; informational only).

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD evidence reported | Yes | "TDD Cycle Evidence" table present in apply-progress |
| All tasks have tests | Yes | every implementation task maps to an existing test file |
| RED confirmed (tests exist) | Yes | all listed test files exist on disk |
| GREEN confirmed (tests pass) | Yes | all listed files pass on re-execution |
| Triangulation adequate | Yes | 54 parametrized parser cases, 13 mapper cases; 3 tests pass by construction and are protected by recorded mutation checks (M2, M3, M5) |
| Safety net for modified files | Yes | `test_schema.py` and `test_determinism.py` pre-existed; relational_mapping suite green before and after |

**TDD Compliance**: 6/6.

### Test Layer Distribution
Unit: profile, parser, schema, determinism and mapper tests (the mapper is a pure function, no DB). Integration-like: 3 output-neutrality tests through the real Spring generator and manifest builder. E2E: none (not applicable). Tool: pytest.

### Assertion Quality
No tautologies, ghost loops or orphan-empty assertions. Guards are non-vacuous (`assert imported` in the AST guard; the neutrality tests assert profiles are actually present). **Assertion quality**: 0 CRITICAL, 0 WARNING. The neutrality tests and the determinism test are characterization tests that pass by construction (declared in apply-progress).

### Spec Compliance Matrix
Key: C = COMPLIANT (covering test passed), C* = COMPLIANT WITH CAVEAT (see WARNINGS 1 and 2; counted as complete in the envelope). PP = `relational_mapping/tests/test_profile_parser.py`, PV = `test_profile.py`, MP = `test_map_profiles.py`, SC = `test_schema.py`, DT = `test_determinism.py`, GN = `generation_runner/tests/test_profile_output_neutral.py`, DN = `domain_manifest/tests/test_profile_output_neutral.py`.

**generation-profile** (9 requirements, 33 scenarios)
| Requirement | Scenario | Test | Result |
|---|---|---|---|
| Profile Value Objects | All fields default to undeclared | PV `test_column_profile_defaults_to_undeclared`, `test_table_profile_defaults_to_undeclared` | C |
| | Value objects are frozen | PV `test_column_profile_is_frozen`, `test_table_profile_is_frozen` | C |
| | Equality and hashing are structural | PV `test_equal_table_profiles_are_equal_and_hash_equal` (incl. `{p1} == {p2}`); SC `test_column_with_profile_is_structurally_equal_and_hashable` | C |
| | Module import purity | PV `test_profile_modules_have_zero_framework_imports`, `test_profile_parser_is_model_and_consumer_free` | C |
| Key Vocabulary and Levels | Full table entry parses | PP `test_full_table_entry_parses_with_canonical_crud_and_default_sort` | C |
| | Full column entry parses | PP `test_full_column_entry_parses` | C |
| | Partial entries leave other keys undeclared | PP `test_partial_entries_leave_other_fields_undeclared` | C |
| | Cross-level key raises | PP `test_invalid_entry_raises_...` cases searchable-on-table, crud-on-column | C |
| | aliases, required, unique rejected | PP rule-3 cases `aliases` (table), `required`, `unique` (column) | C |
| None Means Undeclared | Absent key stays None per key | PP `test_partial_entries_leave_other_fields_undeclared` | C |
| | Zero declared keys canonicalizes to None | PP `test_zero_declared_keys_canonicalize_to_none` (3 entries x 2 levels) | C |
| | Undeclared element has no profile | MP `test_undeclared_class_and_attribute_have_no_profile` | C |
| Strict Validation Rules | Rules 1-12 (12 scenarios) | PP `test_invalid_entry_raises_with_exact_key_reason_and_message` (exact key, reason and `str(exc)` per case) | C x12 |
| | Error message with a key | PP `test_error_with_key_message_and_attributes` | C |
| | Error is an UnmappableModelError | PP `test_error_is_an_unmappable_model_error` | C |
| CRUD Canonical Ordering | Input order does not matter | PP `test_crud_input_order_does_not_matter` | C |
| | Empty crud list is declared | PP `test_empty_crud_list_is_declared_not_undeclared` | C |
| defaultSort Is Stored Unresolved | Unresolvable attribute id is accepted | PP `test_unresolvable_default_sort_attribute_is_accepted` (parser only; the "mapped" half was confirmed by an ad hoc runtime check in Docker: `map_to_relational` succeeds and yields `TableProfile(default_sort=DefaultSort(ElementId("no-such-attribute"), ASC))`, no committed test) | C* |
| Entity Key Is Carried | entity false does not change mapping | MP `test_entity_false_still_produces_the_table`; PP `test_entity_false_is_stored` | C |
| Keys Outside profile Ignored | Provenance keys are ignored | PP `test_provenance_keys_outside_profile_are_ignored_even_when_malformed` | C |
| | Unknown element id is skipped | MP `test_unknown_ids_and_malformed_keys_outside_profile_never_raise` | C |
| Parser Purity and Determinism | Same entry, equal result | PP `test_same_entry_parsed_twice_is_equal_and_hash_equal` | C |

**relational-mapping delta** (7 requirements, 26 scenarios)
| Requirement | Scenario | Test | Result |
|---|---|---|---|
| RelationalModel Domain Structure | Domain module has zero framework imports | existing `test_schema.py` import guard (green with the new `profile` import) | C |
| | Profile fields default to None | SC `test_column_defaults`, `test_table_defaults` | C |
| | Profile-carrying values remain hashable | SC column hash test; `Table` cannot be hashed (pre-existing), `test_table_with_profile_is_structurally_equal` asserts `==` and `hash(Table.profile)` only (the `Table` half of the scenario is unsatisfiable, WARNING 1) | C* |
| Class-to-Table Mapping | Simple class becomes a table | existing mapper tests | C |
| | Declared class profile reaches the table | MP `test_declared_class_profile_lands_on_the_table` | C |
| | Undeclared class has no table profile | MP `test_undeclared_class_and_attribute_have_no_profile` | C |
| | STI takes root profile only | MP `test_sti_table_profile_comes_from_the_root_only` | C |
| | Subclass-only class profile sets no table profile | MP `test_subclass_only_class_entry_sets_no_table_profile` | C |
| | Malformed subclass class profile still raises | MP `test_malformed_subclass_class_entry_still_raises_for_the_subclass` | C |
| Attribute-to-Column Mapping | Primitive attribute becomes typed column | existing mapper tests | C |
| | Declared attribute profile reaches the column | MP `test_declared_attribute_profile_lands_on_the_column` | C |
| | Enumeration-typed attribute carries its profile | MP `test_enum_typed_attribute_keeps_its_profile` | C |
| | Undeclared attribute has no column profile | MP `test_undeclared_class_and_attribute_have_no_profile` | C |
| | Subclass-owned attribute keeps profile and owner | MP `test_subclass_owned_attribute_keeps_its_profile_and_owner` | C |
| Deterministic Mapping | Repeated mapping is identical | existing determinism tests | C |
| | Profile-carrying model maps equal and hashes equal | DT `test_profile_carrying_model_maps_equal_with_equal_hashes` (`==` on results; hashes on `Table.profile` and columns only; tables are unhashable, WARNING 1) | C* |
| Profiles Collected Before Table Work | Malformed entry aborts mapping | MP `test_malformed_attribute_profile_aborts_before_any_result` | C |
| | Error catchable as mapper failure contract | same test (`pytest.raises(UnmappableModelError)`) | C |
| | First offending entry wins | MP `test_first_offending_entry_in_metadata_order_is_the_one_reported` | C |
| | Unknown ids and keys outside profile never raise | MP `test_unknown_ids_and_malformed_keys_outside_profile_never_raise` | C |
| Synthetic Columns and Join Tables Carry No Profile | id and discriminator have no profile | MP `test_synthetic_columns_never_carry_a_profile` | C |
| | Foreign-key columns have no profile | same test | C |
| | Join table and its columns have no profile | same test (`join_table.profile is None`; every column with `source_element_id is None`) | C |
| Output-Neutral | Spring oracle unchanged | `test_sample_model.py` (8) and `test_inheritance_backward_compatibility.py` (1), no expectation edited | C |
| | Domain Manifest unchanged | `apps/domain_manifest` 88 passed, no expectation edited | C |
| | Declared profile does not change manifest or oracle output | GN `test_declared_profile_does_not_change_spring_sources`, DN `test_declared_profile_does_not_change_the_domain_manifest` | C |

**Compliance summary**: 59/59 scenarios compliant, of which 3 carry a caveat (C*): two because the spec wording claims `Table` hashability (impossible, pre-existing), one because the mapper-level half is verified only by an ad hoc runtime check, not a committed test. 0 UNTESTED, 0 FAILING. Requirements: 16/16.

### Correctness (Static Evidence)
| Check | Status | Notes |
|---|---|---|
| 12 validation rules, exact messages | Implemented | `profile_parser.py`; every reason string matches the spec table; `str(exc)` formats match (`{element_id!r}`, `{key!r}`); within-entry order is numeric (3, 4, 5-7, 8-12) |
| None means undeclared | Implemented | absent key returns `None`; `body or None` canonicalizes `{}`; `crud: []` stays `()`; JSON `null` raises rule 4 |
| Bool strictness | Implemented | `isinstance(value, bool)`; `1`, `0`, `"true"`, `None` raise |
| CRUD canonical order, duplicates, exact-value membership | Implemented | `_CRUD_ORDER` projection; `"READ"` raises rule 6 |
| STI root-only | Implemented | `draft.profile = table_profile_by_id.get(root_id)`; subclass entries are validated in `_collect_profiles` but never reach `Table.profile` |
| Synthetic columns None | Implemented | `profile=` passed only from `_map_attribute_column` (both branches); `id`, `class_type`, FK and join-table columns and join `Table` keep the default `None` |
| Up-front collection (DD141) | Implemented | `_collect_profiles` runs before `_map_enumerations`, in `generation_metadata` order; unknown ids skipped unvalidated |
| Import purity | Implemented | `profile.py` imports `dataclasses`, `enum`, `ElementId`; `profile_parser.py` adds `collections.abc`, `profile`, `errors`; no forbidden import; AST guard passes and was proven able to fail during apply |
| No source change in `domain_manifest`, `spring_generator`, `uml_modeling` | Confirmed | `git diff --stat` over those dirs is empty; only new untracked `domain_manifest/tests/test_profile_output_neutral.py` (allowed); oracle test files unedited |
| Working tree hygiene | Clean | 5 modified backend files, 4 modified docs, expected new files; no `.orig`/`.rej`; no mutation leftovers (mapper diff is exactly the wiring, suite green); `.pi/` untracked with mtime Sep 19 (present in the initial git status, before this work) |

### Coherence (Design)
| Decision | Followed? | Notes |
|---|---|---|
| DD132 module location | Yes | `domain/profile.py` |
| DD133 tri-state `None` | Yes | |
| DD134 hashable by construction, `crud` tuple | Yes | profile value objects hashable; `Table` never was (WARNING 1) |
| DD135 pure, model-free parser | Yes | AST-guarded |
| DD136 error subclasses `UnmappableModelError` | Yes | |
| DD137 disjoint key levels except `readOnly` | Yes | |
| DD138 `aliases`/`required`/`unique`/provenance out | Yes | |
| DD139 `entity` carried, not acted on | Yes | |
| DD140 `defaultSort.attribute` unresolved | Yes | |
| DD141 collected up front | Yes | extra `attribute_owner_by_id` param recorded as resolution A |
| Design wiring table lists an `InvalidGenerationProfileError` import in `mapper.py` | Deviation | not imported, never referenced; harmless (SUGGESTION 2) |

### Size
Authored 956 lines vs the 800 budget: 129 modified tracked backend lines plus 827 new backend lines (`profile.py` 58, `profile_parser.py` 139, `test_profile_parser.py` 228, `test_map_profiles.py` 224, `test_profile.py` 104, `generation_runner` neutrality test 44, `domain_manifest` neutrality test 30). Non-test source 265, tests about 691. Over by 156 lines because of table-driven Strict TDD triangulation. Accepted as `size:exception` by the user's standing choice; recorded, not a defect.

### docs/ai consistency
`DECISIONS_LOG.md` top entry (line 3) is DD132-DD141, titled "Change applied, verify pending"; `CURRENT_STATE.md`, `HANDOFF_LATEST.md`, `NEXT_STEPS.md` and the session note all consistently say "applied, verify pending", uncommitted. Counts true on disk: 34/34 tasks, 987 -> 1069 (+82), 137 relational_mapping. They disclose the `Table` hashability and manifest-test-location findings. No doc repeats the 90 figure (only apply-progress). All must flip to "verified/archived" at archive.

### Issues Found
**CRITICAL**: None.

**WARNING**:
1. Spec, design and proposal claim hashability of `Table` and `RelationalModel`, which was never true (pre-existing `MappingProxyType discriminator_values`; `hash(Table(...))` raises `TypeError: unhashable type: 'dict'`, confirmed at runtime). Sentences to amend, to say that `Column`, `Table.profile` and the profile value objects are hashable while `Table` and `RelationalModel` are compared by equality only:
   - `specs/relational-mapping/spec.md` line 11: "structural equality and hashing remain intact".
   - same file lines 23-26, scenario "Profile-carrying values remain hashable": `Table(..., profile=TableProfile(auditable=True))` "each is hashed" (unsatisfiable for `Table`).
   - same file line 94, Deterministic Mapping requirement: "two mappings MUST be equal and equally hashed".
   - same file lines 101-104, scenario "Profile-carrying model maps equal and hashes equal": "`hash()` of their tables and columns are equal".
   - `design.md` line 219: "Two `map_to_relational` calls on the same model stay `==` and equally hashable".
   - `proposal.md` line 88 ("repeated mapping ... is equal and hashable"); line 70 is acceptable as written (about frozen value objects).
   - `tasks.md` 4.1 and 5.5 (historical: `hash(Table(..., profile=...))`); implementation deviates knowingly.
   The generation-profile spec and design line 244 are correct (they hash `Column` and `TableProfile` only). Non-blocking: the intent (profile values hashable, deterministic) is proven.
2. Scenario "Unresolvable attribute id is accepted" says "parsed and mapped", but the only committed test is parser-level (mapper half confirmed once at runtime, not committed); no mapper-level test maps a model whose `defaultSort.attribute` matches nothing. Correct by construction (no lookup exists), so a coverage gap, not a defect.
3. Three tests pass by construction (determinism, AST guard, neutrality). They are non-vacuous and covered by the recorded mutation checks; noted for transparency.
4. apply-progress says `apps/domain_manifest` is "90 passed together with the two new neutrality test files"; on disk it is 88 passed (only one neutrality file lives in `domain_manifest`; the other is in `generation_runner`). Fix the sentence; no code impact.

**SUGGESTION**:
1. Deviation 2 (manifest half of the neutrality test in `domain_manifest/tests/`): the spec scenario names no file, so the text still matches. Consider adding `apps/generation_runner/tests/test_profile_output_neutral.py` to the spec "Verification Commands" (today only the full suite runs it).
2. Deviation 3 (`InvalidGenerationProfileError` not imported in `mapper.py`): correct as implemented; amend the design wiring table to drop it.
3. Rule-3 scenario for `aliases`/`required`/`unique` exercises each key at one level only (`aliases` at table, `required` and `unique` at column); a cross-product parametrization would be cheap.
4. At archive, flip the DD132-DD141 title and the four docs from "verify pending" to "verified/archived".

### Verdict
PASS WITH WARNINGS
0 CRITICAL, 4 WARNING, 4 SUGGESTION. All 34 tasks complete, 1069 tests pass, 59/59 scenarios compliant, 3 with caveats (spec wording that claims `Table` hashability, impossible and pre-existing; one missing mapper-level unresolvable-id test). Archive-ready once the orchestrator amends the spec/design wording (WARNING 1).
