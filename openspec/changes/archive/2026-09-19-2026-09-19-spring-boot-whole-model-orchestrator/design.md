# Design: Spring Boot generator — whole-model source orchestrator

This change adds one pure public orchestrator that turns a complete `RelationalModel` into one ordered in-memory `GeneratedSources` aggregate. It delegates to existing lower-level Spring Boot generators, rejects exact duplicate output paths atomically, and does not materialize, compile, validate, or execute anything.

## Technical Approach

Strictly additive. Keep all current lower-level generator contracts unchanged and add one thin aggregation layer in `backend/apps/spring_generator/emit/renderer.py`.

```text
generate_model_sources(model, *, base_package)
   ├─ validate base_package through delegated table/enum/shared-error generators
   ├─ append table files in model.tables order
   │    └─ generate_table_sources(table, base_package=base_package).files
   ├─ append enum files in model.enum_types order
   │    └─ generate_enum_source(enum_type, base_package=base_package)
   ├─ append shared errors exactly once
   │    └─ generate_shared_error_sources(base_package=base_package).files
   ├─ append project config exactly once
   │    └─ generate_project_config_sources().files
   ├─ preflight exact duplicate GeneratedFile.path values from the full ordered list
   │    └─ raise GeneratedSourcePathCollisionError before constructing GeneratedSources
   └─ return GeneratedSources(files=tuple(ordered_files))
```

The orchestrator must not sort. Ordering is the product contract: tables, enums, shared errors, project config.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD51 | `generate_model_sources(model: RelationalModel, *, base_package: str = "com.modelia.generated") -> GeneratedSources` lives in `apps.spring_generator.emit.renderer`. | A new module such as `model_renderer.py`; an API named `generate_project_sources`; changing `GeneratedSources`. | `renderer.py` already owns the public Spring generator entry points and shared Jinja environment. Reusing `GeneratedSources` keeps the output contract frozen and in-memory. |
| DD52 | The orchestrator imports `RelationalModel` from `apps.relational_mapping.domain.schema` and `GeneratedFile`/`GeneratedSources` from `apps.spring_generator.domain.sources`. | Accepting looser duck types; importing mapper or validation APIs. | The frozen domain dataclass is the explicit input contract. The mapper and validation layers remain outside generation purity boundaries. |
| DD53 | Aggregation order is exactly table artifacts, enum artifacts, shared errors, project config. | Alphabetical path sorting; grouping by Java package; globals first. | `RelationalModel.tables` and `RelationalModel.enum_types` already encode deterministic user/model order. Sorting would hide that contract and could change generated review diffs. |
| DD54 | Table boundaries are preserved by appending each `generate_table_sources(table).files` tuple as a complete contiguous block. | Interleaving all entities, then all repositories, then DTOs; flattening by layer. | Inheritance tables already have a special internal boundary: root entity, subclass entities, root repository. Whole-model aggregation must not reinterpret lower-level ordering. |
| DD55 | Singleton artifacts are generated once after all model-owned artifacts. Empty models still produce singleton artifacts only. | Running singleton generators per table; emitting nothing for empty models. | The orchestrator represents a project-level generation request, so shared errors and `application.yml` belong to the aggregate even when no tables or enums exist. |
| DD56 | Exact duplicate `GeneratedFile.path` values are rejected by a typed `GeneratedSourcePathCollisionError` under `UngeneratableSourceError`. | Silent overwrite through `as_mapping()`; deduplication; keeping first or last; untyped `ValueError`. | Path is the existing generated source identity. Duplicate paths indicate an invalid aggregate and must be catchable by existing generator-error handling. |
| DD57 | Duplicate detection is atomic and happens before constructing or returning `GeneratedSources`. | Returning a partial aggregate; constructing `GeneratedSources` then checking `as_mapping()`. | `GeneratedSources.as_mapping()` would collapse duplicates by dictionary behavior. Checking the ordered list first preserves evidence and prevents partial success semantics. |
| DD58 | Collision payload is minimal and deterministic: `path: str` and `occurrences: int`. The message includes both values. | Including generated contents, full file objects, table names, or enum names. | The product contract only requires exact path duplicate rejection. Provenance can be added later without changing the basic typed error class. |
| DD59 | `base_package` propagation is delegated only to generators that already accept it: table, enum, and shared-error generation. Project config remains package-independent. | Adding a package parameter to `generate_project_config_sources`; manually rewriting paths or contents. | This preserves current package validation and avoids making YAML depend on Java packaging. |
| DD60 | The orchestrator adds no new Java templates, path conventions, validation rules, runtime scaffolding, or compilation/materialization behavior. | Adding OpenAPI, Postman, Manifest, filtering, frontend/mobile, Java `config/`, Docker, Gradle, or smoke tests. | This slice closes only the whole-model source aggregation gap and intentionally leaves runtime/project materialization for future changes. |

## Interfaces / Contracts

### Public API

```python
# backend/apps/spring_generator/emit/renderer.py
from apps.relational_mapping.domain.schema import RelationalModel
from apps.spring_generator.domain.sources import GeneratedSources


def generate_model_sources(
    model: RelationalModel,
    *,
    base_package: str = "com.modelia.generated",
) -> GeneratedSources:
    ...
```

Contract:

- Pure function of `model` and `base_package`.
- Returns `GeneratedSources(files=tuple[GeneratedFile, ...])`.
- Preserves lower-level generator paths, contents, and file order inside each delegated result.
- Raises existing lower-level typed errors unchanged when a delegated generator rejects its input.
- Raises the new duplicate-path typed error if two or more generated files share the same exact `path`.

### Typed duplicate-path error

```python
# backend/apps/spring_generator/emit/errors.py
class GeneratedSourcePathCollisionError(UngeneratableSourceError):
    def __init__(self, path: str, occurrences: int):
        self.path = path
        self.occurrences = occurrences
        super().__init__(
            "Generated source path {!r} appears {} times".format(path, occurrences)
        )
```

Payload requirements:

- `path`: exact duplicate `GeneratedFile.path` value.
- `occurrences`: total number of files in the candidate aggregate with that path.
- Parent class: `UngeneratableSourceError` directly, not `UngeneratableTableError` or `UngeneratableEnumError`, because a collision can cross tables, enums, and singletons.
- If multiple paths collide, the raised error uses the first colliding path discovered by scanning the ordered candidate file list from left to right.

### Private helpers

Recommended private symbols in `renderer.py`:

```python
def _extend_generated_files(files: list[GeneratedFile], sources: GeneratedSources) -> None:
    ...


def _reject_duplicate_generated_paths(files: tuple[GeneratedFile, ...]) -> None:
    ...
```

These helpers are optional but useful. They should remain private because the product API is `generate_model_sources`.

## Aggregation Algorithm

Pseudo-code:

```python
def generate_model_sources(model: RelationalModel, *, base_package: str = "com.modelia.generated") -> GeneratedSources:
    files: list[GeneratedFile] = []

    for table in model.tables:
        files.extend(generate_table_sources(table, base_package=base_package).files)

    for enum_type in model.enum_types:
        files.append(generate_enum_source(enum_type, base_package=base_package))

    files.extend(generate_shared_error_sources(base_package=base_package).files)
    files.extend(generate_project_config_sources().files)

    candidate = tuple(files)
    _reject_duplicate_generated_paths(candidate)
    return GeneratedSources(files=candidate)
```

Duplicate preflight pseudo-code:

```python
def _reject_duplicate_generated_paths(files: tuple[GeneratedFile, ...]) -> None:
    counts: dict[str, int] = {}
    first_collision: str | None = None

    for generated_file in files:
        path = generated_file.path
        counts[path] = counts.get(path, 0) + 1
        if counts[path] == 2 and first_collision is None:
            first_collision = path

    if first_collision is not None:
        raise GeneratedSourcePathCollisionError(
            path=first_collision,
            occurrences=counts[first_collision],
        )
```

Atomicity requirements:

- Build only a local candidate list/tuple before preflight.
- Do not call `GeneratedSources.as_mapping()` for collision detection.
- Do not return or expose `GeneratedSources` until after preflight passes.
- Do not mutate `model`, tables, enums, or generated file instances.

## Order Handling

For a model with tables `(Product, Order)` and enum types `(order_status,)`, expected path regions are:

1. `generate_table_sources(Product, base_package=...)` files in their existing order.
2. `generate_table_sources(Order, base_package=...)` files in their existing order.
3. `generate_enum_source(order_status, base_package=...)`.
4. `generate_shared_error_sources(base_package=...)` files in their existing order:
   - `src/main/java/<pkg>/errors/ResourceNotFoundException.java`
   - `src/main/java/<pkg>/errors/GlobalExceptionHandler.java`
5. `generate_project_config_sources()` files in their existing order:
   - `src/main/resources/application.yml`

For `RelationalModel()` the aggregate contains only item 4 then item 5.

## Purity Guarantees

`generate_model_sources` must not:

- write, create, read, or materialize generated files on disk;
- inspect environment variables;
- open database connections;
- access the network;
- run subprocesses;
- invoke Java, Gradle, Docker, or CI tools;
- call UML or relational validation routines;
- call mapper functions;
- sort, mutate, overwrite, deduplicate, or normalize generated files after lower-level generation.

The only allowed work is in-memory delegation, list/tuple aggregation, exact string-path counting, and construction of frozen dataclass outputs.

## Compatibility Boundaries

Must remain unchanged:

- `backend/apps/relational_mapping/domain/schema.py` and the `RelationalModel` contract.
- `backend/apps/spring_generator/domain/sources.py`, including `GeneratedSources.as_mapping()` behavior.
- All Java/YAML templates.
- `generate_table_sources`, including supported inheritance table behavior and internal file order.
- `generate_enum_source`, including enum rejection rules and path/content output.
- `generate_shared_error_sources`, including two-file output and base package behavior.
- `generate_project_config_sources`, including package independence and the `src/main/resources/application.yml` path.
- Existing typed lower-level errors and their payloads.

Explicitly outside this boundary:

- Generated-project materialization or filesystem writing.
- Java compilation, Gradle execution, Docker, CI, or runtime smoke tests.
- OpenAPI, Postman, Domain Manifest, filtering/search metadata, generated filtering APIs, frontend output, mobile output, and new Java `config/` classes.
- Inheritance API expansion beyond whatever `generate_table_sources` already emits.

## Test / TDD Plan

Create tests first, then implement the smallest code to pass them.

### New test file: `backend/apps/spring_generator/tests/test_model_sources.py`

1. Public API exists:
   - import `renderer.generate_model_sources`.
2. Normal aggregate order:
   - build `RelationalModel(tables=(product, order), enum_types=(order_status,))`.
   - compare `paths = tuple(file.path for file in sources.files)` against direct lower-level generator outputs concatenated in the required order.
3. Empty model emits globals:
   - `RelationalModel()` returns two shared-error paths followed by `src/main/resources/application.yml`.
4. Singleton inclusion exactly once:
   - multiple tables/enums still produce exactly one `ResourceNotFoundException.java`, one `GlobalExceptionHandler.java`, and one `application.yml`.
5. Custom package propagation:
   - table, enum, and shared-error Java paths/content use `org.example.myproject`.
   - `application.yml` path/content remains independent of that package.
6. Lower-level output byte identity:
   - corresponding files inside the aggregate equal direct outputs from `generate_table_sources`, `generate_enum_source`, `generate_shared_error_sources`, and `generate_project_config_sources`.
7. Inheritance table boundary:
   - first table is a supported discriminator-backed `Vehicle` table.
   - assert the aggregate begins with exactly `generate_table_sources(vehicle).files`, then the next table block.

Optional factory addition:

```python
# backend/apps/spring_generator/tests/factories.py
from apps.relational_mapping.domain.schema import RelationalModel

def a_relational_model(*, tables=(), enum_types=()) -> RelationalModel:
    return RelationalModel(tables=tables, enum_types=enum_types)
```

### New test file: `backend/apps/spring_generator/tests/test_model_source_collisions.py`

1. Table/enum path collision:
   - table `status` and enum type `status` both target `src/main/java/<pkg>/domain/Status.java`.
   - assert `GeneratedSourcePathCollisionError` is raised.
   - assert `isinstance(exc.value, UngeneratableSourceError)`.
   - assert `exc.value.path == "src/main/java/com/modelia/generated/domain/Status.java"`.
   - assert `exc.value.occurrences == 2`.
2. Duplicate enum path collision:
   - enum types whose names normalize to the same PascalCase Java name.
   - assert the same typed error and payload.
3. Atomic no-partial behavior:
   - use `with pytest.raises(...)` and no variable assignment from the call.
   - where practical, monkeypatch `GeneratedSources.__init__` is not needed; the contract is satisfied by no returned value and by implementation review that preflight precedes return construction.
4. First-collision determinism:
   - create two collision pairs and assert the earliest colliding path in aggregate scan order is reported.

### Extend `backend/apps/spring_generator/tests/test_determinism.py`

- Add repeated-call assertion for `generate_model_sources` using a model with at least two tables and one enum.
- Assert returned `GeneratedSources` values are equal and every corresponding path/content pair is identical.

### Extend `backend/apps/spring_generator/tests/test_purity.py`

- Add no-DB-fixture test for `generate_model_sources`.
- Patch `apps.uml_modeling.validation.engine.validate` and assert it is not called.
- If existing purity style patches mapper functions or subprocess/filesystem APIs later, include `generate_model_sources` in the same guard.

### Regression tests not required

Do not add Java compilation, Gradle, Docker, OpenAPI, Postman, frontend, mobile, or generated-project materialization tests in this change.

## Rollout

Implementation can be one small work unit:

1. Add failing tests for aggregate order, globals, empty model, package propagation, determinism, purity, and collisions.
2. Add `GeneratedSourcePathCollisionError` in `emit/errors.py`.
3. Add `generate_model_sources` and private duplicate-path helper(s) in `emit/renderer.py`.
4. Run focused backend tests for `apps.spring_generator`.
5. Avoid changes outside `backend/apps/spring_generator/emit/` and `backend/apps/spring_generator/tests/`.

## Review Checklist

- [ ] The public API name is exactly `generate_model_sources`.
- [ ] Output order is tables, enums, shared errors, project config.
- [ ] Empty model emits shared errors then `application.yml`.
- [ ] Duplicate path collisions raise `GeneratedSourcePathCollisionError` before any aggregate is returned.
- [ ] The error has `path` and `occurrences` payload attributes.
- [ ] No lower-level generator output changes.
- [ ] No filesystem, DB, network, subprocess, Java, Gradle, Docker, validation, or mapper behavior is introduced.
