# Design: Spring Boot generator — relationships (FK) + enum types

> Extends the archived `2026-09-18-spring-boot-generator-core` cycle (DD1–DD22).
> New decisions continue at **DD23**; every DD1–DD22 convention still holds unless a
> decision below names it explicitly.

## Technical Approach

Strictly additive. No public signature changes; one new public function. The existing
4-stage pipeline is untouched — only stage 1's rule set narrows and stage 2 gains two
branches ahead of the scalar path:

```
generate_table_sources(table, *, base_package)            [unchanged signature]
   ├─1 reject_out_of_scope(table)   PK → composite-FK → discriminator → unnamed ENUM   (DD35)
   ├─2 build_entity_context(...)    per column, first matching branch wins:            (DD23)
   │        PK  → DD8 identity path
   │        FK  → @ManyToOne|@OneToOne + @JoinColumn                              (DD24, DD25)
   │        enum→ @Enumerated(EnumType.STRING) + @Column                          (DD28, DD29)
   │        else→ existing java_type_for() scalar path
   ├─3 render Entity.java.j2
   └─4 render Repository.java.j2                                                  [unchanged]

generate_enum_source(enum_type, *, base_package) -> GeneratedFile                      (DD30)
   ├─1 reject_ungeneratable_enum(enum_type)   empty → duplicate-constant            (DD33)
   ├─2 build_enum_context(...)                SCREAMING_SNAKE + verbatim label (DD31, DD32)
   └─3 render Enum.java.j2 → src/main/java/<pkg>/domain/<PascalName>.java
```

Both functions stay pure, DB-free and filesystem-free (DD3). Neither knows about the
other; combining them over a whole `RelationalModel` remains the future caller's job.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD23 | **One field per `Column`, always.** `_field_context` picks the **first** matching branch: PK → FK-member → `enum_type_name` → scalar. A FK column yields the relationship field **instead of**, never in addition to, a scalar `categoryId` field, so `len(fields) == len(table.columns)` stays invariant. PK membership outranks FK membership | Emitting both the raw `UUID categoryId` and the `Category category` field (a JPA double-mapping error unless one is `insertable=false, updatable=false`); appending relationship fields after the scalars | Double-mapping the same DB column is the classic Hibernate `Repeated column in mapping` failure. The one-field invariant is also what keeps DD12's declaration-order rule trivially true (DD36). The PK-first precedence is defensive: the mapper's synthetic UUID PK is never a FK, but if it ever were, DD8's identity path must still win deterministically rather than depending on branch order by accident |
| DD24 | **`@OneToOne` iff `set(fk.column_names)` equals `set(uc.column_names)` for some `uc` in `table.unique_constraints`; `@ManyToOne` otherwise.** Set comparison, evaluated against the table's own constraints only | Inferring 1:1 from the source UML multiplicity (not present on `ForeignKey`); always `@ManyToOne`; cross-table lookup | Derivable from a single `Table`, so the one-`Table`-in signature survives (proposal constraint 1). A unique constraint over exactly the FK's columns *is* the relational statement of "at most one child per parent". The set (not tuple) comparison makes column order in the constraint irrelevant. The DD16-shaped join table gets a unique constraint over **both** FK columns, which matches *neither* single-column FK set — so it falls through to two `@ManyToOne` fields with zero special-casing, exactly as proposal constraint 3 requires |
| DD25 | **`@JoinColumn(name = "<column.name>", nullable = <column.nullable>[, unique = true])` replaces `@Column` on relationship fields** — never both. `unique = true` only in the DD24 `@OneToOne` case. Fixed attribute order `name, nullable, unique`. **`referencedColumnName` is never emitted** | Emitting `@Column` alongside `@JoinColumn`; always emitting `referencedColumnName = "<fk.referenced_column_names[0]>"`; carrying `length`/`columnDefinition` over | `@Column` and `@JoinColumn` on the same field is invalid JPA. Omitting `referencedColumnName` lets JPA default to the referenced entity's `@Id`, which this generator unconditionally names `id` (DD8 over `relational_mapping`'s synthetic-UUID-PK invariant) — emitting it would restate a guaranteed default. Explicit `name` first mirrors DD10 verbatim |
| DD26 | **Relationship field name = `camel_case(base)` where `base` = the FK column name with one trailing `_id` removed** (`category_id` → `category`); getter/setter = `pascal_case(base)`. If stripping yields an empty string, or the name has no `_id` suffix, `base` is the column name unchanged. New helper `naming.py::relationship_base_name(column_name) -> str`, implemented with `re.sub(r"_id$", "", name)` | `camel_case(fk.referenced_table)`; the FK column name verbatim (`categoryId`) | `referenced_table` **breaks** on two legitimate shapes this slice must support: a self-referencing FK (`manager_id` → `employee`) would name the field after its own class instead of the role, and two FKs to the same table (`billing_address_id` + `shipping_address_id` → both `address`) would emit two identically-named fields — a Java compile error. The column name carries the role; the referenced table does not. Stripping *before* `camel_case` keeps DD16's whitelist and reserved-word `_` suffix as the single validation surface (`class_id` → `class` → `class_`), and `re.sub` keeps the DD14 no-concatenation guard satisfied |
| DD27 | **No import is emitted for the referenced entity or the enum type.** Both are generated into `{base_package}.domain`, the same package as the entity being rendered, so the would-be import `{base_package}.domain.{pascal_case(referenced_table)}` is redundant. The entity's `<base_package>.*` import group therefore stays empty; only `Repository.java` (in `.persistence`) populates it. A self-referencing FK is consequently not special-cased anywhere | Emitting the same-package import anyway; special-casing `fk.referenced_table == table.name` to suppress a self-import | Java resolves same-package types with no import; emitting one is legal but noise a reviewer must re-justify (same argument DD17 used to drop `@Repository`). It also makes the self-reference case fall out for free instead of needing the guard proposal constraint 5 warns about — `Employee.manager` of type `Employee` needs no import and no branch |
| DD28 | **The enum branch keys on `column.enum_type_name is not None` and short-circuits before any `java_type_for()` call.** Field type = `pascal_case(column.enum_type_name)`. `javatypes.py` gains **no** `ColumnType.ENUM` row and is not modified at all. `build_entity_context`'s import-collection loop must skip the same columns, not just `_field_context` | Adding `ColumnType.ENUM -> JavaType(...)` to `_JAVA_TYPE_BY_COLUMN_TYPE`; branching on `column.type is ColumnType.ENUM` | `javatypes.py` is a pure `ColumnType -> JavaType` table (DD5); an enum's Java type depends on `enum_type_name`, a *different* field, so no total function over `ColumnType` alone can produce it. Keying on `enum_type_name` rather than `ColumnType.ENUM` is what makes the residual `ENUM`-without-a-name case a *named* rejection (DD35) instead of a bare `KeyError`. The import loop is a second, easily-missed call site of `java_type_for` in the same function — calling it for a FK or enum column would resurrect the `KeyError` the branch exists to prevent |
| DD29 | **Enum-field annotations: `@Enumerated(EnumType.STRING)`, then the existing `_column_annotation(...)`, then `@NotNull` when `nullable=False`. Never `@Size`.** DD11's fixed per-field order extends to: `@Id`, `@GeneratedValue`, `@ManyToOne`\|`@OneToOne`, `@JoinColumn`, `@Enumerated`, `@Column`, `@NotNull`, `@Size` | `@Enumerated(EnumType.ORDINAL)` (or omitting `@Enumerated`, whose default *is* ORDINAL); skipping `@Column` on enum fields; skipping `@NotNull` | ORDINAL persists a positional integer, so reordering a UML enumeration's literals silently corrupts every stored row — `STRING` is the only safe default for generated code. `@Column` and `@Enumerated` are orthogonal in JPA (unlike DD25's `@JoinColumn` case), so `_column_annotation` is reused verbatim and DD10 still holds. DD9's nullability rule is column-shape-driven and applies unchanged. `@Size` is already gated on `type is VARCHAR`, so it excludes itself |
| DD30 | **`generate_enum_source` lives in `emit/renderer.py`** alongside `generate_table_sources`, reusing `_ENVIRONMENT`, `_validate_base_package` and `package_path`; its context builder `build_enum_context(enum_type, *, base_package) -> EnumContext` lives in `emit/context.py` next to the other builders. New template `emit/templates/Enum.java.j2` | A new `emit/enum_renderer.py` module; building the enum source inline in `context.py` | A second module would either duplicate the DD13 Jinja `Environment` or import it across modules, splitting ownership of the single configured environment. `renderer.py` is already defined as "the public API surface" (DD3); both entry points belonging there is the smaller, more honest boundary. Keeping the context builder in `context.py` preserves DD2's invariant that **all** branching lives in `context.py` and templates stay data-driven, which is also the surface DD14's guard polices |
| DD31 | **Enum constant = SCREAMING_SNAKE_CASE** via a fixed 3-step regex normalization of the label: (1) `re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", label)` splits camel/Pascal boundaries, (2) `re.sub(r"[^A-Za-z0-9]+", "_", s)` collapses every non-alphanumeric run to one `_`, (3) `.upper()`. The result is validated by the existing `naming._validate`, so an illegal result raises `InvalidJavaIdentifierError` | Using the label verbatim as the constant; `pascal_case(label)`; silently sanitizing illegal labels | SCREAMING_SNAKE is the universal Java enum-constant convention, and generated code that ignores it is the first thing a reviewer flags. The three steps make `in_progress`, `InProgress`, `in-progress` and `IN PROGRESS` all converge on `IN_PROGRESS` deterministically. Reusing `naming._validate` keeps DD16's whitelist as the one boundary between user-supplied UML text and emitted `.java` — reserved-word suffixing is a harmless no-op because no Java keyword is uppercase. All three steps are `re.sub`/`.upper()`, so the DD14 guard stays green |
| DD32 | **The verbatim label is preserved as a plain `private final String label` + constructor arg + `public String getLabel()`** on the generated enum. **DD19 still holds: no Jackson, no `@JsonValue`, no annotation of any kind on the enum.** No `AttributeConverter` is generated | SCREAMING_SNAKE with the original label discarded; `@JsonValue` on an accessor (revisiting DD19); generating an `AttributeConverter` so the persisted value matches the label | DD31 is the first place in this generator where an identifier is transformed **and JPA offers no annotation slot to carry the original** — DD10's `@Column(name=...)` and DD16's rule both rest on that slot existing. Four annotation-free lines restore the invariant that the source DB string is always recoverable from the emitted source, and hand the future `AttributeConverter`/DTO slice a ready-made hook. `@JsonValue` would reverse DD19's layering argument (serialization belongs to the `api/` DTO layer) for one type, which is worse than not reversing it at all. **Known divergence, recorded below**: `@Enumerated(STRING)` persists `name()`, so the stored value is `IN_PROGRESS`, not `in_progress` — self-consistent inside a generated project, but a future DDL emitter reading `EnumType.labels` must apply DD31 or read `getLabel()` |
| DD33 | **Error root widened, additively.** New root `UngeneratableSourceError(Exception)`; `UngeneratableTableError` is re-parented under it (its name and every existing subclass are unchanged); new sibling branch `UngeneratableEnumError(UngeneratableSourceError)` with `EmptyEnumTypeError` and `DuplicateEnumConstantError`. `generate_enum_source` calls `reject_ungeneratable_enum(enum_type)` first, in the fixed order empty-labels → duplicate-constant | Hanging the enum errors off `UngeneratableTableError`; renaming the existing root; letting an empty or colliding enum render anyway | An enum-type failure is not a table failure, but every existing `isinstance(e, UngeneratableTableError)` assertion must keep passing — re-parenting widens the hierarchy without touching a single existing name or test. Two labels colliding on one constant (`in progress` / `in-progress` → `IN_PROGRESS`) emits Java that does not compile, which is exactly the class of silent failure DD15 exists to convert into a named, catchable error. An empty `labels` tuple emits a legal-but-useless `enum X { }` and almost certainly signals an upstream mapper bug |
| DD34 | **`ForeignKeysUnsupportedError` is renamed to `CompositeForeignKeyUnsupportedError`**, carrying `table_name`, `foreign_key_name`, `column_names` (the **first** offending FK in `table.foreign_keys` order, not the whole list). **No backwards-compatible alias is kept** | Repurposing the old name in place to mean "composite FK"; keeping `ForeignKeysUnsupportedError` as a deprecated alias | The old name asserts "this generator does not support foreign keys", which is now false — a caller catching it would be catching a promise the generator no longer makes, and that is a worse failure mode than a rename. Blast radius is two files inside this one app (`emit/errors.py`, `tests/test_rejections.py`); nothing outside `spring_generator` imports it (DD1: nothing imports this app). Narrowing the payload from the whole FK list to the first offender matches DD15's first-offender-wins philosophy already used for the ENUM column check |
| DD35 | **New fixed rejection order in `reject_out_of_scope`**: (1) PK shape → `UnsupportedPrimaryKeyError`; (2) any FK with `len(column_names) > 1`, first offender in `foreign_keys` order → `CompositeForeignKeyUnsupportedError`; (3) discriminator → `InheritanceUnsupportedError`; (4) a column with `type is ColumnType.ENUM` **and** `enum_type_name is None`, first offender in `columns` order → `UnsupportedColumnTypeError`. Single-column FKs and named enum columns raise nothing | Dropping the composite-FK check entirely (the mapper never emits one today); moving composite-FK after discriminator; dropping check 4 now that enums generate | Composite FK is kept defensively per proposal constraint 7: `ForeignKey.column_names` is tuple-shaped, so the type system permits a shape DD24/DD25/DD26 have no answer for, and a defensive raise costs one `if`. Keeping composite-FK in the *old* FK slot preserves the relative order of every surviving check, so the two existing order tests become renamed assertions rather than reordered ones. Check 4 is the narrowed residue of the old blanket ENUM rejection: it is the only remaining path to a `java_type_for` `KeyError` (DD28) |
| DD36 | **Determinism is unchanged and needs no new rule.** Field order is still `Table.columns` declaration order (DD12) because DD23 guarantees exactly one field per column, produced in place. Import grouping is untouched: the new `jakarta.persistence.{ManyToOne, OneToOne, JoinColumn, Enumerated, EnumType}` imports join the existing `jakarta.*` group and sort lexicographically by FQN with everything else; each is added only when at least one field actually uses it, mirroring the existing `uses_not_null`/`uses_size` flags. Per DD27 the `<base_package>.*` group stays empty for entities, and `Enum.java.j2` renders with `import_groups = ()` | Adding a sort over relationship fields; a separate import group for same-package types | Re-sorting would decouple the emitted class from the model the user drew, which DD12 rejected for exactly this reason. Because no new *kind* of ordering is introduced, the existing `hypothesis` determinism property tests extend to FK/enum tables by widening their input strategy, not by adding a new ordering rule |

## Interfaces / Contracts

```python
# emit/naming.py                                                              (DD26, DD31)
def relationship_base_name(column_name: str) -> str   # "category_id" -> "category"
def screaming_snake_case(label: str) -> str           # "In Progress" -> "IN_PROGRESS"

# emit/context.py                                                       (DD23-DD26, DD28-DD30)
@dataclass(frozen=True) class EnumConstantContext:
    name: str        # SCREAMING_SNAKE Java constant                              (DD31)
    label: str       # verbatim EnumType label, preserved                         (DD32)

@dataclass(frozen=True) class EnumContext:
    package: str                 # "{base_package}.domain"
    class_name: str              # pascal_case(enum_type.name)
    constants: tuple[EnumConstantContext, ...]

def build_enum_context(enum_type: EnumType, *, base_package: str) -> EnumContext

# emit/errors.py                                                          (DD33-DD35)
class UngeneratableSourceError(Exception)                       # NEW root
class UngeneratableTableError(UngeneratableSourceError)         # re-parented, name kept
class CompositeForeignKeyUnsupportedError(UngeneratableTableError)   # RENAMED from
                     # ForeignKeysUnsupportedError; table_name, foreign_key_name, column_names
class UngeneratableEnumError(UngeneratableSourceError)          # NEW branch
class EmptyEnumTypeError(UngeneratableEnumError)                # enum_type_name
class DuplicateEnumConstantError(UngeneratableEnumError)        # enum_type_name, constant, labels

def reject_ungeneratable_enum(enum_type: EnumType) -> None      # NEW

# emit/renderer.py                                                             (DD30)
def generate_enum_source(
    enum_type: EnumType, *, base_package: str = "com.modelia.generated"
) -> GeneratedFile: ...
```

### FK / enum column → Java field (extends the DD5–DD10 table)

`<n>` = `column.name`, `base` = `relationship_base_name(<n>)` (DD26).

| Column shape | Java type | Import | Mapping annotations | Validation |
|---|---|---|---|---|
| in `fk.column_names`, FK set **==** a `unique_constraints` set | `pascal_case(fk.referenced_table)` | **none** (DD27) | `@OneToOne`, `@JoinColumn(name = "<n>", nullable = <nullable>, unique = true)` | `@NotNull` when not nullable |
| in `fk.column_names`, otherwise | `pascal_case(fk.referenced_table)` | **none** (DD27) | `@ManyToOne`, `@JoinColumn(name = "<n>", nullable = <nullable>)` | `@NotNull` when not nullable |
| `enum_type_name` is set | `pascal_case(enum_type_name)` | **none** (DD27) | `@Enumerated(EnumType.STRING)`, then the DD10 `@Column(...)` | `@NotNull` when not nullable |
| `type is ENUM` and `enum_type_name is None` | — | — | **rejected**: `UnsupportedColumnTypeError` (DD35) | — |
| any FK with `len(column_names) > 1` | — | — | **rejected**: `CompositeForeignKeyUnsupportedError` (DD35) | — |

Conditional imports (DD36): `jakarta.persistence.ManyToOne` / `OneToOne` / `JoinColumn` /
`Enumerated` / `EnumType`, each only when emitted.

### `Enum.java.j2` (DD2, DD13, DD31, DD32)

```jinja
package {{ package }};

public enum {{ class_name }} {
{% for constant in constants %}
    {{ constant.name }}("{{ constant.label }}"){% if loop.last %};{% else %},{% endif %}
{% endfor %}

    private final String label;

    {{ class_name }}(String label) {
        this.label = label;
    }

    public String getLabel() {
        return this.label;
    }
}
```

Output path `src/main/java/<base_package as path>/domain/<class_name>.java` (DD20 layout).

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/spring_generator/emit/context.py` | Modify | FK + enum branches in `_field_context` (DD23–DD26, DD28, DD29); skip `java_type_for` for those columns in the import loop (DD28); conditional relationship/enum imports (DD36); `EnumConstantContext`/`EnumContext`/`build_enum_context` (DD30) |
| `backend/apps/spring_generator/emit/errors.py` | Modify | `UngeneratableSourceError` root + `UngeneratableEnumError` branch (DD33); rename to `CompositeForeignKeyUnsupportedError` (DD34); new `reject_out_of_scope` order (DD35); `reject_ungeneratable_enum` |
| `backend/apps/spring_generator/emit/naming.py` | Modify | `relationship_base_name` (DD26), `screaming_snake_case` (DD31) |
| `backend/apps/spring_generator/emit/renderer.py` | Modify | `generate_enum_source` (DD30) |
| `backend/apps/spring_generator/emit/templates/Enum.java.j2` | Create | Bare Java enum with preserved labels (DD32) |
| `backend/apps/spring_generator/emit/javatypes.py` | **Unchanged** | No `ColumnType.ENUM` row (DD28); docstring stays accurate |
| `backend/apps/spring_generator/emit/templates/Entity.java.j2` | **Unchanged** | Already loops over `field.annotations`; new annotations need no template change (DD2 holds) |
| `backend/apps/spring_generator/tests/factories.py` | Modify | `a_foreign_key()`, `a_unique_constraint()`, `an_enum_type()`; `a_table(unique_constraints=...)` |
| `backend/apps/spring_generator/tests/test_relationship_fields.py` | Create | DD23–DD27 |
| `backend/apps/spring_generator/tests/test_enum_fields.py` | Create | DD28, DD29 |
| `backend/apps/spring_generator/tests/test_enum_source.py` | Create | DD30–DD33 |
| `backend/apps/spring_generator/tests/test_rejections.py` | Modify | DD34, DD35 — rewrite the order tests |
| `backend/apps/spring_generator/tests/test_determinism.py` | Modify | Widen strategies to FK/enum tables; `len(fields) == len(columns)` (DD36) |
| `docs/ai/{CURRENT_STATE,NEXT_STEPS,DECISIONS_LOG}.md` | Modify | `rules.design` dual-documentation convention: record DD23–DD36 |

## Testing Strategy

Strict TDD (RED → GREEN → REFACTOR), `pytest` + `hypothesis`, no DB fixtures. One module
per new mapping concern, mirroring the existing `spring_generator/tests/` convention
(module docstring naming the DDs covered, `a_table()`-based fixtures, structural `.java`
assertions only — no `javac`, no Java parser, per proposal D2).

| Layer | Module | What to test |
|---|---|---|
| Unit | `test_relationship_fields.py` | Plain FK → `@ManyToOne` + `@JoinColumn(name, nullable)`; FK matching a `UniqueConstraint` → `@OneToOne` + `unique = true` (DD24); **self-referencing** FK generates its own class as the field type with no import and no error (DD27); two FKs to the same table → two distinct field names (DD26); DD16 join-table shape → exactly two `@ManyToOne` fields, no `@ManyToMany`/`@JoinTable` anywhere; **no `@Column`** on a relationship field and **no leftover scalar field** (`len(fields) == len(columns)`, DD23, DD25); `referencedColumnName` never emitted; `ManyToOne`/`OneToOne`/`JoinColumn` imports present only when used; `<base_package>.*` group empty on the entity (DD27); `relationship_base_name` unit table incl. `id`, no-suffix, and `class_id` → `class_` |
| Unit | `test_enum_fields.py` | Field type is `pascal_case(enum_type_name)`; `@Enumerated(EnumType.STRING)` present and `ORDINAL` never appears; DD11 order `@Enumerated` before `@Column` before `@NotNull` (DD29); `@Column(name, nullable)` still emitted; `@Size` never emitted; nullable enum column gets no `@NotNull`; `Enumerated`/`EnumType` imports conditional; an enum column does not raise through `java_type_for` (DD28) |
| Unit | `test_enum_source.py` | Path `.../domain/<Pascal>.java` and matching `package` line; custom `base_package` honored, invalid one raises `ValueError` (DD20); parametrized DD31 table (`in_progress`, `InProgress`, `in-progress`, `IN PROGRESS` → `IN_PROGRESS`); `getLabel()` returns the **verbatim** label (DD32); no annotation and no `com.fasterxml.jackson` substring anywhere (DD19); last constant terminated by `;`, others by `,`; braces balanced; `generate_enum_source(e) == generate_enum_source(e)` (determinism, DD36); empty `labels` → `EmptyEnumTypeError`; colliding labels → `DuplicateEnumConstantError`; label `"1st"` → `InvalidJavaIdentifierError`; all three subclass `UngeneratableSourceError` |
| Unit | `test_rejections.py` (rewrite) | New fixed order PK → composite-FK → discriminator → unnamed-ENUM (DD35), one test per adjacent pair; composite FK → `CompositeForeignKeyUnsupportedError` with first-offender attributes (DD34); **single-column FK raises nothing**; **named enum column raises nothing**; `ENUM` without `enum_type_name` → `UnsupportedColumnTypeError`; every table error still subclasses `UngeneratableTableError` *and* `UngeneratableSourceError` (DD33); no partial output on rejection |
| Property | `test_determinism.py` (extend) | `hypothesis` strategies widened to FK-bearing and enum-bearing tables: `generate(t) == generate(t)` byte-identical; field order == `table.columns` order and `len(fields) == len(columns)` (DD23, DD36); imports deduped/grouped/sorted; braces and parentheses balanced |
| Guard | `test_no_concat_guard.py` (unchanged) | Must stay green over the modified `emit/` modules — `relationship_base_name` and `screaming_snake_case` use `re.sub`/`.upper()` only (DD26, DD31) |
| Integration / E2E | — | N/A — no endpoint, no WS, no DB, no filesystem (DD3) |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. Both functions remain pure in-process transformations that
open no file, spawn no process, and write nothing to disk (DD3). The one adjacent concern —
user-supplied UML enumeration labels and relationship names flowing verbatim into emitted
`.java` text — is closed structurally by routing **every** new identifier through DD16's
whitelist (DD26, DD31), not by escaping. The one value that reaches emitted source *without*
identifier conversion is DD32's preserved label inside a Java string literal; it is covered by
`test_enum_source.py`'s brace-balance and structural assertions.

## Sequence-Diagram Rule

`openspec/config.yaml` `rules.design` requires sequence diagrams for realtime/collaboration
flows (Django Channels). No realtime flow exists in this scope; the two-pipeline diagram in
**Technical Approach** is included instead as the only non-obvious control flow.

## Migration / Rollout

No migration required. No models, no tables, no persisted data, no on-disk artifacts. The one
source-compatibility break is DD34's `ForeignKeysUnsupportedError` → `CompositeForeignKeyUnsupportedError`
rename, whose only consumers are inside this app. Rollback = revert this change's commits.

## Open Questions

- [ ] **DD32 persisted-value divergence.** `@Enumerated(STRING)` stores `name()` (`IN_PROGRESS`),
      not the source label (`in_progress`). Self-consistent inside a generated project, but a
      future DDL/`CHECK`-constraint emitter reading `EnumType.labels` must either apply DD31 or
      read `getLabel()`. Revisit if and when an `AttributeConverter` or DTO slice lands.
- [ ] **DD26 name collision.** A FK column `category_id` and a sibling scalar column literally
      named `category` both produce a field `category`. Same class as the already-documented
      cross-artifact `Order`-table-vs-`Order`-enum collision: detection belongs to the future
      orchestrating caller that sees a whole `RelationalModel`, not to a one-`Table` function.
- [ ] Bidirectional `@OneToMany` inverse collections stay out of scope (proposal constraint 1);
      they require the whole `RelationalModel`, which is a real API-shape change.
- [ ] Single Table inheritance generation remains blocked on `Column` having no owning-class
      attribution (exploration Open Question 1); DD35 keeps the discriminator rejection in place.
- [ ] `unique_constraints` are now *read* (DD24) but still not *emitted* as
      `@Table(uniqueConstraints = ...)`; `indexes` remain ignored. Unchanged tech debt.

> Size note: this artifact exceeds the skill's 800-word soft budget, matching the explicit
> tradeoff recorded by the archived core cycle's design. `sdd-tasks` needs the full
> FK/enum annotation table and the DD35 rejection order to slice implementable units without
> re-deriving them.
