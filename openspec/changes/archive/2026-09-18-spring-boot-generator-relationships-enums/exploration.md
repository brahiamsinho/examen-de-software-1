# Exploration: Spring Boot generator — relationships, inheritance, enum generation (next slice, spec §22, item 12 of §37)

## Current State

- Archived `2026-09-18-spring-boot-generator-core` built `backend/apps/spring_generator/`:
  pure `generate_table_sources(table: relational_mapping.domain.schema.Table, *,
  base_package="com.modelia.generated") -> GeneratedSources`, one `Table` -> one JPA
  `@Entity` + one Spring Data repository interface. `emit/errors.py::reject_out_of_scope`
  rejects (fixed DD15 order) non-UUID/composite PK -> any FK -> discriminator -> ENUM
  column, first offender wins.
- `backend/apps/relational_mapping/domain/schema.py` (frozen dataclasses, unchanged since
  that archived cycle): `Column(name, type, nullable, length, precision, scale,
  enum_type_name, source_element_id)` — **no owning-class field**. `Table(name, columns,
  primary_key, foreign_keys, unique_constraints, indexes, source_class_ids,
  discriminator_column, discriminator_values)`. `ForeignKey(name, column_names,
  referenced_table, referenced_column_names, on_delete, on_update,
  source_relationship_id)` — `referenced_table` is a plain string, so the referenced
  entity's Java class name is deterministically derivable via the SAME `pascal_case()`
  already used for the entity's own class name; no cross-table object is needed.
  `EnumType(name, labels, source_enumeration_id)` lives on `RelationalModel.enum_types`,
  NOT on `Table` — a `Column` only carries `enum_type_name` (a string key). Generating
  the referencing entity field needs no lookup (`pascal_case(enum_type_name)` is
  deterministic), but generating the enum's own `.java` source needs `EnumType.labels`,
  one level above `Table`.
- Join tables (`mapper.py::_build_join_table`, archived design.md DD16): a `Table` with
  `id` PK + two `UUID NOT NULL` FK columns, one `UniqueConstraint` over the pair, one
  `Index` per FK column, no discriminator. This shape needs **no special detection** —
  generic "emit `@ManyToOne` + `@JoinColumn` per FK column" handles it automatically as
  an ordinary two-relationship entity.
- 1:1 vs N:1 detection (DD12) is derivable from a single `Table` alone: if a FK's
  `column_names` exactly match a `table.unique_constraints` entry, it's the 1:1 case
  (`@OneToOne`); otherwise `@ManyToOne`. No cross-table data needed.
- **Critical, likely-blocking gap for inheritance**: `Table.discriminator_values` maps
  `class_id -> verbatim class name` and `Table.source_class_ids` is root-first-then-
  descendants (DD9), but there is **no per-Column attribution to an owning class**
  anywhere in the frozen model. DD7 ("descendant columns always `nullable=True`; root
  columns `NOT NULL`") only disambiguates root vs. *some* descendant — it cannot
  distinguish which of 2+ sibling subclasses a given nullable column belongs to.
  Reconstructing per-column ownership (needed to emit one Java subclass per UML class
  with `@DiscriminatorValue`) is impossible from the current `RelationalModel` shape
  without either extending `Column` with new owning-class metadata (touching an
  already-archived cycle's domain model) or narrowing scope to root+exactly-one-subclass
  trees.
- `emit/javatypes.py::_JAVA_TYPE_BY_COLUMN_TYPE` has no `ColumnType.ENUM` entry (would
  `KeyError`); FK columns never go through `javatypes.py` at all — their field type is
  the referenced entity's/enum's class name, not a scalar `JavaType`.
- `tests/factories.py::a_table()` already accepts `foreign_keys=`/`discriminator_column=`
  overrides but not `discriminator_values`/`source_class_ids`; no `EnumType` factory
  exists yet.

## Affected Areas

- `backend/apps/spring_generator/emit/errors.py` — `reject_out_of_scope`'s fixed check
  order must be loosened for FK and ENUM (and, separately/later, discriminator).
- `backend/apps/spring_generator/emit/context.py` — `build_entity_context`/
  `_field_context` need FK-aware (`@ManyToOne`/`@OneToOne` + `@JoinColumn`) and
  enum-aware (`@Enumerated(EnumType.STRING)`) field paths, bypassing `javatypes.py`'s
  scalar-only lookup for those columns.
- `backend/apps/spring_generator/emit/renderer.py` — new render paths/templates for
  relationship fields, plus (additively) a new sibling function for standalone enum
  source files.
- `backend/apps/spring_generator/emit/templates/Entity.java.j2` — relationship-annotation
  blocks; a new `Enum.java.j2` template for bare Java enum types.
- `backend/apps/spring_generator/tests/factories.py` — needs an `EnumType`-style builder
  and richer `a_table()` overrides for inheritance-shaped fixtures.
- `backend/apps/spring_generator/tests/test_rejections.py` — every rejection removed
  from scope needs its DD15-order test updated/removed; anything still genuinely
  unsupported needs a new explicit test.
- `backend/apps/relational_mapping/domain/schema.py` — untouched by the
  relationships+enum slice; is the likely blocking dependency for the inheritance slice
  (Open Question 1).
- `docs/ai/CURRENT_STATE.md`, `NEXT_STEPS.md`, `DECISIONS_LOG.md` — must be updated per
  `AGENTS.md`'s memory convention once any slice lands.

## Approaches

1. **Relationships-first, unidirectional owning-side only** — `@ManyToOne`/`@OneToOne`
   + `@JoinColumn` for every FK on the table being rendered (join tables generated as
   ordinary two-relationship entities, never `@ManyToMany`/`@JoinTable`); no
   `@OneToMany` inverse collections.
   - Pros: `generate_table_sources(table)` signature fully preserved (no API-shape
     change); no upstream schema change; 1:1 vs N:1 derivable from the single
     `Table`'s own `unique_constraints`; join tables need zero special-casing.
   - Cons: unidirectional-only means no `entity.getChildren()` collection accessor on
     the "one" side.
   - Effort: Medium.
2. **Enum type generation as an additive sibling function**
   `generate_enum_source(enum_type: EnumType, *, base_package) -> GeneratedFile`,
   called independently.
   - Pros: pure function of `EnumType` alone; zero change to the existing function's
     signature; referencing entity fields only need `column.enum_type_name`
     (deterministic pascal_case), no cross-object lookup.
   - Cons: introduces a second public entry point; the future caller that walks a whole
     `RelationalModel` and invokes both functions doesn't exist yet — scope decision
     needed (Open Question 5).
   - Effort: Low.
3. **Combine 1+2 in one change vs. split.** Recommendation: combine — both additive,
   non-conflicting, small enough together for one review budget.
4. **Inheritance/discriminator generation now vs. deferred.** BLOCKED as scoped today
   (see the Current State gap). Recommend a separate, later change gated on Open
   Question 1. Effort: Medium (narrowed to 1-subclass trees) to High (if `Column` gains
   new owning-class metadata — touches an archived cycle's frozen domain model and full
   test suite).

## Recommendation

Propose **Change A: "Spring Boot generator — relationships (FK) + enum types"** as the
next `sdd-propose` target: unidirectional owning-side `@ManyToOne`/`@OneToOne` +
`@JoinColumn`, join tables as plain two-relationship entities, plus the additive
`generate_enum_source(EnumType)` function. Both pieces are strictly additive, preserve
`generate_table_sources(table)`'s current signature, need zero upstream
`relational_mapping` schema changes, and stay consistent with how item 12 was already
split from item 13.

Treat **Change B: "Spring Boot generator — Single Table inheritance"** as a separate,
later change, explicitly blocked pending Open Question 1.

## Risks

- Loosening `reject_out_of_scope`'s fixed DD15 order for FK/ENUM requires re-verifying
  the remaining checks (PK shape, and later discriminator) stay deterministic.
- Self-referencing FK (`fk.referenced_table == table.name`, valid per DD14's
  self-composition tree) must not special-case-fail — a self-referencing `@ManyToOne`
  is legal JPA.
- No cross-artifact Java type-name collision check exists today (e.g. a table `order`
  and an enum `order` both pascal_case to `Order` in the same `domain` package) —
  collision detection across a whole `RelationalModel` is a future orchestrating
  caller's job, not this slice's; should be stated explicitly, not silently assumed.
- New templates/context code must keep obeying the existing LibCST
  no-manual-string-concatenation guard and the byte-identical determinism tests.
- `ForeignKey.column_names` is tuple-shaped (composite-capable) even though the mapper
  only ever emits single-column FKs today — whether `reject_out_of_scope` should
  defensively reject a hypothetical composite FK is an open decision, not an assumption
  to make silently.

## Open Questions (for the user, before proposal)

1. **Blocking for inheritance only, not this change.** `Column` has no owning-class
   attribution. Options: (a) add `owning_class_id: ElementId | None` to `Column` in the
   archived `relational_mapping` app (reopens that cycle's domain model + tests), (b)
   narrow inheritance generation to trees with exactly one subclass (where DD7's
   nullable heuristic is unambiguous), or (c) defer Single Table generation entirely.
2. **Unidirectional-only relationships acceptable for v1?** A bidirectional mapping
   (`@OneToMany` inverse) needs `generate_table_sources` to see the whole
   `RelationalModel`, not one `Table` — a real API-shape change. Recommend
   unidirectional-only.
3. **Join-table representation**: plain `@Entity` with two `@ManyToOne` fields
   (recommended — zero extra detection logic) vs. detecting the DD16 shape and emitting
   `@ManyToMany` + `@JoinTable` on the endpoint entities (needs cross-table awareness +
   suppressing the join entity).
4. Should `reject_out_of_scope` keep a defensive composite-FK rejection even though the
   mapper guarantees single-column FKs today? Low risk either way but should be a
   recorded decision.
5. Is the future "walk a whole `RelationalModel`, call both generator functions,
   combine results" orchestrating caller in scope for Change A, or does Change A stop
   at the two additive functions (consistent with item 12 already stopping short of
   item 13)?

## Ready for Proposal

No — Open Questions 2, 3, and 5 need explicit user resolution before `sdd-propose` for
Change A. Question 1 gates a separate, later Change B (inheritance) and does not block
Change A. Question 4 is low-priority and can default to a reasonable rule at design time
if not raised explicitly.
