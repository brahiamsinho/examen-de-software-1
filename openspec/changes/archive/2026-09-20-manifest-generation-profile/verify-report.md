```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:830aceafd4e8bba4ffc4f50105a036ccefa463c6d50c4e3bbf5422ec538ec692
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 7/7
scenarios: 29/29
test_command: docker compose exec -T backend pytest -q
test_exit_code: 0
test_output_hash: sha256:5f60ec311ff079bf5a6c596b95171a00baef50129b2c7b22012ed106d90cdd9d
build_command: docker compose exec -T backend python -m compileall -q apps/domain_manifest
build_exit_code: 0
build_output_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Verification Report

**Change**: manifest-generation-profile
**Version**: delta against `openspec/specs/domain-manifest-export/spec.md` (2 MODIFIED, 5 ADDED requirements)
**Mode**: Strict TDD (hybrid store, Docker-only tests)

`test_output_hash` is the sha256 of the captured summary line `1107 passed in 83.96s (0:01:23)`. `build_output_hash` is the sha256 of empty output (`compileall -q` prints nothing on success). `evidence_revision` is the sha256 over `git diff` plus the hashes of untracked files under `backend/apps/domain_manifest` and the change folder, taken before this report was written.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 24 |
| Tasks complete | 23 |
| Tasks incomplete | 1 (11.4, archive-time, cleanup) |

Task 11.4 is intentionally open until archive: renaming the main-spec heading now would leave the old body under the new name until the delta merges. Judged WARNING (cleanup task), not CRITICAL.

### Build & Tests Execution
**Build**: Passed (`compileall -q apps/domain_manifest`, exit 0, no output)

**Tests** (all re-run independently in Docker; `docker compose down` never used):

| Scope | Command | Result | Apply claim |
|---|---|---|---|
| Full backend | `pytest -q` | 1107 passed in 83.96s | 1107, matches |
| `apps/domain_manifest` | `pytest -q apps/domain_manifest` | 125 passed | 125, matches |
| Tripwires + decoupling | `pytest -v test_manifest.py::test_sample_entity_header test_attributes.py::test_sample_attribute test_determinism.py test_builder_decoupling.py` | 39 passed | 39, matches |
| `apps/relational_mapping` + `apps/generation_runner` | `pytest -q ...` | 208 passed | 208, matches |

**Coverage**: not measured (informational only).

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | OK | "TDD Cycle Evidence" table present in apply-progress |
| All tasks have tests | OK | every code task maps to an existing test file |
| RED confirmed (tests exist) | OK | `test_profile.py` (new), `test_attributes.py`, `test_manifest.py`, `test_profile_output_neutral.py` |
| GREEN confirmed | OK | all 125 domain_manifest tests pass now |
| Triangulation adequate | OK | parametrized: declared false, empty, SimpleNamespace, both directions, three unresolvable ids |
| Safety net | OK | pre-existing tests in modified files stay green |

Tasks 5.1, 6.1, 7.1, 8.1 pass by construction (RED proof by mutation M1/M2/M9/M10, recorded in apply-progress). Accepted: behaviour-preserving guards cannot go RED before the code lands.

**Assertion quality**: no tautologies, ghost loops or smoke-only tests found.
**Test layer**: all in-process pytest unit/integration; no E2E needed (DD150).

### Spec Compliance Matrix (7 requirements, 29 scenarios)

| Requirement | Scenario | Covering test | Result |
|---|---|---|---|
| Entity Content | Sample entity with attributes | `test_manifest.py::test_customer_scenario`, `test_sample_entity_header` | COMPLIANT |
| Entity Content | Many-to-one and N:M | existing `test_relationships.py` / `test_manifest.py` (unchanged, green) | COMPLIANT |
| Entity Content | Hierarchy subtypes | `test_sample_entity_header` (subtypes param), `test_default_sort_on_a_subtype_owned_attribute_resolves_on_the_root_entity` | COMPLIANT |
| Entity Content | Sample carries no profile key | `test_sample_entity_header`, `test_sample_attribute`, `test_profile_output_neutral.py::test_empty_generation_metadata_leaves_the_manifest_unchanged` | COMPLIANT |
| Entity Content | Attribute profile alongside fixed keys | `test_attributes.py::test_a_declared_column_profile_is_added_and_the_fixed_keys_are_unchanged` | COMPLIANT |
| Declared-Facts-Only Emission | Never-emitted keys absent | `test_undeclared_facts_are_never_emitted[aliases/entity/generation_metadata]` | COMPLIANT (see S2) |
| Declared-Facts-Only Emission | Entity flag not emitted when declared | `test_the_entity_flag_is_never_emitted_even_when_declared`, `test_build_table_profile_flags` | COMPLIANT |
| Declared-Facts-Only Emission | Each entity-level key | `test_the_entity_profile_is_emitted_last_with_every_declared_key`, `test_build_table_profile_flags` | COMPLIANT |
| Declared-Facts-Only Emission | Each attribute-level key | `test_profile.py::test_build_column_profile` (each key, all three) | COMPLIANT |
| Declared-Facts-Only Emission | Declared false emitted | `test_build_column_profile`, `test_build_table_profile_flags`, `test_a_declared_false_is_still_emitted` | COMPLIANT |
| Declared-Facts-Only Emission | Undeclared omitted, never null | single-key cases in `test_build_*_profile` | COMPLIANT |
| Declared-Facts-Only Emission | Empty or absent emits no key, no AttributeError | `test_build_*_profile` (None, all-None, SimpleNamespace), `test_an_absent_or_empty_column_profile_adds_no_key` | COMPLIANT |
| Declared-Facts-Only Emission | crud plain-str list, not re-sorted | `test_crud_is_a_list_of_plain_strings_in_declared_order`, `test_crud_is_not_re_sorted` | COMPLIANT |
| Declared-Facts-Only Emission | direction plain lowercase string | `test_default_sort_shape_and_plain_string_direction[asc/desc]` | COMPLIANT |
| Declared-Facts-Only Emission | Alphabetical serialization | `test_the_serialized_profile_is_alphabetical_whatever_the_insertion_order` | COMPLIANT |
| Declared-Facts-Only Emission | Schema version unchanged | `test_the_schema_version_stays_one_when_profiles_are_declared` | COMPLIANT |
| Default Sort Resolution | Resolves to emitted name | `test_default_sort_resolves_to_the_emitted_camel_case_attribute_name` | COMPLIANT |
| Default Sort Resolution | Subtype-owned resolves on root | `test_default_sort_on_a_subtype_owned_attribute_resolves_on_the_root_entity` | COMPLIANT |
| Default Sort Resolution | Unknown id raises exact error | `test_an_unresolvable_default_sort_id_raises_the_exact_error[*]` (exact `str(...)` and `build_manifest` path) | COMPLIANT |
| Default Sort Resolution | Synthetic and foreign ids unknown | `test_a_synthetic_column_id_is_unknown`, `...exact_error[a-other-table/a-class-type]` | COMPLIANT (see S3) |
| Default Sort Resolution | Resolver not called without default sort | `test_build_table_profile_flags` (`spy.calls == []`) | COMPLIANT |
| ManifestError Location | Re-export keeps imports working | `test_manifest_error_lives_in_errors_and_is_re_exported`, `test_cli.py` | COMPLIANT |
| Profile Builder Decoupling | Guard still passes | `test_builder_decoupling.py` unedited (`rglob` over `builder/` covers both new files) | COMPLIANT |
| CRUD Does Not Filter | Declaring crud keeps six operations | `test_declaring_crud_does_not_filter_the_operations` | COMPLIANT |
| Determinism and Sample Neutrality | Two runs equal bytes | `test_a_profile_carrying_model_serializes_to_identical_bytes_without_an_id_key`, `test_determinism.py` | COMPLIANT |
| Determinism and Sample Neutrality | Sample manifest unchanged | tripwires unedited and green | COMPLIANT |
| Determinism and Sample Neutrality | Profile model changes manifest, empty metadata does not | `test_profile_output_neutral.py` (2 tests) | COMPLIANT |
| Determinism and Sample Neutrality | Regression suites untouched | full suite 1107 passed; protected-path `git diff --stat` empty | COMPLIANT |
| Determinism and Sample Neutrality | Decision log records supersession and debt | [manual] `docs/ai/DECISIONS_LOG.md` lines 3-17: DD142-DD150, DD131 superseded, DD147 tech debt | COMPLIANT (manual) |

**Compliance summary**: 29/29 scenarios compliant (28 by passing tests, 1 [manual] by inspection as the spec designates).

### Correctness (Static Evidence)
| Check | Status | Notes |
|---|---|---|
| Entity profile keys | OK | `auditable`, `readOnly`, `crud`, `defaultSort{attribute,direction}` exactly as the spec |
| Attribute profile keys | OK | `searchable`, `sortable`, `readOnly` |
| Omission rules | OK | `is not None` (not truthiness); `or None` yields no empty dict |
| Key is `attribute`, not `attributeId` | OK | `profile.py` line 44 |
| Exact ManifestError message | OK | equals the spec string, built with `!r` on table name and id |
| Discriminator excluded, synthetic ids never match | OK | `_resolver` skips `table.discriminator_column`; `None` never equals a declared id |
| Resolver only when declared | OK | gated by `default_sort is not None` |
| ManifestError location and re-export | OK | class in `builder/errors.py`; `manifest.py` and `entities.py` import it; `builder/__init__.py` not modified |
| Import purity | OK | no `apps.relational_mapping` import in `domain_manifest` non-test source (docstring mentions only); `errors.py` has no imports |
| `schemaVersion` | OK | still `SCHEMA_VERSION = 1` |
| Profile is last key (entity and attribute) | OK | asserted via last-key checks |
| Protected paths | OK | `git diff --stat` empty for `backend/apps/relational_mapping`, `backend/apps/spring_generator`, `docker-compose.yml`, `scripts` |
| Tripwires unmodified | OK | diffs of `test_manifest.py` and `test_attributes.py` show only imports, `EXCLUDED_KEYS` and additions; `test_sample_entity_header` and `test_sample_attribute` bodies untouched; `test_determinism.py` and `test_builder_decoupling.py` have no diff |
| Mutation leftovers | None | `profile.py`, `entities.py`, `attributes.py` read clean; suite green |
| `.pi/` | Untouched | pre-existing untracked dir (mtime 2026-09-19), also untracked in the initial status |

### Coherence (Design)
| Decision | Followed? | Notes |
|---|---|---|
| DD142 pure `profile.py`, duck-typed `getattr` | Yes | |
| DD143 `ManifestError` in `errors.py` | Yes | breaks the entities/manifest cycle |
| DD144 shared `attribute_name` | Yes | resolver and `_attribute` share it |
| DD145 omit undeclared, never null | Yes | |
| DD146 `_text` via `getattr(value, "value", value)` | Yes | |
| DD147 crud does not filter operations | Yes | tested, logged as tech debt |
| DD148 `EXCLUDED_KEYS` narrowed | Yes | exactly `["aliases", "entity", "generation_metadata"]` |
| DD149 neutrality test retargeted | Yes | |
| DD150 no compose, scripts or golden change | Yes | |

### Judgment of the known items
- (a) **M3 is an equivalent mutant: confirmed.** Without the `profile is None` guard, `getattr(None, field, None)` returns `None` for every field, so `_declared` returns an empty dict and `or None` gives `None`; `build_table_profile` likewise reaches `None` without calling the resolver. No observable difference, so no test can kill it. Accepted (S1).
- (b) **Task 11.4 open until archive: accepted** as WARNING W1; the archive step must perform it.
- (c) **Proposal stale on EXCLUDED_KEYS: confirmed.** Sentences to amend (design and spec win):
  1. `proposal.md` line 54 (Risks table): "Narrow it to `aliases` + `entity`" must read `aliases` + `entity` + `generation_metadata`, i.e. `["aliases", "entity", "generation_metadata"]`.
  2. Line 71 (Success Criteria): "`aliases` and `entity` never appear" must also name `generation_metadata`.
  3. Line 31 (Capabilities): "`aliases` stays forbidden" understates the spec, which forbids `aliases`, `entity` and `generation_metadata`.
  4. Line 20 (Out of Scope): "`aliases` - stays excluded" is accurate but omits that `generation_metadata` also stays excluded (optional touch-up).
  5. Lines 5 and 31 keep the old requirement name `Declared-Facts-Only Exclusion`; acceptable as a reference to the current main spec, renamed at archive (task 11.4).
- (d) **Size: fine.** About 419 authored lines (production ~70: `errors.py` 9, `profile.py` 47, ~20 in builders; tests ~350) vs the 800 budget; no exception needed.
- (e) **Docs: consistent.** `CURRENT_STATE.md`, `HANDOFF_LATEST.md`, `NEXT_STEPS.md` and the session note all say "applied, verify pending" and quote 88 to 125, 1070 to 1107 and 208; this run confirms every count on disk. Duplicate "newest" labels exist (S4).

### Issues Found
**CRITICAL**: None.

**WARNING**:
- W1. Task 11.4 unchecked (archive-time): the main spec `openspec/specs/domain-manifest-export/spec.md` still has `Declared-Facts-Only Exclusion` and a Purpose that says section 33 `generation_metadata` is out of scope. Archive must REPLACE (not append) the heading and fix the Purpose text. Docs must flip from "verify pending" to "verified" afterwards.
- W2. `proposal.md` is stale on `EXCLUDED_KEYS` (list under item (c)); amend before archive so the archived change does not contradict the spec.

**SUGGESTION**:
- S1. The `profile is None` guards are redundant (equivalent mutant M3); harmless, may be dropped in a later refactor.
- S2. `EXCLUDED_KEYS == ["aliases", "entity", "generation_metadata"]` drives the parametrization but is not asserted explicitly; add a one-line equality assertion to pin the guard list.
- S3. A "foreign id" (an id of another table) is covered by an id matching no column of this table (`a-other-table`), which is behaviourally identical; no separate two-table test. Acceptable.
- S4. Duplicate "newest" labels: `CURRENT_STATE.md` lines 10 and 12, `HANDOFF_LATEST.md` lines 13 and 26, `NEXT_STEPS.md` lines 9 and 11 each mark two different changes as newest. Drop the label on the older entry when docs are updated after verify/archive. `HANDOFF_LATEST.md` also calls DD142-DD150 "applied"; update to "archived" at archive time.
- S5. Changed-file coverage was not measured; add a coverage run if a number is wanted.

### Verdict
PASS WITH WARNINGS

0 CRITICAL, 2 WARNING, 5 SUGGESTION: all 29 scenarios pass, the full suite is 1107 passed, protected paths are untouched; the only open items are archive-time task 11.4 and the stale proposal text.
