# Tasks: UML → RelationalModel deterministic mapping (spec §21)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1300–1550 (new app: domain ~150, mapping ~350, 12 test modules + factories ~700–900; uml_modeling rule + 2 test files ~100; settings + docs ~50) |
| Session review budget | 800 lines (this session; skill default is 400) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 |
| Delivery strategy | ask-on-risk (session pattern, not explicitly overridden) |
| Chain strategy | size:exception — single PR, confirmed by user |

Decision needed before apply: No — resolved
Chained PRs recommended: Yes (declined; size:exception accepted instead)
Chain strategy: size:exception, single PR
400-line budget risk: High (accepted via size:exception)

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Domain shape: app shell + frozen dataclasses (Phase 1) | PR 1 | `cd backend && pytest apps/relational_mapping/tests/test_apps.py apps/relational_mapping/tests/test_schema.py -q` | N/A — pure dataclass module, no process/DB to run | Delete `relational_mapping/{__init__,apps,domain}.py` + `tests/{test_apps,test_schema}.py` |
| 2 | Mapper stages 1–3: hierarchy, enums, classes/attributes/identifiers/inheritance (Phase 2–3) | PR 2 | `cd backend && pytest apps/relational_mapping/tests/test_map_errors.py apps/relational_mapping/tests/test_map_enumerations.py apps/relational_mapping/tests/test_map_classes.py apps/relational_mapping/tests/test_map_attributes.py apps/relational_mapping/tests/test_map_identifiers.py apps/relational_mapping/tests/test_map_inheritance.py -q` | N/A — pure functions, no DB fixtures | Revert `mapping/{errors,naming,mapper}.py` additions + Phase 2–3 test files; PR 1 untouched |
| 3 | Mapper stage 4–5: relationships, nullability, self-reference, freeze, determinism (Phase 4–5) | PR 3 | `cd backend && pytest apps/relational_mapping/tests/test_map_relationships.py apps/relational_mapping/tests/test_map_nullability.py apps/relational_mapping/tests/test_map_self_reference.py apps/relational_mapping/tests/test_determinism.py -q` | N/A — no I/O; `hypothesis` runs in-process | Revert `_map_relationships`/`_freeze` additions + Phase 4–5 test files; PR 1–2 untouched |
| 4 | `MULTI_PARENT_GENERALIZATION` rule + app registration + docs (Phase 6–7) | PR 4 | `cd backend && pytest apps/uml_modeling/tests/test_rules_relationships.py apps/uml_modeling/tests/test_engine.py -q` | N/A — validation is a pure function over `CanonicalUmlModel` | Revert rule/registry/settings/doc edits; new app stays registered but unused |

## Phase 1: Foundation — App Shell + Domain Shape

- [x] 1.1 RED: `backend/apps/relational_mapping/tests/test_apps.py` — AppConfig `name`/`label`, app registered
- [x] 1.2 GREEN: `backend/apps/relational_mapping/{__init__,apps}.py` — registration shell, no `models.py` (DD1)
- [x] 1.3 RED: `backend/apps/relational_mapping/tests/test_schema.py` — frozen shapes, field defaults, `table_by_name`/`column_by_name`, mutation raises
- [x] 1.4 GREEN: `backend/apps/relational_mapping/domain/{__init__,types,schema}.py` — `ColumnType`, `ReferentialAction`, 8 frozen dataclasses (DD2)

## Phase 2: Mapper Stage 1 — Hierarchy + Errors

- [x] 2.1 RED: `backend/apps/relational_mapping/tests/test_map_errors.py` — multi-parent, cycle, dangling endpoint raise typed `UnmappableModelError` subclasses
- [x] 2.2 GREEN: `backend/apps/relational_mapping/mapping/{__init__,errors}.py` + `mapper.py::_build_hierarchy` — roots, `descendants_of`, `parent_of`; cycle + multi-parent guards (DD18)
- [x] 2.3 GREEN: `backend/apps/relational_mapping/tests/factories.py` — hierarchy/multiplicity builders importing only `apps.uml_modeling.domain` (DD20)

## Phase 3: Mapper Stages 2–3 — Enumerations, Classes, Attributes, Identifiers, Inheritance

- [x] 3.1 RED: `backend/apps/relational_mapping/tests/test_map_enumerations.py` — one `EnumType` per `Enumeration`, label order, all enums emitted (DD10), unknown ref raises
- [x] 3.2 GREEN: `backend/apps/relational_mapping/mapping/mapper.py::_map_enumerations`
- [x] 3.3 RED: `backend/apps/relational_mapping/tests/test_map_classes.py` — class→table, `snake_case` singular (DD4), `model.classes` order (DD9), empty model
- [x] 3.4 GREEN: `backend/apps/relational_mapping/mapping/naming.py::snake_case` + `mapper.py::_map_tables` class pass
- [x] 3.5 RED: `backend/apps/relational_mapping/tests/test_map_attributes.py` — 8 `PrimitiveType` rows, root columns `NOT NULL` (DD7), DD8 collisions
- [x] 3.6 GREEN: `mapping/naming.py::unique_name` (DD8) + attribute-column pass in `_map_tables`
- [x] 3.7 RED: `backend/apps/relational_mapping/tests/test_map_identifiers.py` — every table exactly one `id UUID` PK named `pk_<table>` (DD5)
- [x] 3.8 GREEN: synthetic PK emission in `mapper.py::_map_tables`
- [x] 3.9 RED: `backend/apps/relational_mapping/tests/test_map_inheritance.py` — Single Table collapse, `class_type` column + verbatim values (DD6), no subclass table
- [x] 3.10 GREEN: inheritance collapse in `_map_tables` using stage-1 hierarchy

## Phase 4: Mapper Stage 4 — Relationships

- [x] 4.1 RED: `backend/apps/relational_mapping/tests/test_map_relationships.py` — 1:1 FK+unique, 1:N FK (DD12), N:M join table (DD16), role-based FK naming (DD15), index rules (DD17)
- [x] 4.2 GREEN: `backend/apps/relational_mapping/mapping/mapper.py::_map_relationships` — FK/join-table/unique/index emission
- [x] 4.3 RED: `backend/apps/relational_mapping/tests/test_map_nullability.py` — DD11 (`lower<=0`) + DD13 composition `NOT NULL`+`CASCADE` regardless of `lower`
- [x] 4.4 GREEN: nullability + `on_delete` logic in `_map_relationships`
- [x] 4.5 RED: `backend/apps/relational_mapping/tests/test_map_self_reference.py` — self association/composition/N:M per DD14
- [x] 4.6 GREEN: self-reference handling in `_map_relationships`

## Phase 5: Mapper Stage 5 — Freeze + Determinism

- [x] 5.1 GREEN: `backend/apps/relational_mapping/mapping/mapper.py::_freeze` + `map_to_relational` orchestration (5-stage pipeline)
- [x] 5.2 RED→GREEN: `backend/apps/relational_mapping/tests/test_determinism.py` — `hypothesis`: repeated mapping equal, FK targets exist, unique column names per table, one PK per table

## Phase 6: `uml-validation` Rule — `MULTI_PARENT_GENERALIZATION`

- [x] 6.1 RED: `backend/apps/uml_modeling/tests/test_rules_relationships.py` — fires on 2 distinct parents; silent on 1 parent and on duplicate edge; deterministic order; `path`/`element_ref` resolve
- [x] 6.2 GREEN: `backend/apps/uml_modeling/validation/diagnostics.py` — add `DiagnosticCode.MULTI_PARENT_GENERALIZATION`
- [x] 6.3 GREEN: `backend/apps/uml_modeling/validation/rules/relationships.py` — add `multi_parent_generalization`
- [x] 6.4 GREEN: `backend/apps/uml_modeling/validation/engine.py` — register rule after `generalization_cycle`, registry comment 11→12
- [x] 6.5 RED→GREEN: `backend/apps/uml_modeling/tests/test_engine.py` — rename `test_registry_has_exactly_eleven_rules` → `..._twelve_rules`, assert `len(RULES) == 12`

## Phase 7: Wiring, Docs, Cleanup

- [x] 7.1 GREEN: `backend/config/settings.py` — add `"apps.relational_mapping"` under `# Local` in `INSTALLED_APPS`
- [x] 7.2 GREEN: `docs/ai/CURRENT_STATE.md`, `docs/ai/DECISIONS_LOG.md` — record DD1–DD20 per `rules.design`
- [x] 7.3 REFACTOR: run full `cd backend && pytest` green; confirm zero `django`/DB/Java imports in `relational_mapping/domain/` and `mapping/`

> Size note: this artifact exceeds the skill's 530-word soft budget. Same tradeoff as Cycle 1 and this change's own `design.md` — 20 DDs, a 5-stage pipeline, and 12 test modules do not compress further without losing per-task traceability to spec requirements and threat-free scope (Threat Matrix = N/A per design.md).
