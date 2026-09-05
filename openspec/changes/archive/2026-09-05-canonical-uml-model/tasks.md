# Tasks: Cycle 1 — Canonical UML Model, Project Document, Validation Engine

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1150-1300 (16 production modules ~590 lines + 14 test modules ~620 lines + settings/docs ~30 lines; all net-new) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 -> PR2 -> PR3 -> PR4 (see Work Units) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Pure domain layer: ids, types, elements, model, test factories (no validation) | PR 1 | `cd backend && pytest apps/uml_modeling/tests/test_ids.py apps/uml_modeling/tests/test_types.py apps/uml_modeling/tests/test_elements.py apps/uml_modeling/tests/test_model.py -q` | N/A — pure in-process dataclasses, no endpoint/process this cycle (design Threat Matrix: N/A) | Delete `backend/apps/uml_modeling/{__init__.py,apps.py,domain/,tests/}` and revert the `INSTALLED_APPS` line |
| 2 | `ProjectDocument` envelope (identity, owner, layout split, revision) | PR 2 | `cd backend && pytest apps/uml_modeling/tests/test_documents.py -q` | N/A — no persistence/API this cycle | Delete `documents.py` and `tests/test_documents.py`; independent of PR 3/4 |
| 3 | Validation contract + engine skeleton + naming/type rules (5 of 10 codes) | PR 3 | `cd backend && pytest apps/uml_modeling/tests/test_diagnostics.py apps/uml_modeling/tests/test_engine.py apps/uml_modeling/tests/test_rules_naming.py apps/uml_modeling/tests/test_rules_types.py -q` | N/A — no endpoint this cycle | Delete `validation/diagnostics.py`, `validation/engine.py`, `validation/rules/{naming,types}.py` and matching tests |
| 4 | Remaining rules (relationships/multiplicity/structure), full 10-rule registry, docs | PR 4 | `cd backend && pytest apps/uml_modeling -q` | N/A — no endpoint this cycle | Delete `validation/rules/{relationships,multiplicity,structure}.py`, matching tests; revert docs |

Dependencies: Unit 1 is required by Units 2 and 3. Units 2 and 3 are mutually independent
(either order, or parallel, is safe). Unit 4 requires Unit 3.

## Phase 1: Package Skeleton & Ids

- [x] 1.1 Create `backend/apps/uml_modeling/{__init__.py,apps.py}` (registration shell: `name="apps.uml_modeling"`, `label="uml_modeling"`) and `tests/__init__.py`; add `"apps.uml_modeling"` under the `# Local` marker in `INSTALLED_APPS` (`backend/config/settings.py`). Confirm `pytest` collects the new package (`testpaths` already covers `apps`, no config change). [prerequisite for all uml-domain-model reqs]
- [x] 1.2 RED: `tests/test_ids.py` — `new_id()` returns a hex `ElementId` (str-typed), two calls differ. GREEN: implement `domain/ids.py` (`ElementId = NewType("ElementId", str)`, `new_id()`). [DD7]

## Phase 2: Types (PrimitiveType, EnumerationRef, Multiplicity)

- [x] 2.1 RED: `tests/test_types.py` — all 8 `PrimitiveType` members exist; `EnumerationRef(enumeration_id)` is frozen; `AttributeType` accepts both. GREEN: implement `domain/types.py` (`PrimitiveType`, `EnumerationRef`, `AttributeType`). [uml-domain-model REQ3 primitive-accepted]
- [x] 2.2 RED: `test_multiplicity_constructible_unvalidated` — `Multiplicity(-1, None)` and `Multiplicity(2, 1)` construct without raising. GREEN: implement unvalidated frozen `Multiplicity(lower, upper)`. **Build-order gate (DD2): this MUST land before Phase 7.4, else `INVALID_MULTIPLICITY` is unreachable.**
- [x] 2.3 RED: hypothesis properties in `tests/test_types.py` — `format(parse(s)) == s` for `"1"|"0..1"|"0..*"|"1..*"`; `parse(format(m)) == m`. GREEN: implement `parse_multiplicity`/`format_multiplicity` (`ValueError` only on malformed syntax). [uml-domain-model REQ5]

## Phase 3: Elements & Model

- [x] 3.1 RED: `tests/test_elements.py` — `UmlAttribute.__post_init__` rejects a class-id-typed attribute, accepts primitive/`EnumerationRef`. GREEN: implement `domain/elements.py` (`Visibility`, `RelationshipKind`, `UmlAttribute`, `UmlParameter`, `UmlOperation`, `UmlClass`, `EnumerationLiteral`, `Enumeration`, `RelationshipEnd`, `Relationship`). [uml-domain-model REQ2, REQ3 class-typed-rejected, REQ4, REQ5]
- [x] 3.2 RED: `tests/test_model.py` — `UmlModel is CanonicalUmlModel` alias identity; declaration order preserved (classes/attributes/operations/literals); `class_by_id`/`enumeration_by_id`/`iter_named_elements` correct; `generation_metadata` entry adds no field to elements; uniqueness compared at model root (no package). GREEN: implement `domain/model.py`. [uml-domain-model REQ1, REQ2, REQ4 literal-order, REQ6, REQ7]
- [x] 3.3 Create `tests/factories.py` (`a_class`, `an_attribute`, `an_enumeration`, `a_relationship`, `a_model`, `a_project_document`) reused by every later test module.

## Phase 4: Project Document Envelope

- [x] 4.1 RED: `tests/test_documents.py` — new `ProjectDocument.id` is a valid unique UUID; `owner_id=""` raises; `owner_id="42"` round-trips unchanged; no `django.contrib.auth` import anywhere in the package. GREEN: implement `documents.py` (`ProjectMetadata`, `Position`, `DiagramLayout`, `ProjectDocument` with non-empty `owner_id` guard). [project-document REQ1, REQ2]
- [x] 4.2 RED: `tests/test_documents.py` — moving a `DiagramLayout` position leaves `UmlModel` unchanged; adding an attribute leaves `DiagramLayout` unaffected; `with_model`/`with_layout` each increment `revision` by exactly 1 given explicit `now`; two independent copies mutating concurrently raise nothing. GREEN: implement `with_model`/`with_layout` (DD8: explicit `now` argument). [project-document REQ3, REQ4]

## Phase 5: Validation Contract & Engine Skeleton

- [x] 5.1 RED: `tests/test_diagnostics.py` — `Severity`, `DiagnosticCode` (10 members), `ElementKind`, `ElementRef`, `Diagnostic`; `ValidationResult.errors`/`is_blocking` true only when an `ERROR` is present; path builders produce `/classes/{id}/attributes/{id}` grammar. GREEN: implement `validation/diagnostics.py`. [uml-validation REQ4, REQ5]
- [x] 5.2 RED: `tests/test_engine.py` — `validate(model)` on a violation-free model returns empty `errors`, `is_blocking=False`; injected fake `rules=(...)` proves no short-circuit and full aggregation. GREEN: implement `validation/engine.py` (`Rule` type, `RULES: tuple[...]` started partial, `validate(model, rules=RULES)`). [uml-validation REQ1, REQ3, DD5]

## Phase 6: Naming & Type Rules

- [x] 6.1 RED: `tests/test_rules_naming.py` — one case per code: empty class name (incl. whitespace-only), duplicate class name, duplicate attribute name, duplicate enumeration literal; each rule invoked directly (never via `validate`), asserting code/severity/path/element_ref. GREEN: implement `validation/rules/naming.py` (`EMPTY_ELEMENT_NAME` walks `iter_named_elements()`; 3 duplicate-detection functions). [uml-validation REQ2, REQ6: EMPTY_ELEMENT_NAME, DUPLICATE_CLASS_NAME, DUPLICATE_ATTRIBUTE_NAME, DUPLICATE_ENUMERATION_LITERAL]
- [x] 6.2 RED: `tests/test_rules_types.py` — `EnumerationRef("missing-id")` with no matching enumeration produces `UNKNOWN_ATTRIBUTE_TYPE`. GREEN: implement `validation/rules/types.py`. [uml-validation REQ6: UNKNOWN_ATTRIBUTE_TYPE]
- [x] 6.3 Wire the 5 naming/type rule functions into `engine.RULES` (declared order); update `test_engine.py` running-count assertion (final count of 10 asserted in Phase 7.6).

## Phase 7: Relationship, Multiplicity & Structure Rules

- [x] 7.1 RED: `tests/test_rules_relationships.py::test_invalid_relationship_endpoint` — relationship source id absent from model -> `INVALID_RELATIONSHIP_ENDPOINT`. GREEN: implement in `validation/rules/relationships.py`. [uml-validation REQ6: INVALID_RELATIONSHIP_ENDPOINT]
- [x] 7.2 RED: `test_generalization_cycle*` — mutual A<->B generalization -> exactly one `GENERALIZATION_CYCLE` anchored at the lowest-sorted class id; self-generalization (source==target) -> length-1 cycle, same code, never `SELF_ASSOCIATION`. GREEN: implement child->parent digraph, iterative DFS with a gray set. [uml-validation REQ6: GENERALIZATION_CYCLE; design algorithm note]
- [x] 7.3 RED: `test_self_association` — association with source==target -> `SELF_ASSOCIATION` WARNING, `is_blocking` stays False. GREEN: implement, scoped to `ASSOCIATION` kind only. [uml-validation REQ6: SELF_ASSOCIATION]
- [x] 7.4 RED: `tests/test_rules_multiplicity.py` — `Multiplicity(-1, None)` and `Multiplicity(2, 1)` each produce `INVALID_MULTIPLICITY` ERROR (two scenarios). GREEN: implement `validation/rules/multiplicity.py` against the unvalidated `Multiplicity` from Phase 2.2. [uml-validation REQ6: both INVALID_MULTIPLICITY scenarios; depends on DD2 build order]
- [x] 7.5 RED: `tests/test_rules_structure.py` — class with zero attributes -> `CLASS_WITHOUT_ATTRIBUTES` WARNING, not blocking. GREEN: implement `validation/rules/structure.py`. [uml-validation REQ6: CLASS_WITHOUT_ATTRIBUTES]
- [x] 7.6 Wire all 5 remaining rules into `engine.RULES`; GREEN `test_engine.py::test_registry_has_exactly_ten_rules`. Add a shared path/element_ref-resolves-to-a-real-element helper in `tests/factories.py`, reused by every rule test. [uml-validation REQ4 integration]

## Phase 8: Wiring, Cleanup & Docs

- [x] 8.1 Run `cd backend && pytest apps/uml_modeling -q`; confirm all domain/document/10-rule tests pass with zero regression to the existing health-check smoke test.
- [x] 8.2 Update `docs/ai/CURRENT_STATE.md`, `ARCHITECTURE.md`, `NEXT_STEPS.md` (real-state convention) and append the Cycle-1 completion note to `docs/ai/DECISIONS_LOG.md`.

> Size note: this artifact exceeds the skill's 530-word soft budget. The same tradeoff was
> recorded by `sdd-spec` (10-rule scenario table) and `sdd-design` (field-level dataclass
> detail): completeness of per-rule TDD sequencing and DD2 build-order traceability was
> prioritized over the word count, matching established project convention.
