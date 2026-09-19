# Design: Spring Boot generator — `application/` + `api/` layers for CRUD capabilities

> Extends the archived `2026-09-18-spring-boot-generator-core` (DD1–DD22) and
> `2026-09-18-spring-boot-generator-relationships-enums` (DD23–DD36) cycles.
> New decisions continue at **DD37**; every DD1–DD36 convention still holds unless a
> decision below names it explicitly. **DD48 amends DD18** — the only backwards-incompatible
> change in this cycle, and a compilation prerequisite, not a preference.

## Technical Approach

Proposal Approach 3, strictly additive except for DD48. `generate_table_sources(table, *, base_package)`
keeps its signature and grows from 2 emitted files to 6. A **third** public entry point is added for
the two per-project (not per-`Table`) error sources, mirroring DD30's `generate_enum_source` precedent:

```
generate_table_sources(table, *, base_package)            [signature unchanged]
   ├─1 reject_out_of_scope(table)          DD35 order, unchanged
   │     + reject_invalid_resource_path(table)  → InvalidResourcePathError   (DD45)
   ├─2 build_entity_context / build_repository_context      [unchanged]
   │   build_dto_context / build_service_context / build_controller_context  (DD37-DD47)
   └─3 render 6 templates, in this fixed file order:                        (DD50)
         domain/<E>.java                Entity.java.j2        [DD48: public no-arg ctor]
         persistence/<E>Repository.java Repository.java.j2    [UNCHANGED - proposal constraint]
         application/dto/<E>RequestDto.java   RequestDto.java.j2            (DD37, DD38)
         application/dto/<E>ResponseDto.java  ResponseDto.java.j2           (DD37, DD38)
         application/<E>Service.java    Service.java.j2                     (DD39, DD40, DD44)
         api/<E>Controller.java         Controller.java.j2                  (DD45-DD47)

generate_shared_error_sources(*, base_package) -> GeneratedSources          (DD42)
   ├─ errors/ResourceNotFoundException.java                                 (DD41)
   └─ errors/GlobalExceptionHandler.java                                    (DD43)
```

Both entry points stay pure, DB-free and filesystem-free (DD3), one-`Table`-at-a-time, with no
`validate()` call and no cross-table awareness beyond `ForeignKey.referenced_table`, which a
single `Table` already carries.

Layer dependency direction (never inverted):

    api/  ──→  application/  ──→  application/dto/  ──→  (nothing)
                   │                    ▲
                   ├──→ persistence/ ───┘ (repositories)
                   ├──→ domain/          (entities, enums)
                   └──→ errors/          (leaf, cross-cutting)

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD37 | **DTOs live in `application/dto/`**, a sub-package of `application/`, as **two** classes: `<E>RequestDto` and `<E>ResponseDto`. Exact paths `src/main/java/<pkg>/application/dto/<E>RequestDto.java` and `.../<E>ResponseDto.java`; package `<base_package>.application.dto` | A new top-level `dto/`; placing DTOs in `api/`; one combined `<E>Dto` | §22's directory list is literal and exhaustive; a top-level `dto/` would be an eighth directory §22 never names, while `application/dto/` **is** under `application/` and satisfies the layout verbatim. `api/` is rejected on layering: the service returns DTOs, so DTOs in `api/` would force `application/ → api/`, inverting §22's own layering. Two classes because DD8 made the PK provider-generated: a request carrying `id` is meaningless and a response omitting it is unusable, so one combined class would need an `id` that is required outbound and forbidden inbound — an untypable contract. Two classes also confine `@NotNull`/`@Size` to the type `@Valid` actually inspects. **Note for the §22 layout spec delta**: `application/`, `api/`, `application/dto/` and `errors/` are now produced; `validation/` and `config/` still MUST NOT be |
| DD38 | **DTO field rules.** `<E>ResponseDto` = one field per `table.columns`, declaration order (DD12). `<E>RequestDto` = the same, **minus the PK column**. A FK column becomes `UUID <camel_case(column.name)>` (e.g. `categoryId`), **never** the related entity type; an enum column keeps `pascal_case(enum_type_name)`; scalars keep their DD5–DD7 Java type. Request fields carry `@NotNull` (when `nullable=False`) and `@Size(max=)` (VARCHAR with `length`) forwarded from DD9; response fields carry **no** annotation at all. **No JPA annotation ever appears on a DTO** — no `@Column`, `@JoinColumn`, `@Enumerated`, `@Entity` | Reusing `relationship_base_name` (`category`) for the flat FK field; annotating response fields too; reusing `FieldContext` verbatim | The DD26 lesson applies directly: deriving the DTO field from the FK **column** (`billing_address_id` → `billingAddressId`) keeps two FKs to the same table distinct and a self-reference named by role, where `referenced_table` would collide. Keeping the `Id` suffix (not stripping it as DD26 does for the JPA field) is what makes `categoryId : UUID` and `category : Category` visibly different things and matches §27's flat-FK-id UI contract. Validation on the response would be dead weight Bean Validation never evaluates |
| DD39 | **`<E>Service`** in `<base_package>.application`, annotated `@Service`, **constructor injection** of every repository it needs, `private final` fields, class-level `@Transactional(readOnly = true)` with `@Transactional` on `create`/`update`/`delete`. Exactly six public methods: `create(<E>RequestDto) -> <E>ResponseDto`, `findById(UUID) -> <E>ResponseDto`, `update(UUID, <E>RequestDto) -> <E>ResponseDto`, `delete(UUID) -> void`, `list(Pageable) -> Page<<E>ResponseDto>`, `count() -> long` | Field `@Autowired`; `@Component`; separate `list(Sort)` and `list(Pageable)` overloads; returning entities | Constructor injection is Spring's own documented recommendation and the only form that makes the generated class constructible in a plain unit test. A separate `list(Sort)` is redundant: `Pageable` already **carries** a `Sort` (`PageRequest.of(page, size, sort)`), so one parameter covers both §23 capabilities and leaves the controller unambiguous. `list` is `repository.findAll(pageable).map(this::toResponseDto)` — `Page.map` is documented Spring Data, so pagination metadata survives the DTO conversion for free |
| DD40 | **FK resolution uses the related entity's repository, `findById(...).orElseThrow(...)`** — never `EntityManager.getReference()`. The service injects one `<Related>Repository` per **distinct** `fk.referenced_table`, deduplicated and ordered by first appearance in `table.foreign_keys`; a self-referencing FK resolves to the entity's **own** repository and is deduplicated against it, adding no second parameter. A **nullable** FK whose DTO value is `null` skips the lookup and sets `null` | `entityManager.getReference(Category.class, id)`; `repository.getReferenceById`; constructing a detached stub entity with only its id set | `getReference` returns a lazy proxy and does **not** verify existence at call time — it throws `EntityNotFoundException` later, at flush or first access, *inside* the transaction and outside any place the service can convert it into the typed 404 that proposal scope item 4 requires. An explicit `findById(...).orElseThrow(...)` is the only shape where the not-found check is where the design says it is. `referenced_table` is already on `ForeignKey`, so this needs no whole-`RelationalModel` awareness and the one-`Table` signature survives. The dedup rule is load-bearing: without it, two FKs to `address` would emit a duplicate constructor parameter (a Java compile error), and a self-reference would inject `EmployeeRepository` twice |
| DD41 | **One generic `ResourceNotFoundException(String resourceName, UUID id)` extending `RuntimeException`, in `<base_package>.errors`** — not one exception class per entity, and not in `application/` | `<E>NotFoundException` per entity; placing it in `application/`; reusing Spring's `EntityNotFoundException` | A per-entity exception would need one `@ExceptionHandler` per entity in the advice — but the advice is a **singleton** (DD42) generated with no knowledge of how many tables exist, so a per-entity hierarchy is structurally impossible under the one-`Table` signature. `errors/` (not `application/`) keeps the advice's import inside its own package and lets `application/` depend on `errors/` as a cross-cutting leaf rather than the reverse. Jakarta's `EntityNotFoundException` is a persistence-layer signal Hibernate also throws for unrelated proxy failures; a distinct type keeps the 404 mapping unambiguous |
| DD42 | **`generate_shared_error_sources(*, base_package) -> GeneratedSources`** is a new public entry point in `emit/renderer.py` taking **no `Table`**, reusing `_ENVIRONMENT`, `_validate_base_package` and `package_path`. It emits the two `errors/` files. `generate_table_sources` emits **only** per-`Table` files | Emitting the error sources from `generate_table_sources`; a fourth `emit/` module | The two `errors/` files are per generated **project**, not per table: emitting them from `generate_table_sources` would produce N byte-identical copies at the same path, and item 13's project writer would write that path N times. A `Table`-free entry point makes the singleton shape explicit in the type signature. `renderer.py` is already "the public API surface" (DD3) and DD30 already set the sibling-entry-point precedent rather than a new module that would split ownership of the single configured Jinja `Environment` |
| DD43 | **`GlobalExceptionHandler`** annotated **`@RestControllerAdvice`**, two handlers returning `ProblemDetail`: `@ExceptionHandler(ResourceNotFoundException.class)` → `ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage())`; `@ExceptionHandler(MethodArgumentNotValidException.class)` → `HttpStatus.BAD_REQUEST` with a `field -> message` map set via `setProperty("errors", …)`, built by a plain `for` loop over `ex.getBindingResult().getFieldErrors()` | Plain `@ControllerAdvice`; extending `ResponseEntityExceptionHandler`; a hand-generated `ErrorResponse` DTO; `@ResponseStatus` on the exception class | A plain `@ControllerAdvice` method returning an object without `@ResponseBody` is resolved as a **view name**, so the 404 body would break; `@RestControllerAdvice` *is* `@ControllerAdvice` meta-annotated with `@ResponseBody`, so the proposal's requirement is met literally and correctly. `ProblemDetail` (RFC 7807, built into Spring 6) gives a structured body with **zero** extra generated classes — the minimality the proposal asked for. Extending `ResponseEntityExceptionHandler` would inherit ~15 handlers this slice never specified |
| DD44 | **DTO ↔ entity conversion lives in two `private` methods on the service**: `private <E>ResponseDto toResponseDto(<E> entity)` and `private void applyRequestDto(<E> entity, <E>RequestDto request)`. **No mapper class, no MapStruct, no Lombok.** The individual statement lines are precomputed in `context.py` as an ordered `tuple[str, ...]` (built with `.format()`, exactly as `FieldContext.annotations` already is) and the template only loops and indents | A generated `<E>Mapper` class; MapStruct; `BeanUtils.copyProperties`; assembling the statements inside the Jinja template | MapStruct would add an annotation processor to every generated `build.gradle` — verbatim the argument DD18 used to reject Lombok. A separate `<E>Mapper` would need the same related repositories injected for the request→entity direction, duplicating the service's dependency set for no isolation gain. `BeanUtils.copyProperties` cannot bridge `UUID categoryId` ↔ `Category category` at all. Precomputing statements in `context.py` preserves DD2's invariant that all branching lives there, keeping DD14's guard pointed at one surface. The FK read `entity.getCategory() == null ? null : entity.getCategory().getId()` is safe precisely because the DD-established fetch is still EAGER — no `LazyInitializationException` is reachable |
| DD45 | **Resource path segment = `naming.resource_path_segment(table.name)`**: pluralize the last `_`-separated word, then lowercase and replace `_` with `-`. Pluralizer is a fixed 3-rule `re.sub` chain — (1) `s\|x\|z\|ch\|sh$` → `+es`, (2) consonant + `y$` → `ies`, (3) otherwise `+s`. Result is validated against `^[a-z0-9]+(-[a-z0-9]+)*$`; a failure raises the new `InvalidResourcePathError(UngeneratableTableError)`, checked as a **fifth** step after DD35's four | An inflection library dependency; naive `+ "s"`; snake_case or camelCase URLs; the singular `table.name` verbatim; `pascal_case(table.name)` | `product` → `products`, `category` → `categories`, `status` → `statuses`, `order_line` → `order-lines` — all deterministic and dependency-free, where naive `+s` gives the wrong `categorys` and a library would make output version-dependent, breaking DD12 determinism across environments. Kebab-case plural is the dominant REST convention and `-` is illegal in a Java identifier, so this segment **cannot** reuse DD16's whitelist — it needs its own, and that whitelist is the boundary that keeps user-supplied UML text from breaking out of a `@RequestMapping("…")` string literal. Derived from `table.name` (not the Java class name) for the same reason DD10 keeps the DB name explicit: the URL should reflect the model the user drew. **Accepted tech debt**: irregular plurals (`person` → `persons`) are legal and unambiguous, just not idiomatic English |
| DD46 | **Endpoint table** (class-level `@RequestMapping("/api/<segment>")`): `POST ""` → 201 Created; `GET "/{id}"` → 200; `PUT "/{id}"` → 200; `DELETE "/{id}"` → 204 No Content (`void`); `GET ""` → 200 `Page<<E>ResponseDto>`; `GET "/count"` → 200 `long`. `@Valid @RequestBody` on POST/PUT, `@PathVariable UUID id` on the `/{id}` routes, explicit `@ResponseStatus` only where the status is not 200 | `PATCH` instead of `PUT`; `/count` as `?count=true`; returning `ResponseEntity<…>` everywhere; a configurable base path | `PUT` is correct because `<E>RequestDto` carries **every** non-PK field and `@Valid` enforces every forwarded `@NotNull` — `PATCH` semantics would require an all-nullable DTO, directly contradicting DD38's constraint forwarding. `GET /api/<seg>/count` and `GET /api/<seg>/{id}` are **not** ambiguous: Spring's pattern comparator ranks a literal segment above a `{variable}`, so `/count` always wins, deterministically and by documented behavior. Plain return types plus `@ResponseStatus` read better than `ResponseEntity` wrappers on six methods with fixed statuses. The literal `/api` prefix is a routing convention, not environment configuration — DD20's no-hardcoding constraint covers hosts, ports, URLs and credentials, none of which appear |
| DD47 | **The controller binds Spring's `Pageable` directly** as a method parameter (`public Page<<E>ResponseDto> list(Pageable pageable)`) and passes it through untouched. No custom `@RequestParam` parsing, no custom `Sort` assembly | `@RequestParam int page, int size, String sort`; a generated `PageRequestDto`; `Slice<T>` | Spring Boot auto-configures `PageableHandlerMethodArgumentResolver` whenever spring-data and spring-web are both on the classpath, binding `?page=0&size=20&sort=name,asc` with **zero** generated lines and giving §23's pagination *and* sorting in one parameter. Hand-parsing a `sort` string is precisely where ordering and injection bugs live, and it would re-implement documented framework behavior — the same argument DD17 used to keep `Repository.java.j2` empty. **Recorded tech debt**: serializing `Page<T>` directly is discouraged from Spring Data 3.3 (`PagedModel` is the successor); accepted here for minimality |
| DD48 | **DD18 is amended: `Entity.java.j2`'s no-arg constructor becomes `public`, not `protected`.** Everything else in DD18 (explicit getters/setters, no Lombok, no `equals`/`hashCode`) is unchanged | Keeping `protected` and having the service build entities some other way; a generated static factory; moving the service into `<pkg>.domain` | This is a **compilation prerequisite, not a preference**: `protected` grants access only to the same package or a subclass, and DD39 puts the service in `<base_package>.application` while the entity is in `<base_package>.domain`, so `new Product()` inside the generated service **would not compile**. A public no-arg constructor is explicitly JPA-legal ("public or protected no-arg constructor") and keeps Hibernate proxying intact. DD18's original rationale — discouraging direct instantiation — is exactly what this cycle must now permit. Moving the service into `domain/` to preserve `protected` would violate §22's layout. **Scope note**: this modifies a file the proposal's affected-areas table listed as untouched, and flips one existing assertion in `tests/test_entity_structure.py` |
| DD49 | **Six new templates**, all data-driven (DD2) and rendered by the single DD13 `_ENVIRONMENT`. Every loop body obeys the DD13 whitespace lesson: a content line **never** ends with a `{% %}` block tag; inline `{{ a if cond else b }}` is used instead, exactly as `Enum.java.j2` already does. Comma-separated lists (constructor parameters, argument lists) are precomputed in `context.py` via the existing `_comma_join` helper and emitted as a single `{{ … }}`, never assembled with a Jinja loop plus a conditional comma | A single mega-template with layer conditionals; building lists in-template | The previous cycle lost time to `trim_blocks`/`lstrip_blocks` interacting with block tags at end-of-line; pushing every conditional and every join into `context.py` removes the whole class of whitespace bug and keeps DD14's guard aimed at one surface. One template per emitted file type also keeps each template readable enough that a reviewer can diff generated Java against it |
| DD50 | **Determinism rules for the new artifacts.** (a) `GeneratedSources.files` order is fixed: Entity, Repository, RequestDto, ResponseDto, Service, Controller — layer order, not alphabetical. (b) DTO field order is `table.columns` order (DD12), with the PK simply omitted from the request. (c) Service constructor parameter order is: own repository first, then each distinct `fk.referenced_table` repository in `table.foreign_keys` first-appearance order (DD40). (d) Conversion-statement order follows the same field order. (e) Imports use `_group_imports` **unchanged** — every new Spring FQN lands in the existing `org.` group and every generated type in the `<base_package>.` group, each added only when used. **DD27 does not extend to sub-packages**: `<pkg>.application.dto.*` is a different package from `<pkg>.application`, so the service and controller **must** import the DTOs | Alphabetical file order; sorting DTO fields; a new import group for `org.springframework.*`; assuming DD27 suppresses the DTO imports | Layer order makes a regeneration diff readable top-to-bottom the way the code actually reads. Re-sorting fields would decouple the DTO from the model the user drew — DD12's argument verbatim. First-appearance FK ordering is the only rule that is stable under `Table` construction without introducing a sort the model never asked for. The DD27 sub-package clarification is the single most likely misreading of the prior cycle's rule and would produce non-compiling Java, so it is recorded as a rule rather than left implicit |

## Interfaces / Contracts

```python
# emit/naming.py                                                                  (DD45)
def resource_path_segment(table_name: str) -> str   # "order_line" -> "order-lines"
                                                    # "category" -> "categories"
                                                    # "status" -> "statuses"

# emit/errors.py                                                                  (DD45)
class InvalidResourcePathError(UngeneratableTableError)   # table_name, segment
def reject_invalid_resource_path(table: Table) -> None    # DD35 step 5

# emit/context.py                                                          (DD37-DD47)
@dataclass(frozen=True) class DtoFieldContext:
    name: str                       # "categoryId" for a FK column (DD38)
    java_type: str                  # "UUID" for a FK column, never the entity type
    getter: str
    setter: str
    annotations: tuple[str, ...]    # request only; () on every response field

@dataclass(frozen=True) class DtoContext:
    package: str                    # "{base_package}.application.dto"
    class_name: str                 # "<E>RequestDto" | "<E>ResponseDto"
    fields: tuple[DtoFieldContext, ...]
    import_groups: tuple[tuple[str, ...], ...]

@dataclass(frozen=True) class RepositoryDependencyContext:
    field_name: str                 # "categoryRepository"
    type_name: str                  # "CategoryRepository"
    entity_type: str                # "Category"

@dataclass(frozen=True) class ServiceContext:
    package: str                    # "{base_package}.application"
    class_name: str                 # "<E>Service"
    entity_class: str
    repository_field: str           # own repository, always first (DD50c)
    repository_type: str
    dependencies: tuple[RepositoryDependencyContext, ...]   # deduped (DD40)
    constructor_parameters: str     # precomputed via _comma_join (DD49)
    constructor_assignments: tuple[str, ...]
    to_response_statements: tuple[str, ...]                 # DD44
    apply_request_statements: tuple[str, ...]               # DD44
    resource_name: str              # table.name, for ResourceNotFoundException
    import_groups: tuple[tuple[str, ...], ...]

@dataclass(frozen=True) class ControllerContext:
    package: str                    # "{base_package}.api"
    class_name: str                 # "<E>Controller"
    service_field: str
    service_type: str
    request_dto: str
    response_dto: str
    resource_path: str              # "/api/order-lines"                  (DD45)
    import_groups: tuple[tuple[str, ...], ...]

def build_request_dto_context(table, *, base_package) -> DtoContext
def build_response_dto_context(table, *, base_package) -> DtoContext
def build_service_context(table, *, base_package) -> ServiceContext
def build_controller_context(table, *, base_package) -> ControllerContext

# emit/renderer.py                                                               (DD42)
def generate_shared_error_sources(*, base_package: str = "com.modelia.generated") -> GeneratedSources
```

### Emitted file paths (extends DD20's layout)

| Layer | Path pattern | Entry point |
|---|---|---|
| domain | `src/main/java/<pkg>/domain/<E>.java` | `generate_table_sources` |
| persistence | `src/main/java/<pkg>/persistence/<E>Repository.java` | `generate_table_sources` |
| **application/dto** | `src/main/java/<pkg>/application/dto/<E>RequestDto.java` | `generate_table_sources` |
| **application/dto** | `src/main/java/<pkg>/application/dto/<E>ResponseDto.java` | `generate_table_sources` |
| **application** | `src/main/java/<pkg>/application/<E>Service.java` | `generate_table_sources` |
| **api** | `src/main/java/<pkg>/api/<E>Controller.java` | `generate_table_sources` |
| **errors** | `src/main/java/<pkg>/errors/ResourceNotFoundException.java` | `generate_shared_error_sources` |
| **errors** | `src/main/java/<pkg>/errors/GlobalExceptionHandler.java` | `generate_shared_error_sources` |
| validation, config | **never produced** | — |

### Column → DTO field (extends DD5–DD10 and the DD23–DD29 table)

| Column shape | Request DTO | Response DTO |
|---|---|---|
| PK (`id`) | **omitted** (DD38) | `UUID id;` no annotation |
| FK column `<n>` | `UUID <camel_case(n)>;` + `@NotNull` when not nullable | `UUID <camel_case(n)>;` |
| enum column | `<pascal(enum_type_name)> <camel(n)>;` + `@NotNull` when not nullable | same, no annotation |
| scalar | DD5–DD7 type + `@NotNull` / `@Size(max=)` per DD9 | DD5–DD7 type, no annotation |

### Service ↔ not-found contract (proposal scope item 4)

| Method | Presence check | On absence |
|---|---|---|
| `findById` / `update` | `repository.findById(id).orElseThrow(...)` | `ResourceNotFoundException(resourceName, id)` |
| `delete` | `if (!repository.existsById(id)) throw …` **then** `deleteById` | same |
| FK resolution | `<rel>Repository.findById(dto.getXId()).orElseThrow(...)` (DD40) | same, with the related resource name |

`deleteById` is explicitly guarded because Spring Data JPA 3.x makes it a silent no-op for a
missing id (older versions threw `EmptyResultDataAccessException`) — relying on either would make
the 404 version-dependent, which is what the proposal's "MUST check explicitly" is about.

## Testing Strategy

Strict TDD (RED → GREEN → REFACTOR), `pytest` + `hypothesis`, no DB fixtures. One module per new
mapping concern, mirroring the existing `spring_generator/tests/` convention (module docstring
naming the DDs covered, `a_table()` factories, structural `.java` text assertions only — no
`javac`, no Java parser, per the archived proposal D2).

| Layer | Module | What to test |
|---|---|---|
| Unit | `test_resource_path.py` (new) | Parametrized DD45 table: `product`→`products`, `category`→`categories`, `status`→`statuses`, `box`→`boxes`, `order_line`→`order-lines`, `day`→`days` (vowel + `y`); segment never contains `_` or an uppercase char; illegal segment → `InvalidResourcePathError`, subclassing `UngeneratableTableError`; check runs **after** DD35's four (one adjacent-pair order test) |
| Unit | `test_dto_generation.py` (new) | Both DTOs exist at the DD37 paths with `package <pkg>.application.dto;`; request omits `id`, response includes it; FK column → `private UUID categoryId;` and the related entity type name appears **nowhere** in either DTO; two FKs to one table → `billingAddressId` + `shippingAddressId`; enum column keeps its enum type; `@NotNull`/`@Size` present on request, **absent** on response; no `jakarta.persistence` import and no `@Column`/`@JoinColumn`/`@Enumerated` substring in either file; field order == `table.columns` order (DD38, DD50b) |
| Unit | `test_service_generation.py` (new) | `@Service` present, `@Component` absent; `private final` fields + one constructor, no `@Autowired`; all six DD39 signatures incl. `Page<ProductResponseDto> list(Pageable`; `@Transactional(readOnly = true)` at class level and `@Transactional` on the three mutators; `orElseThrow` + `ResourceNotFoundException` on `findById`/`update`; `existsById` guard before `deleteById`; `getReference` never appears (DD40); FK resolution calls `categoryRepository.findById`; **two FKs to the same table inject one repository**; **self-referencing FK injects no second repository**; nullable FK emits a null guard; `toResponseDto`/`applyRequestDto` are `private`; no `MapStruct`/`Mapper`/`BeanUtils` substring (DD44); DTO imports present despite the sub-package (DD50e) |
| Unit | `test_controller_generation.py` (new) | `@RestController` + `@RequestMapping("/api/products")`; all six DD46 mappings with exact paths; `@Valid @RequestBody` on POST and PUT only; `@ResponseStatus(HttpStatus.CREATED)` on POST and `NO_CONTENT` on DELETE; `Pageable pageable` bound directly and no `@RequestParam` for page/size/sort (DD47); `@PathVariable UUID id`; controller references only DTOs, never the entity type; kebab-plural path for `order_line` |
| Unit | `test_error_sources.py` (new) | `generate_shared_error_sources()` returns exactly 2 files at the DD37 `errors/` paths; `generate_table_sources` emits **nothing** under `errors/` (DD42); `ResourceNotFoundException extends RuntimeException` with `(String, UUID)`; `@RestControllerAdvice` present and bare `@ControllerAdvice` absent; both `@ExceptionHandler` types present, mapped to `NOT_FOUND` and `BAD_REQUEST`; `ProblemDetail` used and no extra error DTO class emitted; `generate_shared_error_sources(...) == generate_shared_error_sources(...)`; custom `base_package` honored |
| Unit | `test_entity_structure.py` (**modify**) | Flip the ctor assertion: `public <E>() {` present, `protected <E>() {` absent (DD48). Every other DD18 assertion unchanged |
| Unit | `test_paths_and_package.py` (**modify**) | `generate_table_sources` now yields exactly **6** files; each `package` line matches its path; still no host/port/URL substring anywhere; **no file under `validation/` or `config/`**; custom `base_package` honored across all six |
| Property | `test_determinism.py` (**extend**) | Widen to all six files: `generate(t) == generate(t)` byte-identical; file order is the fixed DD50a layer order; DTO field order == `table.columns` order; braces and parentheses balanced in every new file; imports deduped, grouped and sorted with the new `org.springframework.*` FQNs |
| Guard | `test_no_concat_guard.py` (unchanged) | Must stay green over the modified `emit/` modules — `resource_path_segment` uses `re.sub` only, and every statement tuple is built with `.format()`/`_comma_join` (DD14, DD44, DD49) |
| Unit | `test_purity.py` (**extend**) | The new entry point also completes with no DB fixture and never calls `validate()` |
| Integration / E2E | — | N/A — no endpoint, no WS, no DB, no filesystem in the **generator** (DD3). The generated Java is not compiled or run (roadmap item 13) |

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/spring_generator/emit/naming.py` | Modify | `resource_path_segment` + the 3-rule pluralizer and segment whitelist (DD45) |
| `backend/apps/spring_generator/emit/errors.py` | Modify | `InvalidResourcePathError`, `reject_invalid_resource_path` as DD35 step 5 (DD45) |
| `backend/apps/spring_generator/emit/context.py` | Modify | `DtoFieldContext`/`DtoContext`/`RepositoryDependencyContext`/`ServiceContext`/`ControllerContext` + their four builders (DD37–DD47, DD49, DD50) |
| `backend/apps/spring_generator/emit/renderer.py` | Modify | 4 new renders inside `generate_table_sources`; new `generate_shared_error_sources` (DD42, DD50a) |
| `backend/apps/spring_generator/emit/templates/RequestDto.java.j2` | Create | DD38, DD49 |
| `backend/apps/spring_generator/emit/templates/ResponseDto.java.j2` | Create | DD38, DD49 |
| `backend/apps/spring_generator/emit/templates/Service.java.j2` | Create | DD39, DD40, DD44, DD49 |
| `backend/apps/spring_generator/emit/templates/Controller.java.j2` | Create | DD46, DD47, DD49 |
| `backend/apps/spring_generator/emit/templates/ResourceNotFoundException.java.j2` | Create | DD41 |
| `backend/apps/spring_generator/emit/templates/GlobalExceptionHandler.java.j2` | Create | DD43 |
| `backend/apps/spring_generator/emit/templates/Entity.java.j2` | **Modify** | `protected` → `public` no-arg constructor (DD48) — **not** listed in the proposal's affected areas |
| `backend/apps/spring_generator/emit/templates/Repository.java.j2` | **Unchanged** | Explicit proposal constraint; `JpaRepository<T, UUID>` already supplies everything DD39 calls |
| `backend/apps/spring_generator/emit/javatypes.py` | **Unchanged** | DTO types reuse the existing table verbatim (DD38) |
| `backend/apps/spring_generator/tests/{test_resource_path,test_dto_generation,test_service_generation,test_controller_generation,test_error_sources}.py` | Create | One module per new concern |
| `backend/apps/spring_generator/tests/{test_entity_structure,test_paths_and_package,test_determinism,test_purity}.py` | Modify | DD48 ctor flip; 6-file expectations; widened determinism; new entry point |
| `openspec/specs/spring-boot-generation/spec.md` | Modify (via `sdd-spec`) | **Package and File Path Layout** delta — see DD37 |
| `docs/ai/{CURRENT_STATE,NEXT_STEPS,DECISIONS_LOG}.md` | Modify | `rules.design` dual-documentation convention: record DD37–DD50 |

## Threat Matrix

N/A for the generator boundary — it introduces no routing, shell command, subprocess, VCS/PR
automation, executable-file classification, or process integration. Both entry points remain pure
in-process transformations that open no file, spawn no process, and write nothing to disk (DD3);
the *generated* Java declares routes, but nothing in this repository ever serves them.

The one new value reaching emitted source outside DD16's identifier whitelist is DD45's resource
path segment, which lands inside a `@RequestMapping("…")` string literal. It is closed
structurally by DD45's own `^[a-z0-9]+(-[a-z0-9]+)*$` whitelist plus `InvalidResourcePathError` —
not by escaping — the same pattern the previous cycle used for DD32's preserved enum label, and
it is covered by `test_resource_path.py` and the brace-balance property test.

## Sequence-Diagram Rule

`openspec/config.yaml` `rules.design` requires sequence diagrams for realtime/collaboration flows
(Django Channels). No realtime flow exists in this scope; the pipeline and layer-dependency
diagrams in **Technical Approach** are included instead as the only non-obvious control flow.

## Migration / Rollout

No migration required. No models, no tables, no persisted data, no on-disk artifacts. The single
backwards-incompatible change is DD48's `protected` → `public` entity constructor, whose only
consumer is `tests/test_entity_structure.py` inside this app (DD1: nothing imports this app).
Rollback = revert this change's commits and restore the original **Package and File Path Layout**
requirement; `domain/` and `persistence/` output returns byte-identical apart from that one line.

## Open Questions

- [ ] **DD48 is a scope delta the proposal did not anticipate.** `Entity.java.j2` was listed as
      untouched, but the generated project cannot compile without a public no-arg constructor.
      Confirm at verify that flipping the DD18 assertion is accepted rather than routed to a
      separate change.
- [ ] **DD45 irregular plurals.** `person` → `persons`, `child` → `childs`. Legal, unambiguous
      URLs but not idiomatic English. Deliberately accepted to stay dependency-free and
      deterministic; revisit only if a real model exercises it.
- [ ] **DD47 `Page<T>` serialization** is discouraged from Spring Data 3.3 in favour of
      `PagedModel`. Accepted tech debt; revisit when roadmap item 13 first compiles generated code
      against a pinned Spring Boot version.
- [ ] **DD42 singleton composition.** `generate_shared_error_sources` must be called exactly once
      per generated project by the future item-13 writer. A caller that forgets it emits a project
      whose services reference a `ResourceNotFoundException` that was never written — detection
      belongs to that orchestrating caller, not to a one-`Table` function.
- [ ] **Cross-artifact name collisions** (a `count` column vs. the `/count` route, an entity named
      `Page`) remain undetectable from a single `Table`. Same class as the previously recorded
      `Order`-table-vs-`Order`-enum collision.
- [ ] Filtering, search, relation-navigation sub-resources, `validation/`, `config/` and §33
      metadata consumption stay out of scope per the proposal.

> Size note: this artifact exceeds the skill's 800-word soft budget, matching the explicit tradeoff
> recorded by both archived cycles' designs. `sdd-tasks` needs the full DTO field table, the
> endpoint table and the not-found contract to slice implementable units without re-deriving them.
