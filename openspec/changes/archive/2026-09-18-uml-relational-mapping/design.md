# Design: UML → RelationalModel deterministic mapping (spec §21)

## Technical Approach

Exploration Approach 1: one new Django app `backend/apps/relational_mapping/` acting purely
as a registration shell (`apps.py` only), mirroring how `uml_modeling` was built in Cycle 1.
Two layers, one-directional, neither importing Django, Ninja, Pydantic, or any DB driver:

```
  mapping/  (errors, naming, mapper)
      │  reads
      ▼
  domain/   (types, schema)   ← leaf: RelationalModel dataclasses, imports only ElementId
      ▲
      └── apps.uml_modeling.domain  (CanonicalUmlModel — read-only, never mutated)
```

The only cross-app edge is `relational_mapping → uml_modeling.domain`. Nothing imports
`relational_mapping`; no models, no migrations, no DDL/SQL emission, no Java/Jinja2/LibCST.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | New app `apps.relational_mapping` with `domain/` (shape) + `mapping/` (algorithm) split; registration shell `apps.py` only, no `models.py` | Put the mapper inside `uml_modeling`; a flat single module | App-per-domain convention (Cycles 1–14, user preference). `uml_modeling` owns the *source* model; the relational shape is a different bounded domain. The `domain/`+`mapping/` split mirrors `domain/`+`validation/` exactly |
| DD2 | All output dataclasses `frozen=True`, ordered collections as `tuple[...]`, maps as read-only `Mapping` | Mutable dataclasses with `list` | Carries Cycle-1 DD3 forward unchanged: real snapshots, deterministic hypothesis shrinking, safe to cache/compare |
| DD3 | Mapper builds mutable `_TableDraft` builders internally and freezes to `Table`/`RelationalModel` at the end | Rebuild frozen tables on every FK addition | FK columns are discovered in a later pass than attribute columns; a builder keeps the pipeline linear and O(n) while the *public* output stays fully frozen |
| DD4 | **Table name = `snake_case(class.name)`, singular, never pluralized** | English pluralization (`inflect`) | Deterministic, dependency-free, reversible, and irregular plurals are a correctness trap. §22's generated JPA entity maps 1:1 to a singular table with no inflection table |
| DD5 | **Synthetic `id UUID NOT NULL` PK on every table, unconditional**, PK named `pk_<table>`; no UML metadata added | New `is_identifier` marker on `UmlAttribute` | Proposal-settled. Matches the app's own UUID-PK convention (`users`, `organizations`, `uml_documents`) and keeps `uml_modeling/domain/` untouched (proposal "Affected Areas") |
| DD6 | **Single Table inheritance**: a whole generalization tree collapses into the root class's table. Discriminator column **`class_type VARCHAR(255) NOT NULL`**; literal value = the **UML class name verbatim** (`"Invoice"`), one per class in the tree including the root. Emitted only when the tree has ≥2 classes | JOINED; TABLE_PER_CLASS; enum-typed discriminator | Proposal-settled. Verbatim class name makes §22's `@DiscriminatorValue("Invoice")` match the generated Java class name with zero transformation. `VARCHAR` over PG `ENUM` so adding a subclass never requires `ALTER TYPE` |
| DD7 | Descendant-contributed attribute columns are **always `nullable=True`**; root-class attribute columns are `NOT NULL` | Everything nullable; everything NOT NULL | Single Table forces it: a root-only row has no value for a subclass column. Root attributes have no optionality metadata in UML, so the stricter default is chosen and recorded as the future extension point |
| DD8 | **Column-name collision rule** (one helper, applied to every column): keep the plain `snake_case` name; on collision inside a table, prefix with the owning class's snake_case name; if still taken, append `_2`, `_3`, … | Prefix every subclass column unconditionally; raise on collision | Keeps the common case clean (`amount`, not `invoice_amount`) while being total and deterministic. It also absorbs three separate edge cases for free: a UML attribute literally named `id` (synthetic PK is created first and wins), a clash with `class_type`, and two sibling subclasses with the same attribute name |
| DD9 | **Deterministic construction order** is part of the contract: tables = `model.classes` order filtered to roots, then join tables in `model.relationships` order; columns = `id`, `class_type`, attribute columns (root first, then descendants breadth-first in `model.classes` order), then FK columns in `model.relationships` order; `enum_types` in `model.enumerations` order | Sorting by name; dict-iteration order | Success criterion "same model → identical `RelationalModel`". Declaration order is already the project's diagnostic-order convention (Cycle-1 DD4) |
| DD10 | **Enumeration → native PG `EnumType`**, one per `Enumeration`, `name = snake_case(enum.name)`, `labels` = `literal.value or literal.name` in declaration order. **All** enumerations are emitted, referenced or not. A column typed `EnumerationRef` gets `type=ColumnType.ENUM` + `enum_type_name` | Lookup table + FK; `VARCHAR` + `CHECK`; emit only referenced enums | Proposal-settled. Emitting all keeps the pass single-purpose and order-independent; an unused PG type is harmless and the model is regenerated, never migrated (proposal risk table) |
| DD11 | **"Many" is defined as `upper is None or upper > 1`. "Optional" is `lower <= 0`** (`<=`, not `==`) | `upper == None or upper >= 2` (same); `lower == 0` | Settles the exploration's open edge cases. `Multiplicity` is deliberately unvalidated (Cycle-1 DD2), so `lower=-1` must map to *something*: `<=` makes every negative lower bound behave as optional instead of accidentally NOT NULL |
| DD12 | **FK placement**: FK column lives on the table of the end whose **own** multiplicity is many, referencing the other end's table. If neither end is many (1:1), the FK goes on the **target** table + a `UniqueConstraint`. If **both** ends are many, a join table is emitted instead | FK always on target; always emit a join table | UML multiplicity on an end counts instances *of that end's class*, so the many end is the one with many rows — that is where the FK belongs. `source` = whole/owner is already the normative reading for COMPOSITION/AGGREGATION, so "FK on target for 1:1" keeps the part pointing at the whole |
| DD13 | **Q5 settled — FK nullability = `referenced_end.lower <= 0`, for ASSOCIATION and AGGREGATION only. COMPOSITION FKs are always `NOT NULL` + `ON DELETE CASCADE` regardless of `lower`** | Let `lower` win for composition too (producing a nullable cascading FK) | The *referenced* end's lower bound is the one that answers "must this row have a related X?". Composition asserts lifecycle ownership, a strictly stronger structural claim than the drawn multiplicity; a nullable `ON DELETE CASCADE` FK is self-contradictory (an orphan part would survive its whole). Association/aggregation FKs keep `ON DELETE NO ACTION` ("plain nullable FK", per proposal) |
| DD14 | **Q6 settled — self-referencing relationships use the generic rule unchanged**, with exactly one documented exception: a **self-referencing COMPOSITION FK is `nullable=True` + `ON DELETE CASCADE`** | A special self-reference code path; raising on self-composition | A self-composition models a tree, and a `NOT NULL` self-FK makes the table uninsertable — the root of the tree has no parent. `CASCADE` is retained so deleting a subtree root deletes the subtree. Trees are legitimate and common, so rejecting them would be wrong; `SELF_ASSOCIATION` is only a WARNING, so the mapper must accept self-links anyway. Self N:M still yields a join table with both FKs to the same table, disambiguated by DD15 then DD8 |
| DD15 | **FK column name = `snake_case(other_end.role) + "_id"` when that end has a `role`, else `<referenced_table>_id`**, then DD8 collision resolution | Always `<referenced_table>_id`; relationship-name-based | Roles are the only user-supplied disambiguator when two relationships connect the same pair of classes (or a class to itself); DD8 guarantees totality when roles are absent |
| DD16 | **Join table**: name `<source_table>_<target_table>`, synthetic `id` UUID PK (DD5), two `UUID NOT NULL` FK columns, **both `ON DELETE CASCADE` regardless of relationship kind**, one `UniqueConstraint` on the pair, one `Index` per FK column | Composite PK of the two FKs; cascade only for composition | Keeps DD5 ("one synthetic UUID PK per table") universal; the `UniqueConstraint` supplies the pair uniqueness a composite PK would have. A join row has no identity without both ends, so CASCADE is correct for every kind |
| DD17 | Every FK column gets a non-unique `Index ix_<table>__<column>`, **except** when it already carries a `UniqueConstraint` (the 1:1 case), where the unique constraint is the index | Index everything; index nothing | §21 requires indexes in the output; a redundant index behind a unique constraint is pure noise in generated DDL |
| DD18 | **The mapper never calls `validate()`.** It raises `UnmappableModelError` subclasses as *defense-in-depth* for the four structures it cannot represent | Mapper runs the validation engine first; mapper silently drops what it can't map | Keeps the dependency edge at `uml_modeling.domain` only and keeps the mapper a pure function of its argument. The new multi-parent-generalization validation rule is the **primary** enforcement (callers validate before mapping); the raise exists so a bypassing caller fails loudly instead of silently losing a parent (proposal risk table) |
| DD19 | GENERALIZATION relationships produce **no column, no FK, no join table** — they are consumed entirely by the DD6 collapse | Also emit a parent FK | Single Table has one physical table; a parent FK would point at itself |
| DD20 | The new app gets its **own** `tests/factories.py` importing only `apps.uml_modeling.domain`, not `apps.uml_modeling.tests.factories` | Reuse the existing test factories across apps | Avoids a cross-app *test-package* dependency (the `backend/apps/README.md` no-cross-imports convention); mapping scenarios need hierarchy/multiplicity-shaped builders (`a_hierarchy()`, `an_association()`) the validation factories do not provide |

## Data Flow

```
caller (future: §22 generator / §23 CRUD derivation)
   │  validate(model)  ── callers' responsibility, NOT the mapper's (DD18)
   ▼
map_to_relational(model: CanonicalUmlModel) -> RelationalModel
   │
   ├─1 _build_hierarchy(model)      → roots, descendants_of, parent_of
   │     raise MultipleGeneralizationParentsError | GeneralizationCycleError
   ├─2 _map_enumerations(model)     → (EnumType, ...) + {enumeration_id: enum_type_name}
   ├─3 _map_tables(...)             → _TableDraft per root: id PK, class_type, attribute columns
   ├─4 _map_relationships(...)      → FK columns/constraints/indexes into drafts; join-table drafts
   └─5 _freeze(...)                 → RelationalModel(tables=(...), enum_types=(...))
```

Stage 1 must also guard cycles: without it, the root walk on a cyclic model would not terminate
(`GENERALIZATION_CYCLE` is the primary defense; this is DD18 again).
Every stage is order-preserving per DD9, so the function is a deterministic pure function.

## Interfaces / Contracts

```python
# domain/types.py
class ColumnType(StrEnum):
    UUID; VARCHAR; TEXT; INTEGER; BIGINT; NUMERIC; BOOLEAN; DATE; TIMESTAMPTZ; ENUM

class ReferentialAction(StrEnum):
    NO_ACTION = "NO ACTION"; CASCADE = "CASCADE"; SET_NULL = "SET NULL"; RESTRICT = "RESTRICT"

# domain/schema.py   (every dataclass frozen=True)
@dataclass(frozen=True) class Column:
    name: str
    type: ColumnType
    nullable: bool = False
    length: int | None = None            # VARCHAR only
    precision: int | None = None         # NUMERIC only
    scale: int | None = None             # NUMERIC only
    enum_type_name: str | None = None    # ENUM only
    source_element_id: ElementId | None = None   # attribute id; None for synthetic/FK columns

@dataclass(frozen=True) class PrimaryKey:
    column_names: tuple[str, ...]        # always length 1 this cycle (DD5)
    name: str | None = None              # "pk_<table>"

@dataclass(frozen=True) class ForeignKey:
    name: str                            # "fk_<table>__<column>"
    column_names: tuple[str, ...]
    referenced_table: str
    referenced_column_names: tuple[str, ...]
    on_delete: ReferentialAction = ReferentialAction.NO_ACTION
    on_update: ReferentialAction = ReferentialAction.NO_ACTION
    source_relationship_id: ElementId | None = None

@dataclass(frozen=True) class UniqueConstraint:
    name: str                            # "uq_<table>__<cols>"
    column_names: tuple[str, ...]

@dataclass(frozen=True) class Index:
    name: str                            # "ix_<table>__<cols>"
    column_names: tuple[str, ...]
    unique: bool = False

@dataclass(frozen=True) class EnumType:
    name: str
    labels: tuple[str, ...]
    source_enumeration_id: ElementId | None = None

@dataclass(frozen=True) class Table:
    name: str
    columns: tuple[Column, ...]
    primary_key: PrimaryKey
    foreign_keys: tuple[ForeignKey, ...] = ()
    unique_constraints: tuple[UniqueConstraint, ...] = ()
    indexes: tuple[Index, ...] = ()
    source_class_ids: tuple[ElementId, ...] = ()      # root first, then descendants (DD6/DD9)
    discriminator_column: str | None = None           # "class_type" when the tree has >= 2 classes
    discriminator_values: Mapping[ElementId, str] = EMPTY   # class_id -> verbatim class name
    def column_by_name(self, name: str) -> Column | None: ...

@dataclass(frozen=True) class RelationalModel:
    tables: tuple[Table, ...] = ()
    enum_types: tuple[EnumType, ...] = ()
    def table_by_name(self, name: str) -> Table | None: ...
    def enum_type_by_name(self, name: str) -> EnumType | None: ...

# mapping/errors.py                       (all defense-in-depth, DD18)
class UnmappableModelError(Exception): ...                       # base
class MultipleGeneralizationParentsError(UnmappableModelError)   # carries class_id, parent_ids
class GeneralizationCycleError(UnmappableModelError)             # carries class_ids
class UnknownEnumerationError(UnmappableModelError)              # carries attribute_id, enumeration_id
class DanglingRelationshipEndpointError(UnmappableModelError)    # carries relationship_id

# mapping/naming.py
def snake_case(name: str) -> str                  # "OrderLine" -> "order_line"
def unique_name(taken: Set[str], preferred: str, owner: str | None) -> str    # DD8

# mapping/mapper.py
def map_to_relational(model: CanonicalUmlModel) -> RelationalModel: ...
```

### Type mapping table (DD10 + attribute → column)

| `PrimitiveType` | `ColumnType` | Extra |
|---|---|---|
| `STRING` | `VARCHAR` | `length=255` |
| `TEXT` | `TEXT` | — |
| `INTEGER` | `INTEGER` | — |
| `LONG` | `BIGINT` | — |
| `DECIMAL` | `NUMERIC` | `precision=19, scale=4` |
| `BOOLEAN` | `BOOLEAN` | — |
| `DATE` | `DATE` | — |
| `DATETIME` | `TIMESTAMPTZ` | — |
| `EnumerationRef` | `ENUM` | `enum_type_name=<mapped EnumType.name>`; unresolved id → `UnknownEnumerationError` |

### Relationship rule table (DD11–DD17)

| Case (non-GENERALIZATION) | Output |
|---|---|
| both ends many | join table (DD16) |
| exactly one end many | FK column on that end's root table → other end's root table |
| neither end many (1:1) | FK column on the **target**'s root table + `UniqueConstraint` on it |
| kind `COMPOSITION` | FK `NOT NULL` + `ON DELETE CASCADE` (DD13) |
| kind `COMPOSITION`, self-referencing | FK `nullable=True` + `ON DELETE CASCADE` (DD14) |
| kind `ASSOCIATION` / `AGGREGATION` | `nullable = referenced_end.lower <= 0`, `ON DELETE NO ACTION` |
| endpoint class is a subclass | FK targets/lands on the hierarchy **root** table (DD6) |
| kind `GENERALIZATION` | nothing (DD19) |

## The new `uml-validation` rule

Lives in `backend/apps/uml_modeling/validation/rules/relationships.py`, beside
`generalization_cycle` (same file, same relationship concern):

```python
def multi_parent_generalization(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """ERROR when a class is the source (child) of GENERALIZATION relationships
    pointing at more than one DISTINCT parent."""
```

- Build `parents_of: dict[child_id, set[parent_id]]` from `kind is GENERALIZATION`, using
  `source` = child (normative direction, `domain/elements.py::Relationship`).
- Emit one `Severity.ERROR` diagnostic per offending class when `len(distinct parents) > 1`;
  two edges to the *same* parent are a duplicate edge, not multiple inheritance, and are ignored.
- `code=DiagnosticCode.MULTI_PARENT_GENERALIZATION` (new member; token fixed by
  `specs/uml-validation/spec.md`),
  `path=class_path(child_id)`, `element_ref=ElementRef(ElementKind.CLASS, child_id)`.
- Iterate in `model.classes` declaration order (not dict order) so the output is deterministic.
- Never raises; a dangling child id simply produces no diagnostic
  (`INVALID_RELATIONSHIP_ENDPOINT` owns that case).

**Task-level consequences (same change, non-optional):** register the rule in `RULES` in
`engine.py` immediately after `generalization_cycle`; update the registry docstring/comment
("exactly 11 rules" → 12); and update
`backend/apps/uml_modeling/tests/test_engine.py::test_registry_has_exactly_eleven_rules`
(rename to `..._twelve_rules`, assert `len(RULES) == 12`). That test is the only count
assertion in the suite — `test_validation_integration.py` and `test_diagnostics.py` contain
no rule-count or closed-code-set assertion, so nothing else breaks.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/relational_mapping/{__init__,apps}.py` | Create | Registration shell; `name="apps.relational_mapping"`, `label="relational_mapping"`. No `models.py`, no `migrations/` |
| `backend/apps/relational_mapping/domain/{__init__,types,schema}.py` | Create | `ColumnType`, `ReferentialAction`; the 8 frozen schema dataclasses (DD2) |
| `backend/apps/relational_mapping/mapping/{__init__,errors,naming,mapper}.py` | Create | Exception hierarchy (DD18), `snake_case`/`unique_name` (DD4, DD8), the 5-stage pipeline |
| `backend/apps/relational_mapping/tests/**` | Create | `factories.py` (DD20) + one module per mapping concern |
| `backend/apps/uml_modeling/validation/diagnostics.py` | Modify | Add `DiagnosticCode.MULTI_PARENT_GENERALIZATION` |
| `backend/apps/uml_modeling/validation/rules/relationships.py` | Modify | Add `multi_parent_generalization` |
| `backend/apps/uml_modeling/validation/engine.py` | Modify | Import + register the rule; registry count comment 11 → 12 |
| `backend/apps/uml_modeling/tests/{test_engine,test_rules_relationships}.py` | Modify | Count assertion 11 → 12; new rule scenarios |
| `backend/config/settings.py` | Modify | Add `"apps.relational_mapping"` under the `# Local` marker in `INSTALLED_APPS` |
| `docs/ai/{CURRENT_STATE,DECISIONS_LOG}.md` | Modify | `rules.design` dual-documentation convention: record DD1–DD20 |

> Correction to the proposal's "Affected Areas": settings is the **module**
> `backend/config/settings.py`, not a `backend/config/settings/` package. `backend/apps/` is
> already a package, so no `apps/__init__.py` change is needed.
> `backend/pyproject.toml` already sets `testpaths = ["config", "apps"]`, so the new test
> directory is collected with zero configuration change.

## Testing Strategy

Strict TDD (RED → GREEN → REFACTOR), `pytest` + `hypothesis`, no `pytest-django` DB fixtures —
the whole change is DB-free. One test module per mapping concern, each importing the mapper
directly.

| Layer | Module | What to test |
|---|---|---|
| Unit | `tests/test_apps.py` | AppConfig `name`/`label`; app is registered |
| Unit | `tests/test_schema.py` | Frozen-dataclass shapes, field defaults, `table_by_name`/`column_by_name`, mutation raises |
| Unit | `tests/test_map_classes.py` | Class → table, `snake_case` singular names (DD4), table order = `model.classes` order (DD9), empty model → empty `RelationalModel` |
| Unit | `tests/test_map_attributes.py` | All 8 `PrimitiveType` → `ColumnType` rows incl. `length`/`precision`/`scale`; root attributes `NOT NULL` (DD7); DD8 collisions (attribute named `id`, sibling-subclass clash, `class_type` clash) |
| Unit | `tests/test_map_enumerations.py` | One `EnumType` per `Enumeration`; `value or name` labels in order; unreferenced enums still emitted (DD10); referencing column gets `ENUM` + `enum_type_name`; unknown `enumeration_id` → `UnknownEnumerationError` |
| Unit | `tests/test_map_identifiers.py` | Every table (incl. join tables) has exactly one `id UUID NOT NULL` PK named `pk_<table>` (DD5) |
| Unit | `tests/test_map_relationships.py` | 1:1 (FK on target + unique), 1:N (FK on the many side, DD12), N:M join table (DD16), role-based FK naming (DD15), index rules (DD17), two relationships between the same pair |
| Unit | `tests/test_map_inheritance.py` | Tree collapses to the root table; `class_type` column + verbatim-class-name values (DD6); descendant columns nullable (DD7); no table for a subclass; FK to a subclass lands on the root table; single class → no discriminator |
| Unit | `tests/test_map_nullability.py` | `lower <= 0` → nullable, `lower >= 1` → NOT NULL for association/aggregation; composition NOT NULL + CASCADE even at `0..1` (DD13); `lower = -1` behaves as optional (DD11) |
| Unit | `tests/test_map_self_reference.py` | Self association/aggregation FK on the same table; self composition nullable + CASCADE (DD14); self N:M join table with two disambiguated FK columns |
| Unit | `tests/test_map_errors.py` | Multi-parent → `MultipleGeneralizationParentsError`; generalization cycle → `GeneralizationCycleError` (and terminates); dangling endpoint → `DanglingRelationshipEndpointError`; all subclass `UnmappableModelError` |
| Property | `tests/test_determinism.py` | `hypothesis`: (a) `map(m) == map(m)` — the §21 determinism criterion; (b) every FK's referenced table + column exists; (c) column names unique within a table; (d) every table has exactly one single-column UUID PK |
| Unit (existing app) | `uml_modeling/tests/test_rules_relationships.py` | Rule fires on 2 distinct parents; silent on 1 parent; silent on a duplicate edge to the same parent; deterministic order; `path`/`element_ref` resolve |
| Unit (existing app) | `uml_modeling/tests/test_engine.py` | `len(RULES) == 12` |
| Integration / E2E | — | N/A — no endpoint, no WS, no DB in this cycle |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. The change adds pure in-process dataclasses and functions with
no I/O, no network, no user-supplied code paths, and no SQL execution.

## Sequence-Diagram Rule

`openspec/config.yaml` `rules.design` requires sequence diagrams for realtime/collaboration
flows (Django Channels). No realtime flow exists in this scope, so the rule does not apply; the
5-stage pipeline diagram above is included instead as the only non-obvious control flow.

## Migration / Rollout

No migration required. No models, no tables, no persisted data, no API consumers. Rollback =
delete `backend/apps/relational_mapping/`, revert the single `INSTALLED_APPS` line, and revert
the validation-rule commit (rule + code + registry + the two test updates).

## Open Questions

- [ ] SQL reserved words (`order`, `user`, `group`) become table/column names verbatim under
      DD4. Quoting is a DDL-emission concern and this cycle emits no DDL — confirm the §22
      generator quotes identifiers rather than pushing reserved-word mangling back into DD4.
- [ ] `VARCHAR(255)` / `NUMERIC(19,4)` are fixed defaults because UML carries no length or
      precision metadata. If §22 needs per-attribute lengths, the extension point is
      `generation_metadata` (already opaque, Cycle-1 D8), not new `UmlAttribute` fields.
- [ ] DD7's "root attributes are NOT NULL" is an assumption, not derived from UML. If a later
      cycle adds attribute optionality metadata, DD7 becomes its consumer.
- [ ] `PrimitiveType.STRING` → `VARCHAR(255)` vs `TEXT` is a §22 JPA-ergonomics call; confirm
      at verify that the generator is happy with `VARCHAR` for `STRING` and `TEXT` for `TEXT`.

> Size note: this artifact exceeds the skill's 800-word soft budget, matching the explicit
> tradeoff recorded in Cycle 1's design. The orchestrator's completion criteria require
> field-level dataclass detail and rule-level mapping tables sufficient for `sdd-tasks` to
> slice implementable units without re-deriving the algorithm.
