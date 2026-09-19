# Design: Spring Boot generator — JPA Single Table inheritance domain slice

> Extends the archived Spring Boot generator cycles through the current six-file application/API generator.
> This change is bounded to discriminator-backed `Table` inputs and emits only domain classes plus one root repository.
> Non-discriminator table generation must remain byte-identical.

## Technical Approach

Add an inheritance branch to `generate_table_sources(table, *, base_package)` after the existing base-package validation and eager typed rejection checks. The public signature stays unchanged and the function remains pure, DB-free, filesystem-free, and text-only.

```text
generate_table_sources(table, *, base_package)
   ├─ validate base_package                                      [unchanged]
   ├─ reject_out_of_scope(table)
   │    ├─ always: PK shape → composite FK → unnamed enum checks
   │    └─ if discriminator metadata exists: supported inheritance shape checks
   ├─ if table.discriminator_column is None and no discriminator_values:
   │    └─ existing six-file path                                [byte-identical]
   └─ else:
        ├─ build_inheritance_context(table, base_package)
        ├─ render root entity from inheritance entity template/context
        ├─ render subclass entities in source_class_ids order
        └─ render root repository from existing Repository.java.j2
```

The implementation should avoid touching the existing non-discriminator context/template path except for routing around it. The safest shape is to add sibling inheritance context builders and either a new inheritance-capable entity template or a backward-compatible extension to `Entity.java.j2` that renders exactly the same bytes when inheritance metadata is absent.

## Architecture Decisions

| # | Decision | Rationale |
|---|---|---|
| DD51 | **Branch by discriminator only in `renderer.py`, after eager validation.** A discriminator-backed table enters the inheritance rendering path; a non-discriminator table executes the current six-file pipeline unchanged. | This preserves existing behavior and limits review scope to the new branch. It also prevents partial output because all rejection happens before any rendering. |
| DD52 | **Add inheritance-specific context structures instead of mutating `EntityContext` broadly.** Introduce `InheritanceHierarchyContext` and `InheritanceEntityContext`, while reusing `FieldContext`, `RepositoryContext`, `_group_imports`, and existing field-building helpers where safe. | Separate contexts make the new shape explicit and reduce risk of changing six-file output. Reusing `FieldContext` keeps field/getter/setter rendering and validation annotations consistent. |
| DD53 | **Root class id is `table.source_class_ids[0]`; subclass ids are the remaining ids in tuple order.** Generated file order is root entity, each subclass in this exact order, then root repository. | The spec defines the first source class id as root and requires deterministic hierarchy order. No sorting should be introduced because tuple order carries mapper intent. |
| DD54 | **Class names come from class ids, not table name, for subclasses; the root keeps the existing table-based name.** Root class name remains `pascal_case(table.name)`. Subclass class names use `pascal_case(class_id)` unless an upstream class-name mapping becomes available. | Current `Table` does not carry UML class display names per class id. This is an ambiguity, so this design records the fallback and flags it for resolution before tasks. Tests should use ids like `car`/`truck` where this is deterministic. |
| DD55 | **The root entity is concrete.** The class declaration is `public class Root` unless future UML metadata exposes abstract-class semantics. | This matches the proposal's resolved assumption and avoids inventing model semantics. |
| DD56 | **The discriminator column is metadata only.** It renders as `@DiscriminatorColumn(name = "...")` on the root and never as a Java field in any entity. | JPA owns discriminator values internally for Single Table inheritance; emitting a normal field would double-map the same column and violate the spec. |
| DD57 | **`@DiscriminatorValue` is mandatory for every generated hierarchy class after validation.** Root and subclasses read values from `table.discriminator_values[class_id]`. | The spec requires values for every generated hierarchy id. Making the context total avoids optional template branches except where explicitly required by legacy wording. |
| DD58 | **Field partitioning is ownership-first after structural-column detection.** PK column is assigned to the root. Discriminator column is skipped. Attribute/enum scalar columns with `owning_class_id == root_id` go to root; those with `owning_class_id == subclass_id` go to that subclass; ownership outside the hierarchy is rejected. | This directly implements ownership metadata and prevents duplication or field loss. Structural detection must happen before `owning_class_id is None` rejection so the synthetic id stays supported. |
| DD59 | **Single-column FK fields are supported only when they can be assigned to the root in this slice.** FK columns with no `owning_class_id` or `owning_class_id == root_id` may render on the root using the existing relationship field logic. FK columns owned by subclasses are rejected until relationship endpoint ownership is specified. | The proposal includes supported single-column relationship fields, but also declares subclass-owned relationship fields out of scope. Root-only FK support preserves existing relationship behavior without inventing subclass relationship placement. |
| DD60 | **Enum fields follow the existing enum branch within their assigned owner entity.** A named enum column renders as `@Enumerated(EnumType.STRING)` plus `@Column`; unnamed `ColumnType.ENUM` is rejected before rendering. | This preserves the existing enum contract while allowing inheritance field partitioning. |
| DD61 | **Unsupported unowned non-structural columns are rejected.** A non-PK, non-discriminator column with `owning_class_id is None` is accepted only if it is an assignable root-level single-column FK under DD59; otherwise it raises a typed malformed-inheritance error. | The mapper says attribute-derived columns carry ownership and synthetic/structural columns do not. Accepting arbitrary unowned scalar columns would hide mapper defects. |
| DD62 | **Use a new `MalformedInheritanceTableError` typed error for malformed supported-shape violations.** It should subclass `UngeneratableTableError` and carry `table_name`, `reason`, and optionally `class_id`/`column_name`. Keep `InheritanceUnsupportedError` only for explicitly unsupported inheritance features if retained. | The delta spec asks for typed malformed-inheritance errors. A single payload-rich class is enough for tests while avoiding an error-class explosion. |
| DD63 | **Validation check order is deterministic and first-offender-wins.** Order: primary key shape, composite FK, unnamed enum columns, then inheritance shape checks when discriminator metadata exists. Inheritance shape order: missing discriminator column, empty `source_class_ids`, missing root id, missing discriminator value in `source_class_ids` order, missing discriminator column in `columns`, unsupported owned column in `columns` order, unsupported subclass FK in `foreign_keys`/`columns` order. | Stable ordering makes tests reliable and keeps error reporting predictable. Moving discriminator rejection out of the old blanket slot is required so supported inheritance is accepted. |
| DD64 | **Imports are computed per generated entity.** Root imports include standard entity imports plus `Inheritance`, `InheritanceType`, `DiscriminatorColumn`, `DiscriminatorValue`, and only the field-related imports actually used. Subclasses include `Entity`, `DiscriminatorValue`, and their own field-related imports; they do not import the root because it is in the same package. | Per-class imports keep subclasses minimal and deterministic. The existing `_group_imports` ordering can be reused for lexicographic group stability. |
| DD65 | **Template strategy must protect exact legacy output.** Prefer a new `InheritanceEntity.java.j2` or pass explicit optional inheritance blocks whose defaults render nothing. Do not alter whitespace in `Entity.java.j2` for non-discriminator entities unless byte-identical tests prove it. | The highest compatibility risk is accidental whitespace/import drift in the existing six-file path. A separate template is the lowest-risk option. |
| DD66 | **Repository generation is reused exactly for the root entity.** The inheritance branch builds a `RepositoryContext` for the root/table and renders the current `Repository.java.j2`, producing only `<Root>Repository extends JpaRepository<<Root>, UUID>`. | JPA polymorphism belongs to the root repository. Reusing the existing template avoids a second repository contract. |
| DD67 | **No DTO/service/controller/error/config/validation artifacts are rendered for discriminator-backed tables.** The inheritance branch returns `GeneratedSources(files=(root, subclasses..., repository))` only. | This enforces the approved bounded slice and prevents premature polymorphic API design. |
| DD68 | **No Java compilation proof in this slice.** Tests assert text shape, deterministic order, import lines, field partitioning, and typed rejection. | The proposal explicitly keeps generated Java compilation infrastructure out of scope. |

## Data and Context Structures

Recommended additions in `backend/apps/spring_generator/emit/context.py` or a small sibling `inheritance_context.py` imported by `renderer.py`:

```python
@dataclass(frozen=True)
class InheritanceEntityContext:
    package: str
    class_name: str
    table_name: str | None              # root only
    extends_class_name: str | None       # subclass only
    discriminator_column: str | None     # root only
    discriminator_value: str
    fields: tuple[FieldContext, ...]
    import_groups: tuple[tuple[str, ...], ...]

@dataclass(frozen=True)
class InheritanceHierarchyContext:
    root: InheritanceEntityContext
    subclasses: tuple[InheritanceEntityContext, ...]
    repository: RepositoryContext
```

Helper contracts:

```python
def table_has_inheritance_metadata(table: Table) -> bool: ...
def reject_malformed_inheritance(table: Table) -> None: ...
def build_inheritance_hierarchy_context(table: Table, *, base_package: str) -> InheritanceHierarchyContext: ...
```

The field builder should be factored so both normal and inheritance contexts can build one column into one `FieldContext` with the existing precedence: PK → FK → named enum → scalar. The inheritance partitioner decides which columns are passed to that builder.

## Validation and Typed Errors

### Error hierarchy

```python
class MalformedInheritanceTableError(UngeneratableTableError):
    table_name: str
    reason: str
    class_id: ElementId | None
    column_name: str | None
```

Suggested reason strings for stable tests:

| Reason | Trigger |
|---|---|
| `discriminator_column_required` | `discriminator_values` exists but `discriminator_column is None` |
| `source_class_ids_required` | discriminator-backed table has empty `source_class_ids` |
| `discriminator_column_missing` | named discriminator column is not present in `table.columns` |
| `discriminator_value_required` | any id in `source_class_ids` lacks a discriminator value |
| `unknown_column_owner` | `Column.owning_class_id` is outside `source_class_ids` |
| `unowned_column_unsupported` | non-PK, non-discriminator, non-root-FK column has no owner |
| `subclass_relationship_unsupported` | FK column is owned by a subclass |

### Check order

1. Existing primary-key check: exactly one UUID PK.
2. Existing composite-FK check: every FK has exactly one column.
3. Existing unnamed enum check: `ColumnType.ENUM` requires `enum_type_name`.
4. If no inheritance metadata exists, return accepted for normal generation.
5. If inheritance metadata exists, validate supported Single Table shape in stable order:
   - `discriminator_column` is present;
   - `source_class_ids` is non-empty;
   - discriminator column exists in `columns`;
   - every hierarchy class id has a discriminator value, iterating `source_class_ids` order;
   - every owned column owner is in the hierarchy;
   - every FK column is root-assignable under DD59;
   - every remaining unowned non-structural column is rejected.

## Field Partitioning Rules

| Column shape | Root entity | Subclass entity | Notes |
|---|---:|---:|---|
| Primary key column | yes | no | Always root; includes `@Id`, `@GeneratedValue`, `@Column(... updatable = false)`. |
| Discriminator column | no | no | Metadata only through `@DiscriminatorColumn`. |
| Root-owned scalar column | yes | no | `owning_class_id == root_id`. |
| Subclass-owned scalar column | no | matching subclass only | `owning_class_id == subclass_id`. |
| Named enum column | owner-dependent | owner-dependent | Uses existing enum field annotations. |
| Single-column FK, root-owned or unowned | yes | no | Uses existing `@ManyToOne`/`@OneToOne` logic. |
| Single-column FK, subclass-owned | rejected | rejected | Unsupported until relationship ownership metadata is specified. |
| Non-structural unowned scalar | rejected | rejected | Prevents silent mapper defects. |
| Composite FK | rejected | rejected | Existing out-of-scope shape. |

Field order within each class should preserve `table.columns` order filtered to that class. This maintains model declaration order and avoids extra sorting.

## Template Strategy

Preferred template: `InheritanceEntity.java.j2`.

Root rendering shape:

```java
package <base>.domain;

<imports>
@Entity
@Table(name = "Vehicle")
@Inheritance(strategy = InheritanceType.SINGLE_TABLE)
@DiscriminatorColumn(name = "class_type")
@DiscriminatorValue("VEHICLE")
public class Vehicle {
    ...root fields...
}
```

Subclass rendering shape:

```java
package <base>.domain;

<imports>
@Entity
@DiscriminatorValue("CAR")
public class Car extends Vehicle {
    ...car-owned fields only...
}
```

Getter/setter/constructor rendering should mirror the current `Entity.java.j2` exactly for fields. If a shared template macro is introduced, its output must be regression-tested against current output to protect byte identity.

## Import Handling

Root fixed imports:

- `jakarta.persistence.Column`
- `jakarta.persistence.DiscriminatorColumn`
- `jakarta.persistence.DiscriminatorValue`
- `jakarta.persistence.Entity`
- `jakarta.persistence.GeneratedValue`
- `jakarta.persistence.GenerationType`
- `jakarta.persistence.Id`
- `jakarta.persistence.Inheritance`
- `jakarta.persistence.InheritanceType`
- `jakarta.persistence.Table`

Subclass fixed imports:

- `jakarta.persistence.DiscriminatorValue`
- `jakarta.persistence.Entity`

Conditional imports remain the same as current entity generation:

- Java type imports such as `java.util.UUID` and `java.math.BigDecimal` when used by fields;
- `jakarta.validation.constraints.NotNull` when any field uses `@NotNull`;
- `jakarta.validation.constraints.Size` when any field uses `@Size`;
- `jakarta.persistence.ManyToOne`, `OneToOne`, `JoinColumn` when root FK fields use them;
- `jakarta.persistence.Enumerated`, `EnumType` when enum fields use them.

Do not import same-package domain types for root/subclass relationships or enum classes.

## Deterministic Output Ordering

The inheritance branch must return files in this exact order:

1. `src/main/java/<pkg>/domain/<Root>.java`
2. `src/main/java/<pkg>/domain/<Subclass1>.java`
3. `src/main/java/<pkg>/domain/<Subclass2>.java`
4. `...`
5. `src/main/java/<pkg>/persistence/<Root>Repository.java`

Subclass order is `table.source_class_ids[1:]`, not alphabetic order. Field order is `table.columns` order filtered by owning class and structural role. Import order remains `_group_imports` group order and lexicographic sort within each group.

## Preservation of Exact Non-Discriminator Output

Implementation must protect the current non-discriminator path as a no-op:

- no new keys passed to existing templates unless defaults produce byte-identical text;
- no whitespace edits to `Entity.java.j2`, `Repository.java.j2`, DTO, service, or controller templates for this slice;
- no change to six-file order for non-discriminator tables;
- no change to DTO/service/controller contexts for non-discriminator tables;
- add a golden or fixture-based regression comparing a representative non-discriminator `Product` generation before/after the inheritance branch.

## Focused Test Strategy

Add tests under `backend/apps/spring_generator/tests/` without adding Java compilation tooling.

### Context/unit tests

- `build_inheritance_hierarchy_context` partitions root-owned and subclass-owned scalar fields correctly.
- PK appears only in root context.
- Discriminator column appears in no field context.
- Named enum field imports/annotations appear on the owning entity only.
- Root-owned FK renders as the existing relationship field shape.
- Subclass-owned FK raises `MalformedInheritanceTableError`.

### Renderer tests

- Supported `Vehicle` table emits exactly `Vehicle.java`, `Car.java`, `Truck.java`, and `VehicleRepository.java`.
- Root entity contains `@Inheritance(strategy = InheritanceType.SINGLE_TABLE)`, `@DiscriminatorColumn(name = "class_type")`, and `@DiscriminatorValue("VEHICLE")`.
- Alternate discriminator column name such as `kind` renders in metadata and no `kind` field exists.
- Subclasses contain `extends Vehicle`, own `@DiscriminatorValue`, no id field, and no root/subclass sibling fields.
- No inheritance output path is under `application/`, `application/dto/`, `api/`, `errors/`, `validation/`, or `config/`.
- Root repository extends `JpaRepository<Vehicle, UUID>` and no subclass repositories exist.
- Repeated generation returns byte-identical file contents in identical order.

### Rejection tests

- Empty `source_class_ids` raises `MalformedInheritanceTableError`.
- Missing discriminator value for any class id raises with that `class_id`.
- Missing discriminator column in `columns` raises typed error.
- `owning_class_id` outside the hierarchy raises typed error with `column_name`.
- Non-structural unowned scalar raises typed error.
- Composite FK remains rejected before inheritance checks.
- Unnamed enum remains rejected before inheritance checks.

### Backward-compatibility tests

- Existing non-discriminator tests continue to pass unchanged.
- Add one explicit byte-identical six-file regression fixture for a non-discriminator table with scalar, enum, and single-column FK fields.
- Property determinism tests either keep discriminator tables in a separate strategy or explicitly assert the two different file-order contracts.

## Unsupported Shapes in This Slice

- DTOs, services, controllers, OpenAPI, Postman, Domain Manifest, validation/config artifacts for inheritance tables.
- Subclass repositories.
- Subclass-owned relationship fields.
- Composite primary keys and non-UUID primary keys.
- Composite foreign keys.
- Whole-model orchestration or cross-artifact Java class-name collision detection.
- Abstract root/subclass generation.
- Bidirectional collections, `@OneToMany`, `@ManyToMany`, and join-table inheritance semantics.
- Java compilation verification.

## Spec Ambiguities to Resolve Before Tasks

1. **Subclass Java class names.** `Table.source_class_ids` contains ids, not display names. The examples imply `car` → `Car`, but real `ElementId` values may be opaque. Tasks need either a class-id-to-name mapping or explicit approval of `pascal_case(class_id)` for this slice.
2. **Root-owned single-column FK support in inheritance.** The delta spec mentions supported single-column relationship fields, while the proposal says subclass-owned relationship fields are deferred. This design supports root-owned/unowned FKs only; tasks should confirm that boundary.
3. **Unowned non-PK columns.** The proposal says columns without `owning_class_id` are root-level only for supported structural columns. The delta mentions columns assignable to root. Tasks should confirm that unowned scalar attributes are always malformed and not implicitly root-owned.
4. **Tables with `discriminator_values` but no `discriminator_column`.** This design treats any discriminator metadata as inheritance intent and raises malformed inheritance. Tasks should confirm this rather than falling back to normal generation.
5. **Root discriminator value optionality.** One requirement says root includes `@DiscriminatorValue` when present, while the supported shape requires values for every generated class id. This design makes it mandatory after validation.
6. **Name collision handling.** Whole-model class-name collision detection is out of scope, but a single table could map subclass ids to duplicate `pascal_case` names. Tasks should decide whether to reject duplicates within one hierarchy now.

## Rollout Plan

1. Add focused tests for inheritance validation and rendering while keeping production untouched until tasks begin.
2. Implement typed malformed-inheritance validation first.
3. Add inheritance contexts and field partitioning helpers.
4. Add the inheritance entity template and renderer branch.
5. Run existing spring generator tests and confirm non-discriminator byte identity.

## Review Notes

This design should fit a single bounded implementation PR if tests are focused. If the inheritance template plus validation tests push the review over the 400-line budget, pause under the session's `ask-on-risk` strategy and split validation/context work from rendering/tests.
