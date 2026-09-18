# Proposal: Spring Boot Generator — Relationships (FK) + Enum Types

## Intent

`generate_table_sources()` today rejects any `Table` carrying a foreign key or an enum-typed column, so only scalar, unrelated tables generate. UML-derived models are overwhelmingly relational and enum-bearing, which makes generation unusable past toy models. This slice of the §22/§37 generation roadmap (follows the archived `spring-boot-generator-core` cycle) lifts both restrictions additively.

## Scope

### In Scope
- Extend `generate_table_sources(table)` — signature unchanged — to emit `@ManyToOne`/`@OneToOne` + `@JoinColumn` per FK column.
- Emit `@Enumerated(EnumType.STRING)` fields for columns carrying `enum_type_name`.
- New pure `generate_enum_source(enum_type: EnumType, *, base_package) -> GeneratedFile` plus an `Enum.java.j2` template.
- Narrow `reject_out_of_scope`: drop FK and ENUM, keep PK-shape and discriminator, add composite-FK.
- Test factories for `EnumType` and FK/enum-bearing tables; update the DD15-order rejection tests.

### Out of Scope
- **Single Table inheritance generation** — a separate, later change; structurally blocked because `Column` has no owning-UML-class attribution.
- Any orchestrating caller that walks a whole `RelationalModel` and combines results.
- Bidirectional `@OneToMany` inverse collections.
- `@ManyToMany`/`@JoinTable` join-table detection or suppression.
- Cross-artifact Java class-name collision detection.
- Any edit to `relational_mapping/domain/schema.py`.

## Settled Design Constraints

| # | Constraint |
|---|---|
| 1 | Unidirectional owning-side only; public signature unchanged, one `Table` in. |
| 2 | `@OneToOne` when a FK's `column_names` exactly match a `unique_constraints` entry on the same table (DD12); `@ManyToOne` otherwise. |
| 3 | Join tables (DD16) generate as plain entities with two `@ManyToOne` fields — zero special-casing. |
| 4 | Referenced-entity/enum field types derive from the existing `pascal_case()` over `ForeignKey.referenced_table` and `Column.enum_type_name`; no cross-table lookup. |
| 5 | Self-referencing FK (`referenced_table == table.name`) is legal JPA and MUST generate. |
| 6 | FK and enum columns bypass `javatypes.py`'s scalar lookup; no `ColumnType.ENUM` entry is added there. |
| 7 | Composite FK (`len(column_names) > 1`) stays defensively rejected. |
| 8 | The change stops at exactly two additive pure functions. |

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `spring-boot-generation`: entity generation extends to FK-bearing and enum-bearing tables; the rejection set narrows to non-UUID/composite PK, discriminator, and composite FK; standalone Java enum source generation is added.

## Approach

Additive only. `emit/context.py` gains FK and enum `_field_context` branches ahead of the scalar path; `Entity.java.j2` gains relationship/enum annotation blocks; `renderer.py` gains a sibling `generate_enum_source` over a new template. `reject_out_of_scope` keeps a deterministic first-offender order over the reduced check set. Strict TDD (RED-GREEN-REFACTOR) per `config.yaml`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/spring_generator/emit/context.py` | Modified | FK + enum field-context branches |
| `backend/apps/spring_generator/emit/renderer.py` | Modified | Relationship render path; `generate_enum_source` |
| `backend/apps/spring_generator/emit/templates/Entity.java.j2` | Modified | Relationship and enum annotation blocks |
| `backend/apps/spring_generator/emit/templates/Enum.java.j2` | New | Bare Java enum body from `EnumType.labels` |
| `backend/apps/spring_generator/emit/errors.py` | Modified | Narrowed, reordered rejection set |
| `backend/apps/spring_generator/tests/` | Modified | `EnumType` factory, FK/enum fixtures, rejection tests |
| `docs/ai/` | Modified | CURRENT_STATE, NEXT_STEPS, DECISIONS_LOG |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Loosened rejection order loses determinism | Med | Keep explicit first-offender order; test residual PK→discriminator→composite-FK sequence |
| New templates break the LibCST no-string-concat guard or byte-identical determinism | Med | Extend determinism tests to FK, enum-field, and enum-source outputs |
| Java class-name collision (table `order` vs enum `order`) | Low | Out of scope and documented; owned by the future orchestrating caller |
| Composite-FK rejection is unreachable via the mapper today | Low | Explicit unit test asserting the defensive raise |

## Rollback Plan

Revert this change's commits. The change is purely additive — no migrations, no persisted state, no upstream schema or signature change — so reverting restores the previous rejection behavior for FK/enum tables with no data or API impact.

## Dependencies

- None external. Reads `relational_mapping.domain.schema` (`Table`, `ForeignKey`, `EnumType`) read-only; already present and unmodified.

## Success Criteria

- [ ] FK-bearing table emits `@ManyToOne`/`@OneToOne` + `@JoinColumn`, including the self-referencing case
- [ ] A DD16 join table emits as a two-relationship entity with no special-case code path
- [ ] Enum column emits `@Enumerated(EnumType.STRING)` typed `pascal_case(enum_type_name)`
- [ ] `generate_enum_source` returns valid Java enum source from `EnumType.labels`
- [ ] Discriminator, non-UUID/composite PK, and composite FK still raise typed errors with no partial output
- [ ] Repeated invocations stay byte-identical; `generate_table_sources(table)` signature unchanged
- [ ] `cd backend && pytest` green
