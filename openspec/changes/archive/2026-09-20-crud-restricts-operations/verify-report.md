```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:5f76eab813434426a7775fcb31635141cd0acb2a1d0eadf66fa857edfca1b2d9
verdict: fail
blockers: 1
critical_findings: 1
requirements: 4/5
scenarios: 37/38
test_command: docker compose exec -T backend pytest -q
test_exit_code: 0
test_output_hash: sha256:8d2c5c9b404924132bc344ff6041ec1a0ad01a4d769f00b7127c4f188d29f47f
build_command: docker compose exec -T backend python -m compileall -q apps/relational_mapping apps/domain_manifest
build_exit_code: 0
build_output_hash: sha256:19eaf43821a7660ec323a87c8457bf74823beb296c39f5e01aa8a683aa50f061
```

## Verification Report

**Change**: crud-restricts-operations (slice 1: shared function + Domain Manifest)
**Version**: N/A
**Mode**: Strict TDD (hybrid store)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 24 |
| Tasks complete | 23 |
| Tasks incomplete | 1 (9.1, archive-time reminder; WARNING, not a core task) |

### Build & Tests Execution
**Build**: Passed (`compileall` exit 0; Python has no separate build step).

**Tests** (all executed independently in Docker; `docker compose down` never run):

| Scope | Claimed | Observed |
|---|---|---|
| Full backend `pytest -q` | 1261 passed | 1261 passed in 100.25s |
| `apps/relational_mapping` | 170 | 170 passed |
| `apps/domain_manifest` | 140 | 140 passed |
| relational_mapping + domain_manifest + spring_generator + generation_runner | 735 | 735 passed |
| `test_builder_decoupling.py` + `test_cli.py` + `test_determinism.py` | n/a | 27 passed |

`test_output_hash` is the digest of the captured tail of the full-suite run (last 5 lines), not the whole stream.

**Coverage**: not available (no coverage tool run; informational).

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD evidence reported | Yes | Table in apply-progress |
| All tasks have tests | Yes | test_profile.py, test_schema.py, test_manifest.py |
| RED confirmed | Yes | test files exist; RED reasons plausible (ImportError, AttributeError, extra items) |
| GREEN confirmed | Yes | all pass on re-execution |
| Triangulation | Yes | 9-row truth table x 3 read_only states, canonical-order and subset cases |
| Safety net | Partly | apply-progress has no safety-net column; baseline counts (1214) are recorded instead |

Mutation evidence M1-M5 recorded; all reverted (working files equal the intended diff; no .orig/.bak/temp leftovers).

### Spec Compliance Matrix

generation-profile delta (1 requirement, 11 scenarios)

| Scenario | Test | Result |
|---|---|---|
| Undeclared profile yields all six | `test_profile.py::test_an_absent_profile_and_an_empty_profile_are_identical`, truth-table `crud=None` rows | COMPLIANT (`TableProfile(auditable=True)` covered at manifest level) |
| Declared crud maps to operation names | `test_effective_operations_for_a_writable_or_unspecified_profile` (9 rows x None/False) | COMPLIANT |
| readOnly true intersects | `test_effective_operations_for_a_read_only_profile` | COMPLIANT |
| readOnly true write-only crud is empty, no error | same test, rows U, D, CUD | COMPLIANT |
| readOnly false or None lets crud decide | truth-table rows x [None, False] (row CUD, not literal CU) | COMPLIANT |
| Declared empty crud yields none | truth-table row `()` | COMPLIANT |
| Order canonical and deterministic | `test_the_result_is_a_canonical_deterministic_tuple_of_plain_strings` | COMPLIANT |
| Constant matches controller order | `test_operation_names_are_the_six_controller_names_in_controller_order` + `test_the_manifest_operation_table_mirrors_the_shared_operation_names` | COMPLIANT |
| Table exposes effective operations | `test_schema.py::test_table_effective_operations_delegates_to_the_profile_derivation` | COMPLIANT |
| Table property is not a field | `test_table_effective_operations_is_a_property_not_a_dataclass_field` | PARTIAL (no hash assertion, see W2) |
| Derivation is pure | existing Module import purity test in `test_profile.py` (module gained no import) | COMPLIANT |

domain-manifest-export delta (4 requirement headings incl. RENAMED, 27 scenarios)

| Scenario | Test | Result |
|---|---|---|
| Six ordered operations (sample) | `test_operations_exist_exactly_when_the_entity_has_a_controller` (unmodified) | COMPLIANT |
| Undeclared profile keeps six | `test_an_undeclared_crud_still_yields_the_six_ordered_operations`, `test_read_only_false_or_unset_does_not_restrict` (+ sample for None / `TableProfile()`) | COMPLIANT |
| Restricted entity lists only its effective ops (C,R) | `test_read_only_intersects_the_declared_crud`, `test_declaring_crud_restricts_the_operations` | PARTIAL (plain `(CREATE, READ)` not literal; same path, covered by truth table) |
| Each crud subset in canonical order | `test_crud_subsets_keep_the_canonical_operation_order` ((C,), (U,D), (D,C,R)) + READ test | COMPLIANT (UPDATE alone / DELETE alone not literal) |
| Empty effective set drops controller and path | `test_an_empty_effective_set_drops_the_controller_and_the_resource_path` (2 params) | COMPLIANT |
| readOnly true keeps only read ops | `test_read_only_keeps_only_the_read_operations`, `test_read_only_intersects_the_declared_crud`, empty-set param | COMPLIANT |
| readOnly false or None lets crud decide | `test_read_only_false_or_unset_does_not_restrict` | PARTIAL (uses crud=None; spec says crud=(CREATE, UPDATE); unit truth table covers the combination) |
| resourcePath null iff operations empty | biconditional assert inside the empty-set test + sample check | COMPLIANT |
| Path validated before suppression | `test_an_invalid_table_name_is_still_rejected_whatever_the_effective_set` ((), READ), inheritance-not-validated test | COMPLIANT |
| Inheritance entities have no operations | sample tripwire (unmodified) | COMPLIANT |
| Declaring crud restricts the operations | `test_declaring_crud_restricts_the_operations` | COMPLIANT |
| **Declared crud and readOnly still emitted verbatim** (crud=() + read_only=True gives profile with crud empty list and readOnly true) | none found | **UNTESTED** |
| Restriction derived from shared function | mirror test + behaviour tests; no source-inspection test | PARTIAL |
| Sample-model output byte-identical | unedited tripwires, determinism, cli, drift guard; `docs/domain-manifest.json` diff empty | COMPLIANT |
| Decoupling guard unchanged | `test_builder_decoupling.py` unmodified, 14 passed | COMPLIANT |
| DD147 annotated as retired | `DECISIONS_LOG.md` line 71 keeps original text plus annotation; DD160-DD167 present; DD166 recorded | COMPLIANT [manual] |
| Declared-Facts-Only Emission (11 restated scenarios) | existing tests, untouched, all pass | COMPLIANT |

**Compliance summary**: 37/38 scenarios compliant (one UNTESTED; four PARTIAL are counted compliant because a passing test covers the behaviour at a neighbouring level).

### Correctness (Static Evidence)
| Item | Status | Notes |
|---|---|---|
| DD161 truth table | Implemented exactly | 9 rows x (None/False) and True, table-driven; matches `profile.py` |
| `Table.effective_operations` | Property, not field | `dataclasses.fields` excludes it; eq/repr unchanged; `Table` is unhashable before and after (dict-typed field), so the spec wording "hash equal" is unattainable (W2) |
| `OPERATION_NAMES` equals `_OPERATIONS` names | Yes | pinned by test |
| `_operations` iterates `_OPERATIONS` in declared order | Yes | `for ... in _OPERATIONS if name in names` |
| `resourcePath` null iff operations empty | Yes | inheritance short-circuit or empty set; runtime-checked |
| Path computed before suppression | Yes | segment computed, then set to None when empty; inheritance not newly validated |
| Undeclared / None / `TableProfile()` gives six | Yes | sample manifest byte-identical (tripwires pass; no diff on them or on `docs/domain-manifest.json`) |
| Unchanged guards | Yes | `git diff --stat` empty for `test_builder_decoupling.py`, `test_cli.py`, `test_determinism.py`, `test_attributes.py`, `builder/profile.py`, `apps/spring_generator`, `frontend/`, `docker-compose.yml`, `scripts/`, `apps/uml_*` |
| No leftovers | Yes | no .orig/.bak/.rej; untracked files limited to `.pi/`, the change folder and the session note |
| `.pi/` | Untouched | untracked, contents dated 2026-09-19 (before this change) |
| No version literal or environment coupling | Yes | none introduced |

### Coherence (Design)
| Decision | Followed? | Notes |
|---|---|---|
| DD160 shared function and constant in `profile.py`, no new import | Yes | |
| DD161 truth table | Yes | |
| DD162 property on `Table`, builder duck-types | Yes | no `apps.relational_mapping` import in `builder/entities.py` |
| DD163 filter rows, suppress path, keep validation | Yes | |
| DD164 single owner of the iff coupling | Yes | |
| DD165 drift guard unchanged | Yes | |
| DD166 transient divergence recorded | Yes | |
| DD167 DD147 annotated in place | Yes | |
| Deviation: `_order` instead of `bad$name` in the inheritance test | Sound | see judged items |

### Judged Items
- (a) M3 equivalence: sound. `effective_operations` already returns canonical order, so the mutant is unobservable through `build_entity`. The added direct test calls `_operations` with out-of-order names and fails on the mutant. The design claim "killed by the existing suite" was wrong; apply recorded it. Accepted.
- (b) `_order` instead of `bad$name`: sound, and more precise. Runtime check: `pascal_case("_order")` returns "Order" (accepted) while `resource_path_segment("_order")` raises `InvalidResourcePathError`; `pascal_case("bad$name")` raises `InvalidJavaIdentifierError`, so `bad$name` would fail for an unrelated reason. The test isolates exactly "path segment not computed for inheritance tables". `bad$name` is correctly used in the non-inheritance rejection test.
- (c) Task 9.1 open until archive: accepted (W1).
- (d) Authored size about 561 lines (253 added / 26 removed tracked, 286 spec delta, 22 session note): under the 700 stop threshold and the 800 budget; no `size:exception` needed. The tasks forecast (about 305 lines, spec delta about 118) understated the delta (S1).
- (e) Restated `Declared-Facts-Only Emission`: the 11 scenario headings are identical to the main spec (diffed). The requirement body differs from main by exactly one clause: the trailing deferred-item mention "`crud` filtering of `operations[]`" is dropped. RENAMED syntax (requirement heading with an arrow from old name to new name, plus a Reason line, new name restated under MODIFIED) matches `archive/2026-09-20-manifest-generation-profile/specs/domain-manifest-export/spec.md`. Counts: main `domain-manifest-export` stays at 15 requirements after the rename; `generation-profile` goes 9 to 10. Delta heading counts (validator basis): 5 requirements, 38 scenarios.
- (f) docs/ai: "applied, verify pending" for this change in CURRENT_STATE, HANDOFF_LATEST, NEXT_STEPS and DECISIONS_LOG; it is the only "newest"; the three earlier changes are marked archived and committed with the correct hashes (07fb611, 4b923aa, 20bf71c); counts (1261 / 170 / 140 / 735) match disk. Stale sentence to fix at archive: `docs/ai/DECISIONS_LOG.md` line 62 still says `manifest-generation-profile` is "archived, uncommitted" (committed as `cdae44c`). Also at archive: flip "verify pending" to "verified, archived" in the four docs and add the commit hash.

### Issues Found
**CRITICAL**:
- C1. Scenario "Declared crud and readOnly are still emitted verbatim" ([pytest]) has no covering test. Runtime behaviour is correct (`build_entity` with `TableProfile(crud=(), read_only=True)` gives a profile with crud empty list and readOnly true, `operations == []`, `resourcePath is None`), but no test asserts `entity["profile"] == {"crud": [], "readOnly": True}` at builder or manifest level, so a mutant such as `if crud:` in `builder/profile.py` would survive. Fix: one test in `test_manifest.py` (about 4 lines).

**WARNING**:
- W1. Task 9.1 is open by design (archive-time reminder).
- W2. Spec wording "equal tables ... hash equal" (Table property scenario) cannot hold: `Table` is unhashable before and after. The test correctly asserts eq, fields and repr only. Fix the scenario sentence in the delta or at archive.
- W3. Four scenarios are PARTIAL at manifest level (plain `(CREATE, READ)` literal; UPDATE alone and DELETE alone; `crud=(CREATE, UPDATE)` with read_only False/None; no source-inspection test for "derived from the shared function"). Covered by the unit truth table; optional to tighten together with the C1 test.
- W4. Safety-net evidence is not a column in apply-progress (baseline counts recorded instead).

**SUGGESTION**:
- S1. Correct the tasks.md forecast (spec delta 118 vs 286 lines) at archive.
- S2. `test_manifest.py` imports the private `_OPERATIONS` and `_operations` from `builder.entities`; acceptable in tests, revisit if the builder is refactored.

### Verdict
FAIL
One CRITICAL (UNTESTED scenario; the fix is a single test). Everything else on the check list is verified. After adding the test, re-run the manifest suite (expect 141 passed, full suite 1262); the change is then archive-ready with W1-W3 noted.

## Addendum: re-verification after fixing C1 (orchestrator)

- C1 fixed: added `test_declared_crud_and_read_only_are_still_emitted_verbatim_when_nothing_is_left` (asserts `entity["profile"] == {"crud": [], "readOnly": True}`, `operations == []`, `resourcePath is None`).
- W3 tightened: parametrized cases for `(UPDATE,)`, `(DELETE,)` and `(CREATE, READ)` were added to `test_crud_subsets_keep_the_canonical_operation_order`, and `test_a_declared_crud_decides_alone_when_read_only_is_not_true` covers `crud=(CREATE, UPDATE)` with `read_only` None/False.
- Re-run in Docker: `apps/domain_manifest` 146 passed (was 140), full backend suite 1267 passed (was 1261). No source file changed.
- Verdict after the fix: PASS WITH WARNINGS (0 CRITICAL). Remaining warnings: W1 task 9.1 closes at archive; W2 the delta wording "equal tables ... hash equal" is amended at archive (Table is unhashable); W4 no safety-net column in apply-progress (baselines recorded instead).
