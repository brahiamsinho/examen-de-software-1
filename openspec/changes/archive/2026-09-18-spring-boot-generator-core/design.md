# Design: Spring Boot generator core — first slice (spec §22, item 12)

## Technical Approach

Exploration Approach 1 narrowed by proposal D4: one new Django app
`backend/apps/spring_generator/` acting purely as a registration shell (`apps.py` only),
mirroring `relational_mapping` one cycle later in the same pipeline. Two layers,
one-directional, neither importing Django, Ninja, Pydantic, nor any DB driver:

```
  emit/     (errors, naming, javatypes, context, renderer, templates/*.java.j2)
      │  reads
      ▼
  domain/   (sources)  ← leaf: frozen GeneratedFile / GeneratedSources
      ▲
      └── apps.relational_mapping.domain  (Table/Column — read-only, never mutated)
```

The only cross-app edge is `spring_generator → relational_mapping.domain`. Nothing imports
`spring_generator`; no models, no migrations, no filesystem writes, no subprocess, no JVM.

```
caller (future: item 13 project writer)
   │
   ▼
generate_table_sources(table: Table, *, base_package="com.modelia.generated") -> GeneratedSources
   │
   ├─1 _reject_out_of_scope(table)   → UngeneratableTableError subclasses (DD15), before any render
   ├─2 _build_context(table, pkg)    → frozen EntityContext / RepositoryContext (plain dicts for Jinja2)
   ├─3 render Entity.java.j2         → src/main/java/<pkg>/domain/<Entity>.java
   └─4 render Repository.java.j2     → src/main/java/<pkg>/persistence/<Entity>Repository.java
```

Stage 1 is total and eager: a rejected `Table` never produces partial output.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | New app `apps.spring_generator` (label `spring_generator`), registration shell `apps.py` only, no `models.py`, no `migrations/`; `domain/` (output shape) + `emit/` (algorithm) split | Put the generator inside `relational_mapping`; a flat module | App-per-domain convention (user preference, Cycles 1–15). `relational_mapping` owns the *relational* shape; Java emission is a different bounded domain. The `domain/`+`emit/` split is `relational_mapping`'s `domain/`+`mapping/` verbatim. Caveat recorded: the generator's Python `domain/` package and the *emitted* Java `domain/` package are different things |
| DD2 | Jinja2 templates live at `emit/templates/*.java.j2`, **never** app-root `templates/`; loaded with `FileSystemLoader(Path(__file__).parent / "templates")` | App-root `templates/`; inline template strings | Django's `APP_DIRS` template loader scans `<app>/templates/` — placing `Entity.java.j2` there would expose Java templates to Django's own template resolution. `emit/templates/` is invisible to that loader. Inline strings would re-introduce the string-assembly §22 forbids |
| DD3 | Public API is a **pure function returning in-memory sources**; the generator never touches the filesystem | Writing into a `tmp_path`/temp dir and returning the root | Mirrors `map_to_relational`'s purity. Tests compare values (`assert sources == sources`) with no I/O, teardown, or path-normalization noise; determinism becomes a plain equality assertion. Writing a project tree is item 13's concern and is trivially testable separately |
| DD4 | Output contract is frozen `GeneratedFile(path: str, contents: str)` + `GeneratedSources(files: tuple[...])` with a derived `as_mapping() -> Mapping[str, str]`; `path` is always POSIX-relative | Returning a bare `dict[str, str]` | Carries `relational_mapping` DD2 forward (frozen, tuple-ordered, comparable, hashable-by-value). A bare dict gives no home for later metadata (base package, layer) and no ordering guarantee. `as_mapping()` keeps dict-style assertions cheap. POSIX paths keep output identical on Windows and Linux |
| DD5 | **Boxed Java types only, never primitives** (`Integer`/`Long`/`Boolean`, not `int`/`long`/`boolean`) | Primitives for non-nullable columns | A primitive cannot represent `nullable=True`, and JPA/Hibernate silently treat a primitive's zero-value as "set". Uniform boxing keeps the type table a pure function of `ColumnType` alone, independent of `nullable` |
| DD6 | **`TIMESTAMPTZ` → `java.time.OffsetDateTime`** | `LocalDateTime`; `Instant`; `java.util.Date` | The source column type is `timestamp **with** time zone`. Hibernate 6 maps `LocalDateTime` to plain `timestamp`, silently dropping the offset the relational model asserts. `OffsetDateTime` round-trips it; `Instant` round-trips the instant but loses the original offset |
| DD7 | **`TEXT` → `String` + `@Column(columnDefinition = "TEXT")`** | `@Lob`; `String` with no annotation | On PostgreSQL, Hibernate maps `@Lob String` to an OID large object requiring a transaction-scoped stream — a well-known trap. `columnDefinition = "TEXT"` is the direct, portable-enough expression of the column the mapper actually produced |
| DD8 | **PK annotations**: `@Id`, `@GeneratedValue(strategy = GenerationType.UUID)`, `@Column(name = "id", nullable = false, updatable = false)`, and **no `@NotNull`** | `@NotNull` on the PK too; `GenerationType.AUTO`; application-assigned UUIDs | `GenerationType.UUID` (JPA 3.1) matches `relational_mapping` DD5's unconditional synthetic UUID PK with no provider-specific generator. `@NotNull` on a provider-generated id fires Bean Validation on `persist()` *before* generation, rejecting every valid insert. `updatable = false` makes the synthetic identity immutable |
| DD9 | **Validation annotations**: `@NotNull` on every **non-PK** column with `nullable=False`; `@Size(max = <length>)` on `VARCHAR` columns that carry a `length`; **never `@NotBlank`** | `@NotBlank` for non-nullable strings; no Jakarta Validation at all | `@NotNull` is the exact Java statement of `nullable=False`. `@NotBlank` additionally rejects `""`, which the database accepts — that is a business rule the relational model never asserted, so emitting it would invent semantics. `@Size` mirrors `length` so validation fails before the DB truncation error |
| DD10 | **`@Column` always emits an explicit `name`**, then only the attributes that are actually present, in the fixed order `name, nullable, length, precision, scale, columnDefinition, updatable` | Rely on Hibernate's implicit naming strategy; always emit every attribute with JPA defaults | Explicit names decouple the emitted Java from whichever naming strategy the generated project configures, and keep the DB name intact when DD16 renames a field. Emitting only present attributes invents no defaults (JPA's own `length` default is already 255). A fixed attribute order is a determinism requirement, not cosmetics |
| DD11 | **Fixed per-field annotation order**: `@Id`, `@GeneratedValue`, `@Column`, `@NotNull`, `@Size` — one per line, built as an ordered `tuple[str, ...]` in the context | Order by annotation package; whatever order the builder happens to append | Same determinism criterion as DD12; a stable order also makes diffs between regenerations readable |
| DD12 | **Determinism**: field declaration order is `Table.columns` declaration order, unchanged and unsorted; imports are deduped and emitted in fixed group order (`java.*`, `jakarta.*`, `org.*`, `<base_package>.*`), lexicographic within each group | Sorting fields by name or by nullability; set-iteration order for imports | Carries `relational_mapping` DD9 forward verbatim — `Table.columns` already guarantees `id` first, then attribute columns in declaration order. Sorting would decouple the emitted class from the model the user drew. Import grouping is the only place a `set` appears, so it is the only place that needs an explicit ordering rule |
| DD13 | Jinja2 `Environment(loader=..., undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True, autoescape=False)`, constructed once at module import | Default `Undefined`; `autoescape=True`; a new `Environment` per call | `StrictUndefined` turns a missing context key into a loud failure instead of a silently-empty Java token. `autoescape` is HTML-specific and would corrupt Java string literals and generics. `trim_blocks`/`lstrip_blocks` keep the template readable while the output stays byte-stable |
| DD14 | **LibCST's concrete role is the D2 no-manual-concatenation guard**: `tests/no_concat_guard.py` parses every module under `emit/` with `libcst.parse_module` and fails on string `+` concatenation, `str.join`, `%`-formatting, or f-strings whose value flows into emitted source. It never parses Java and is never called at render time | Using LibCST to build the emitted Java (impossible — it is a Python CST library); using LibCST to build the template-context dict (a plain dict needs no CST); dropping LibCST entirely | Proposal D2 stated what LibCST is *not* for but left its actual caller unnamed. §22's real, enforceable constraint is "no manual string concatenation of source"; a CST walk over the generator's own modules is the only mechanical way to enforce it, and it gives `libcst` a genuine, executed role instead of a decorative dependency |
| DD15 | **Typed rejection hierarchy** in `emit/errors.py`: base `UngeneratableTableError` plus `UnsupportedPrimaryKeyError`, `ForeignKeysUnsupportedError`, `InheritanceUnsupportedError`, `UnsupportedColumnTypeError`, each carrying structured attributes and an `!r` message — checked eagerly in that fixed order before any rendering | Silently skipping unsupported columns; a single generic `ValueError`; returning a partial result plus warnings | Mirrors `relational_mapping/mapping/errors.py` exactly (base + attribute-carrying subclasses, defense-in-depth). D4's scope boundary must be *observable*: a caller handing in a FK-bearing table gets a named, catchable failure rather than an entity that silently lost a relationship. A fixed check order makes the first failure deterministic for a table that violates several rules at once |
| DD16 | **Java identifier safety**: `pascal_case`/`camel_case` accept only `[A-Za-z_][A-Za-z0-9_]*` after conversion; anything else raises `InvalidJavaIdentifierError`. A Java reserved word (`class`, `public`, `native`, …) gets a trailing `_` (a legal Java identifier), while DD10's explicit `@Column(name = ...)` preserves the database name | Emitting the name verbatim; stripping offending characters silently; rejecting reserved words outright | UML class/attribute names are user input that flows into emitted source; a whitelist is the boundary that makes template injection into `.java` text structurally impossible. Silent stripping could collapse two distinct columns onto one field. Rejecting reserved words would make a legitimately-named attribute ungeneratable, so the `_` suffix is preferred and is fully reversible via `@Column(name=...)` |
| DD17 | **Repository** = `public interface <Entity>Repository extends JpaRepository<<Entity>, UUID> { }`, empty body, **no `@Repository` annotation** | `CrudRepository`; `JpaRepository` plus `@Repository`; hand-emitted CRUD method declarations | `JpaRepository` *is* proposal D3's hard-coded full CRUD (`save`/`findById`/`findAll`/`delete`) plus the pagination and sorting §23 will need, at zero emitted lines. `@Repository` is redundant — Spring Data's repository scanning registers the proxy regardless — and redundant annotations in generated code are noise a reviewer must re-justify every cycle |
| DD18 | **Entity shape**: `protected` no-arg constructor + explicit per-field getters and setters; **no Lombok**, and **no `equals`/`hashCode`** in this slice | Lombok `@Getter`/`@Setter`/`@Data`; records; generating `equals`/`hashCode` on the id | JPA requires an accessible no-arg constructor; `protected` satisfies Hibernate proxying while discouraging direct use. Lombok would add an annotation-processor dependency to every generated `build.gradle` and make the emitted source non-self-evident. JPA entity identity semantics (id-based `equals` is subtly wrong before flush) is a real design topic that deserves its own decision, not a default smuggled into slice 1 |
| DD19 | **No Jackson annotations emitted this slice** | `@JsonProperty`/`@JsonFormat` on entity fields | §22 lists Jackson "cuando corresponda"; serialization belongs to the `api/` DTO layer, which D4 puts out of scope. Annotating entities for JSON would bake an exposed-entity API shape into the first slice — the opposite of the layering §22 mandates |
| DD20 | **`base_package` is a validated keyword parameter**, default `"com.modelia.generated"`, matched against `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$`; paths are `src/main/java/<base_package as path>/{domain,persistence}/…`. **No `application.yml`, no host, port, URL, or credential appears in any template** | Hardcoding the package; deriving it from the organization/document name | Keeps the §22 layout explicit and the externalized-configuration constraint trivially satisfiable: this slice emits no configuration file at all, so there is nothing to hardcode. A validated parameter lets item 13 pass a real per-project package without changing this API |
| DD21 | **Dependencies**: `jinja2>=3.1,<4.0` → `backend/requirements/base.txt` (runtime); `libcst>=1.4,<2.0` → `backend/requirements/test.txt` (DD14 guard only), each with a comment naming its consumer | Both in `base.txt`; both in `test.txt` | Follows `base.txt`'s existing commented-dependency precedent (`redis`, `email-validator`). Jinja2 is imported by shipped emitter code; LibCST is imported only by the guard the suite runs, so shipping it in the production image would be dead weight. `dev.txt` already pulls `-r test.txt`, so developers get both |
| DD22 | The new app gets its **own** `tests/factories.py`, importing only `apps.relational_mapping.domain` — never `apps.relational_mapping.tests.factories` | Reusing the relational-mapping test factories | Carries `relational_mapping` DD20 forward: `backend/apps/README.md` forbids cross-app imports, and a cross-app *test-package* dependency is the same coupling. Generator scenarios need `a_table()`/`a_column()` builders that start from `Table`, not from `CanonicalUmlModel` |

## Interfaces / Contracts

```python
# domain/sources.py                                  (frozen, DD4)
@dataclass(frozen=True) class GeneratedFile:
    path: str          # POSIX-relative, e.g. "src/main/java/com/modelia/generated/domain/Order.java"
    contents: str

@dataclass(frozen=True) class GeneratedSources:
    files: tuple[GeneratedFile, ...] = ()
    def as_mapping(self) -> Mapping[str, str]: ...     # derived view, insertion-ordered
    def file_by_path(self, path: str) -> GeneratedFile | None: ...

# emit/errors.py                                     (scope guards, DD15)
class UngeneratableTableError(Exception): ...                 # base
class UnsupportedPrimaryKeyError(UngeneratableTableError)     # table_name, column_names, reason
class ForeignKeysUnsupportedError(UngeneratableTableError)    # table_name, foreign_key_names
class InheritanceUnsupportedError(UngeneratableTableError)    # table_name, discriminator_column
class UnsupportedColumnTypeError(UngeneratableTableError)     # table_name, column_name, column_type
class InvalidJavaIdentifierError(UngeneratableTableError)     # source_name, converted       (DD16)

# emit/naming.py                                     (DD16)
def pascal_case(snake: str) -> str        # "order_line" -> "OrderLine"
def camel_case(snake: str) -> str         # "order_line" -> "orderLine"
def package_path(base_package: str) -> str   # "com.modelia.generated" -> "com/modelia/generated"

# emit/javatypes.py                                  (DD5-DD7, the table below)
@dataclass(frozen=True) class JavaType:
    name: str                  # simple name used in the field declaration
    import_fqn: str | None     # None for java.lang types

# emit/renderer.py                                   (public API, DD3)
def generate_table_sources(
    table: Table, *, base_package: str = "com.modelia.generated"
) -> GeneratedSources: ...
```

### Column type → Java type → JPA annotations (DD5–DD10)

Covers every member of `relational_mapping.domain.types.ColumnType`. `<n>` = `column.name`,
`nullable` is `column.nullable`, and an attribute is emitted only when its source value is not
`None`.

| `ColumnType` | Java type | Import | `@Column(...)` | Jakarta Validation |
|---|---|---|---|---|
| `UUID` **(the PK)** | `UUID` | `java.util.UUID` | `name = "id", nullable = false, updatable = false`, preceded by `@Id` + `@GeneratedValue(strategy = GenerationType.UUID)` | **none** (DD8) |
| `UUID` (non-PK) | `UUID` | `java.util.UUID` | `name = "<n>", nullable = <nullable>` | `@NotNull` when not nullable |
| `VARCHAR` | `String` | — (`java.lang`) | `name = "<n>", nullable = <nullable>, length = <length>` | `@NotNull` when not nullable; `@Size(max = <length>)` when `length` is set |
| `TEXT` | `String` | — (`java.lang`) | `name = "<n>", nullable = <nullable>, columnDefinition = "TEXT"` (DD7) | `@NotNull` when not nullable |
| `INTEGER` | `Integer` | — (`java.lang`) | `name = "<n>", nullable = <nullable>` | `@NotNull` when not nullable |
| `BIGINT` | `Long` | — (`java.lang`) | `name = "<n>", nullable = <nullable>` | `@NotNull` when not nullable |
| `NUMERIC` | `BigDecimal` | `java.math.BigDecimal` | `name = "<n>", nullable = <nullable>, precision = <precision>, scale = <scale>` | `@NotNull` when not nullable |
| `BOOLEAN` | `Boolean` | — (`java.lang`) | `name = "<n>", nullable = <nullable>` | `@NotNull` when not nullable |
| `DATE` | `LocalDate` | `java.time.LocalDate` | `name = "<n>", nullable = <nullable>` | `@NotNull` when not nullable |
| `TIMESTAMPTZ` | `OffsetDateTime` (DD6) | `java.time.OffsetDateTime` | `name = "<n>", nullable = <nullable>` | `@NotNull` when not nullable |
| `ENUM` | — | — | — | **rejected**: `UnsupportedColumnTypeError` (D4, DD15) |

Fixed annotation imports: `jakarta.persistence.{Entity, Table, Id, GeneratedValue, GenerationType, Column}`
on every entity; `jakarta.validation.constraints.{NotNull, Size}` only when at least one such
annotation is emitted.

### Rejection rules (DD15) — evaluated in this order

| Condition on the input `Table` | Raised |
|---|---|
| `len(primary_key.column_names) != 1`, or the PK column is missing, or its type is not `ColumnType.UUID` | `UnsupportedPrimaryKeyError` |
| `table.foreign_keys` is non-empty | `ForeignKeysUnsupportedError` |
| `table.discriminator_column is not None` (or `discriminator_values` non-empty) | `InheritanceUnsupportedError` |
| any column has `type is ColumnType.ENUM` (first offender in `columns` order) | `UnsupportedColumnTypeError` |
| a table or column name does not convert to a legal Java identifier | `InvalidJavaIdentifierError` |

`unique_constraints` and `indexes` are **accepted and ignored** in this slice (they carry no
relationship semantics and are DDL concerns); this is recorded as explicit tech debt below.

### Templates (DD2, DD13) — `emit/templates/`

```jinja
{# Entity.java.j2 (abbreviated) — every value is pre-computed in the context; #}
{# the template contains no conditionals over ColumnType and builds no identifier. #}
package {{ package }};

{% for group in import_groups %}{% for fqn in group %}import {{ fqn }};
{% endfor %}
{% endfor %}@Entity
@Table(name = "{{ table_name }}")
public class {{ class_name }} {
{% for field in fields %}
{% for annotation in field.annotations %}    {{ annotation }}
{% endfor %}    private {{ field.java_type }} {{ field.name }};
{% endfor %}
    protected {{ class_name }}() {
    }
{% for field in fields %}
    public {{ field.java_type }} {{ field.getter }}() {
        return this.{{ field.name }};
    }

    public void {{ field.setter }}({{ field.java_type }} {{ field.name }}) {
        this.{{ field.name }} = {{ field.name }};
    }
{% endfor %}}
```

`Repository.java.j2` is the DD17 one-liner interface over `{{ class_name }}` and `UUID`.
All branching (which annotations, which imports, which accessors) lives in `emit/context.py`,
so the templates stay data-driven and the guard in DD14 has a single surface to police.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/spring_generator/{__init__,apps}.py` | Create | Registration shell; `name="apps.spring_generator"`, `label="spring_generator"`. No `models.py`, no `migrations/` (DD1) |
| `backend/apps/spring_generator/domain/{__init__,sources}.py` | Create | Frozen `GeneratedFile`/`GeneratedSources` (DD4) |
| `backend/apps/spring_generator/emit/{__init__,errors,naming,javatypes,context,renderer}.py` | Create | Rejection hierarchy (DD15), identifier rules (DD16), type table (DD5–DD7), context builder, public `generate_table_sources` (DD3) |
| `backend/apps/spring_generator/emit/templates/{Entity,Repository}.java.j2` | Create | Jinja2 templates (DD2, DD13, DD17, DD18) |
| `backend/apps/spring_generator/tests/**` | Create | `factories.py` (DD22), `no_concat_guard.py` (DD14) + one module per concern |
| `backend/config/settings.py` | Modify | Add `"apps.spring_generator"` under the `# Local` marker in `INSTALLED_APPS`, after `"apps.relational_mapping"` |
| `backend/requirements/base.txt` | Modify | `jinja2>=3.1,<4.0` + comment (DD21) |
| `backend/requirements/test.txt` | Modify | `libcst>=1.4,<2.0` + comment (DD21) |
| `docs/ai/{CURRENT_STATE,DECISIONS_LOG}.md` | Modify | `rules.design` dual-documentation convention: record DD1–DD22 |

> `backend/pyproject.toml` already sets `testpaths = ["config", "apps"]`, so the new test
> directory is collected with zero configuration change. `backend/config/settings.py` is a
> module, not a package.

## Testing Strategy

Strict TDD (RED → GREEN → REFACTOR), `pytest` + `hypothesis`, no `pytest-django` DB fixtures —
the whole change is DB-free and filesystem-free (DD3). One module per concern, mirroring
`relational_mapping/tests/`. Per proposal D2, `.java` assertions are **structural only**
(expected paths, `package`/class/interface/field/annotation lines, brace balance) — no `javac`,
no Java parser.

| Layer | Module | What to test |
|---|---|---|
| Unit | `tests/test_apps.py` | AppConfig `name`/`label`; app is registered |
| Unit | `tests/test_sources.py` | Frozen shapes, `as_mapping()` ordering, `file_by_path`, mutation raises |
| Unit | `tests/test_naming.py` | `pascal_case`/`camel_case`/`package_path`; reserved word → `_` suffix with the DB name preserved; illegal name → `InvalidJavaIdentifierError` (DD16) |
| Unit | `tests/test_java_types.py` | All 9 supported `ColumnType` rows → Java type + import, incl. DD6 `OffsetDateTime` and DD7 `columnDefinition` |
| Unit | `tests/test_entity_identity.py` | PK gets `@Id` + `@GeneratedValue(strategy = GenerationType.UUID)` + `updatable = false`; PK gets **no** `@NotNull` (DD8) |
| Unit | `tests/test_column_annotations.py` | Explicit `name` always emitted; `length` only for `VARCHAR` with a length; `precision`/`scale` only for `NUMERIC`; absent values omitted, not defaulted (DD10) |
| Unit | `tests/test_validation_annotations.py` | `nullable=False` → `@NotNull`; `nullable=True` → none; `@Size(max=)` from `length`; `@NotBlank` never appears; validation imports present only when used (DD9) |
| Unit | `tests/test_entity_structure.py` | `@Entity`/`@Table(name=...)`, protected no-arg ctor, getter+setter per field, no Lombok, no `equals`/`hashCode`, no Jackson import (DD18, DD19) |
| Unit | `tests/test_repository.py` | `interface <E>Repository extends JpaRepository<<E>, UUID>`, empty body, no `@Repository`, correct entity import (DD17) |
| Unit | `tests/test_paths_and_package.py` | Both files at `src/main/java/<pkg path>/{domain,persistence}/…`; `package` declaration matches the path; custom `base_package` honored; invalid `base_package` rejected; no host/port/URL substring in any output (DD20) |
| Unit | `tests/test_rejections.py` | FK, discriminator, `ENUM` column, composite PK, non-UUID PK each raise their named error; all subclass `UngeneratableTableError`; fixed check order when several rules are violated; no partial output (DD15) |
| Property | `tests/test_determinism.py` | `hypothesis`: (a) `generate(t) == generate(t)`; (b) field order == `table.columns` order; (c) imports deduped, grouped, sorted; (d) braces and parentheses balanced in every emitted file (DD12) |
| Unit | `tests/test_no_manual_concatenation.py` | LibCST guard over every module in `emit/` fails on string `+`, `.join`, `%`, or source-bearing f-strings (DD14, proposal D2) |
| Integration / E2E | — | N/A — no endpoint, no WS, no DB, no filesystem in this cycle |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. The generator is a pure in-process function: it opens no file,
spawns no process, performs no I/O, and writes nothing to disk (DD3). The one adjacent concern —
user-supplied UML names flowing verbatim into emitted `.java` text — is closed structurally by
DD16's identifier whitelist, not by escaping, and is covered by `tests/test_naming.py`.

## Sequence-Diagram Rule

`openspec/config.yaml` `rules.design` requires sequence diagrams for realtime/collaboration flows
(Django Channels). No realtime flow exists in this scope; the 4-stage pipeline diagram above is
included instead as the only non-obvious control flow.

## Migration / Rollout

No migration required. No models, no tables, no persisted data, no API consumers, no generated
artifacts on disk. Rollback = delete `backend/apps/spring_generator/`, revert the single
`INSTALLED_APPS` line and the two requirements lines.

## Open Questions

- [ ] **§22 names LibCST as a generation mechanism, but LibCST is a Python-only CST library and
      this generator emits Java.** DD14 gives it the only honest, executed role available
      (enforcing §22's own no-concatenation rule). If the spec author intended LibCST to *emit*
      something, that something must be Python — a later cycle's generated Python client, not
      item 12. Confirm at verify.
- [ ] `unique_constraints` and `indexes` are accepted and silently ignored (they would become
      `@Table(uniqueConstraints = ...)` / `@Index`). Tech debt, deliberately deferred so slice 1
      stays at one entity + one repository.
- [ ] JPA entity `equals`/`hashCode` semantics (DD18) need their own decision before the
      `application/` layer starts putting entities into collections.
- [ ] SQL reserved words (`order`, `user`, `group`) still reach `@Table(name=...)`/`@Column(name=...)`
      unquoted — this closes the archived `uml-relational-mapping` design's first open question
      only partially. Quoting bites at DDL time, so it belongs to item 13 (compilation), where a
      real schema is produced.
- [ ] `base_package` default `com.modelia.generated` is a placeholder; item 13 will likely derive
      it per generated project.

> Size note: this artifact exceeds the skill's 800-word soft budget, matching the explicit
> tradeoff recorded in the `uml-relational-mapping` design. `sdd-tasks` needs the full
> column-type/annotation table and the rejection-order table to slice implementable units
> without re-deriving them.
