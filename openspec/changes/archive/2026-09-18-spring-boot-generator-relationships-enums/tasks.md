# Tasks: Spring Boot Generator — Relationships (FK) + Enum Types

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~900-1000 (prod ~350-400: errors.py, context.py, naming.py, renderer.py, Enum.java.j2; tests ~570: 3 new modules, factories.py, test_rejections.py rewrite, test_determinism.py widen; docs ~60) |
| Session review budget | 800 lines (override of the 400-line default, per orchestrator) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 → PR 2 → PR 3 → PR 4 → PR 5 |
| Delivery strategy | ask-on-risk |
| Chain strategy | size:exception — single PR, confirmed by user |

Decision needed before apply: No — resolved
Chained PRs recommended: Yes (declined; size:exception accepted instead)
Chain strategy: size:exception, single PR
400-line budget risk: High (accepted via size:exception)

**DD34 sequencing constraint honored**: Task 1.1 (RED — rewrite `test_rejections.py`) and Task 1.2 (GREEN — rename `ForeignKeysUnsupportedError` → `CompositeForeignKeyUnsupportedError` + DD35 reorder in `errors.py`) are both inside **Work Unit 1 / PR 1**, executed back-to-back with no other unit landing between them. The suite is red only within 1.1→1.2, never across a PR boundary.

### Suggested Work Units

| Unit | Goal | PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|----|-----------------------|------------------|--------------------|
| 1 | Error hierarchy: DD33 root/re-parent, DD34 rename, DD35 reorder | PR 1 | `cd backend && pytest apps/spring_generator/tests/test_rejections.py -v` | N/A — pure in-process function, no DB/API/filesystem (design Threat Matrix: N/A) | Revert `errors.py` + `test_rejections.py`; no other file depends on the rename outside this app |
| 2 | FK relationship fields: DD23-DD27 | PR 2 | `cd backend && pytest apps/spring_generator/tests/test_relationship_fields.py -v` | N/A — same as above | Revert `context.py` FK branch, `naming.py::relationship_base_name`, `test_relationship_fields.py`, factory additions |
| 3 | Enum fields on entities: DD28-DD29 | PR 3 | `cd backend && pytest apps/spring_generator/tests/test_enum_fields.py -v` | N/A — same as above | Revert `context.py` enum branch + `test_enum_fields.py`; FK branch (PR 2) unaffected |
| 4 | `generate_enum_source` + `Enum.java.j2`: DD30-DD33 enum branch | PR 4 | `cd backend && pytest apps/spring_generator/tests/test_enum_source.py -v` | N/A — same as above | Revert `renderer.py::generate_enum_source`, `Enum.java.j2`, enum error classes, `screaming_snake_case`, `EnumContext`/`build_enum_context` |
| 5 | Determinism widening (DD36) + docs/ai sync | PR 5 | `cd backend && pytest apps/spring_generator/tests/test_determinism.py -v && pytest apps/spring_generator` | N/A — same as above | Revert `test_determinism.py` widening and docs/ai edits; no production code touched |

## Phase 1: Error Hierarchy Rework (DD33 root/re-parent, DD34, DD35)

- [x] 1.1 RED — Rewrite `backend/apps/spring_generator/tests/test_rejections.py`: new order PK→composite-FK→discriminator→unnamed-ENUM (one test per adjacent pair); `CompositeForeignKeyUnsupportedError` with first-offender `table_name`/`foreign_key_name`/`column_names`; single-column FK raises nothing; named-enum column raises nothing; every table error subclasses both `UngeneratableTableError` and `UngeneratableSourceError`; no partial output on rejection.
- [x] 1.2 GREEN — `backend/apps/spring_generator/emit/errors.py`: add `UngeneratableSourceError(Exception)` root; re-parent `UngeneratableTableError` under it (name/subclasses unchanged); rename `ForeignKeysUnsupportedError` → `CompositeForeignKeyUnsupportedError` (no alias); reorder `reject_out_of_scope` to PK-shape → composite-FK (first offender in `foreign_keys` order) → discriminator → unnamed-ENUM (first offender in `columns` order, `type is ColumnType.ENUM` and `enum_type_name is None`).
- [x] 1.3 Grep `backend/apps/spring_generator/` for any other `ForeignKeysUnsupportedError` reference and update it (proposal: only `errors.py` + `test_rejections.py` import it).
- [x] 1.4 Run `cd backend && pytest apps/spring_generator/tests/test_rejections.py -v`; confirm green before starting Phase 2.

## Phase 2: FK Relationship Field Generation (DD23-DD27)

- [x] 2.1 Extend `backend/apps/spring_generator/tests/factories.py`: add `a_foreign_key()`, `a_unique_constraint()`; add `unique_constraints=` param to `a_table()`.
- [x] 2.2 RED — Create `backend/apps/spring_generator/tests/test_relationship_fields.py`: plain FK → `@ManyToOne`+`@JoinColumn(name, nullable)`; FK matching `unique_constraints` → `@OneToOne`+`unique=true` (DD24); self-referencing FK → own class type, no import, no error (DD27); two FKs to same table → two distinct field names (DD26); DD16 join-table shape → two `@ManyToOne` fields, zero special-casing; no `@Column` on a relationship field and `len(fields)==len(columns)` (DD23/DD25); `referencedColumnName` never emitted; relationship imports conditional; `<base_package>.*` import group empty (DD27); `relationship_base_name` table incl. `id`, no-suffix, `class_id`→`class_`.
- [x] 2.3 GREEN — Add `relationship_base_name(column_name: str) -> str` to `backend/apps/spring_generator/emit/naming.py` (DD26, `re.sub(r"_id$", "", name)`).
- [x] 2.4 GREEN — In `backend/apps/spring_generator/emit/context.py::_field_context`, add the FK branch: precedence PK → FK-member → scalar; `@OneToOne` iff `set(fk.column_names) == set(uc.column_names)` for some table `unique_constraints` entry, else `@ManyToOne`; `@JoinColumn(name, nullable[, unique])` fixed attribute order, replacing `@Column`, never emitting `referencedColumnName`; field name/getter via `relationship_base_name`; no import emitted for the same-package referenced entity (DD27); add conditional `jakarta.persistence.{ManyToOne,OneToOne,JoinColumn}` imports only when used.
- [x] 2.5 Run `cd backend && pytest apps/spring_generator/tests/test_relationship_fields.py -v`; confirm green.

## Phase 3: Enum Field Generation on Existing Entities (DD28-DD29)

- [x] 3.1 RED — Create `backend/apps/spring_generator/tests/test_enum_fields.py`: field type `pascal_case(enum_type_name)`; `@Enumerated(EnumType.STRING)` present, `ORDINAL` never appears; fixed order `@Enumerated`→`@Column`→`@NotNull` (DD11 extended); `@Size` never emitted on enum fields; nullable enum column omits `@NotNull`; `Enumerated`/`EnumType` imports conditional; an enum column does not raise through `java_type_for` in either call site.
- [x] 3.2 GREEN — In `context.py::_field_context`, add the enum branch keyed on `column.enum_type_name is not None`, short-circuiting before any `java_type_for()` call; update precedence to PK → FK → enum → scalar (DD23, DD28); annotations `@Enumerated(EnumType.STRING)` then existing `_column_annotation(...)` then `@NotNull` when not nullable (DD29); add conditional `jakarta.persistence.{Enumerated,EnumType}` imports.
- [x] 3.3 GREEN — Fix the **second** `java_type_for` call site inside `build_entity_context`'s import-collection loop (context.py) to skip FK/enum columns identically to `_field_context` — the miss the design's Risks section flags explicitly.
- [x] 3.4 Run `cd backend && pytest apps/spring_generator/tests/test_enum_fields.py -v`; confirm green.

## Phase 4: `generate_enum_source()` + `Enum.java.j2` (DD30-DD32, DD33 enum branch)

- [x] 4.1 Extend `backend/apps/spring_generator/tests/factories.py`: add `an_enum_type(name=..., labels=...)`.
- [x] 4.2 RED — Create `backend/apps/spring_generator/tests/test_enum_source.py`: path `.../domain/<Pascal>.java` + matching `package` line; invalid `base_package` raises `ValueError`; DD31 parametrized table (`in_progress`, `InProgress`, `in-progress`, `IN PROGRESS` → `IN_PROGRESS`); `getLabel()` returns the verbatim label; zero annotations, no `com.fasterxml.jackson` substring anywhere (DD19/DD32); last constant terminated by `;`, others by `,`; balanced braces; `generate_enum_source(e) == generate_enum_source(e)` (determinism); empty `labels` → `EmptyEnumTypeError`; colliding constants → `DuplicateEnumConstantError`; label `"1st"` → `InvalidJavaIdentifierError`; all three subclass `UngeneratableSourceError`.
- [x] 4.3 GREEN — `errors.py`: add `UngeneratableEnumError(UngeneratableSourceError)`, `EmptyEnumTypeError`, `DuplicateEnumConstantError`; add `reject_ungeneratable_enum(enum_type)` checking empty-labels then duplicate-constant, in that order (DD33).
- [x] 4.4 GREEN — Add `screaming_snake_case(label: str) -> str` to `naming.py`: 3-step regex (camel/Pascal split → non-alnum collapse to `_` → `.upper()`), validated through existing `naming._validate` (DD31).
- [x] 4.5 GREEN — Add `EnumConstantContext`, `EnumContext` dataclasses and `build_enum_context(enum_type, *, base_package) -> EnumContext` to `context.py` (DD30, DD32).
- [x] 4.6 Create `backend/apps/spring_generator/emit/templates/Enum.java.j2`: bare `public enum` with one constant per label (`;` on last, `,` otherwise), `private final String label`, constructor, `getLabel()` — zero annotations (DD32).
- [x] 4.7 GREEN — Add `generate_enum_source(enum_type, *, base_package="com.modelia.generated") -> GeneratedFile` to `renderer.py`, reusing `_ENVIRONMENT`, `_validate_base_package`, `package_path`; calls `reject_ungeneratable_enum` first, then `build_enum_context`, then renders `Enum.java.j2` to `domain/<class_name>.java` (DD30).
- [x] 4.8 Run `cd backend && pytest apps/spring_generator/tests/test_enum_source.py -v`; confirm green.

## Phase 5: Determinism Verification (DD36) + Docs

- [x] 5.1 RED — Widen `backend/apps/spring_generator/tests/test_determinism.py` `hypothesis` strategies to generate FK-bearing and enum-bearing tables; add `len(fields) == len(columns)` and field-order-matches-`table.columns` assertions; add a `generate_enum_source(e) == generate_enum_source(e)` property.
- [x] 5.2 GREEN — Run the widened property tests; adjust import grouping in `context.py` only if a counterexample surfaces (design expects none — DD36 is a no-new-rule decision).
- [x] 5.3 Run `cd backend && pytest apps/spring_generator/tests/test_no_concat_guard.py -v` (must stay green, unmodified) then the full suite `cd backend && pytest`.
- [x] 5.4 Update `docs/ai/CURRENT_STATE.md`: record FK-relationship and enum generation now supported by `spring_generator`.
- [x] 5.5 Update `docs/ai/DECISIONS_LOG.md`: record DD23-DD36 per the `rules.design` dual-documentation convention (`openspec/config.yaml`).
- [x] 5.6 Update `docs/ai/NEXT_STEPS.md`: mark this slice done; list Single Table inheritance, bidirectional `@OneToMany`, `@ManyToMany`/`@JoinTable`, and cross-artifact name-collision detection as explicit follow-ups (proposal Out of Scope).
