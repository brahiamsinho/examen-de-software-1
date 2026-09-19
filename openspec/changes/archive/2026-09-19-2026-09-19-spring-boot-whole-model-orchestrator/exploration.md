# Exploration: Spring Boot generator whole-model orchestrator

Change: `2026-09-19-spring-boot-whole-model-orchestrator`

## Current state read

- `openspec/specs/relational-mapping/spec.md` defines the frozen, DB-free `RelationalModel(tables, enum_types)` contract and deterministic table/enum ordering.
- `openspec/specs/spring-boot-generation/spec.md` explicitly says whole-model orchestration is not implemented yet and keeps Java compilation, OpenAPI, Postman, Domain Manifest, frontend/mobile, and Java `config/` classes out of scope.
- `backend/apps/relational_mapping/domain/schema.py` exposes the needed inputs: `RelationalModel.tables`, `RelationalModel.enum_types`, `Table`, and `EnumType`.
- `backend/apps/spring_generator/domain/sources.py` already has the right aggregate output type: frozen `GeneratedSources(files=tuple[GeneratedFile, ...])`.
- `backend/apps/spring_generator/emit/renderer.py` already provides the lower-level APIs that the orchestrator should call:
  - `generate_table_sources(table, *, base_package="com.modelia.generated") -> GeneratedSources`
  - `generate_enum_source(enum_type, *, base_package="com.modelia.generated") -> GeneratedFile`
  - `generate_shared_error_sources(*, base_package="com.modelia.generated") -> GeneratedSources`
  - `generate_project_config_sources() -> GeneratedSources`
- Existing tests cover per-table paths, enum generation, shared errors, project config, determinism, purity, and forbidden output directories, but no test walks a `RelationalModel` end to end.

## Recommended bounded initial slice

Add one pure in-memory public orchestrator that accepts a complete `RelationalModel`, delegates to the existing generators, aggregates all `GeneratedFile` values into one deterministic `GeneratedSources`, and rejects duplicate generated paths before returning.

Recommended contract:

```python
def generate_model_sources(
    model: RelationalModel,
    *,
    base_package: str = "com.modelia.generated",
) -> GeneratedSources:
    ...
```

Recommended deterministic aggregate order:

1. For each `table` in `model.tables` order, append every file from `generate_table_sources(table, base_package=base_package)` in that table generator's existing file order.
2. For each `enum_type` in `model.enum_types` order, append `generate_enum_source(enum_type, base_package=base_package)`.
3. Append both files from `generate_shared_error_sources(base_package=base_package)` exactly once.
4. Append the single file from `generate_project_config_sources()` exactly once.
5. Before constructing/returning `GeneratedSources`, detect any duplicate `GeneratedFile.path` across the whole aggregate and raise a typed generator error rather than silently keeping the first/last file.

This order keeps model-declared tables first, then model-declared enums, then project singletons. It is not alphabetical and does not sort because the relational mapper already owns deterministic ordering.

## Why this slice is small enough

- It does not invent new Java templates.
- It does not change per-table, enum, shared-error, inheritance, or YAML rendering behavior.
- It reuses `GeneratedSources`; no new output model is needed.
- It enables the known missing project-level caller without touching generated-project materialization or compilation.
- Collision detection can operate only on generated POSIX paths, which already encode Java package + simple class name for Java sources and exact resource path for YAML.

## Collision rule

The first slice should detect exact generated path collisions across all artifacts before returning. This covers the main Java name/path failures:

- Table `order` and enum `order` both generate `src/main/java/<pkg>/domain/Order.java`.
- Two enum types whose names normalize to the same Java enum name generate the same `domain/<Enum>.java` path.
- Two tables whose names normalize to the same entity/repository/DTO/service/controller paths collide.
- Repeated singleton invocation bugs would collide on `errors/...` or `src/main/resources/application.yml`.

Recommended typed error shape in `backend/apps/spring_generator/emit/errors.py`:

```python
class GeneratedSourcePathCollisionError(UngeneratableSourceError):
    path: str
    occurrences: int
```

The implementation phase can carry richer provenance if useful, but the product behavior only needs: duplicate generated path => no aggregate returned.

## Product decisions genuinely needed

1. Confirm the public API name `generate_model_sources`; alternatives are `generate_relational_model_sources` or `generate_project_sources`.
2. Confirm aggregate order. Recommended: tables, enums, shared errors, project config.
3. Confirm duplicate generated path handling. Recommended: typed error, fail-fast/no returned partial aggregate, no overwrite policy.
4. Confirm whether an empty `RelationalModel()` should still emit project-level shared errors and `application.yml`. Recommended: yes, because the orchestrator is project-level; tables/enums are optional but project singletons are generated once.
5. Confirm whether collision detection by exact generated path is sufficient for this slice. Recommended: yes; broader semantic Java analysis waits for compilation/materialization work.

No additional product decision is needed for Docker, Gradle, OpenAPI, Postman, manifest, frontend, mobile, filtering, or inheritance API behavior because all are excluded from this slice.

## Exact source paths for a future implementation phase

Modify:

- `backend/apps/spring_generator/emit/renderer.py` — add `generate_model_sources()` and small private aggregation/collision helpers if needed.
- `backend/apps/spring_generator/emit/errors.py` — add a typed collision error under `UngeneratableSourceError`.
- `backend/apps/spring_generator/tests/factories.py` — optionally add a `RelationalModel` factory to keep tests readable.
- `backend/apps/spring_generator/tests/test_determinism.py` — extend repeated-call checks to the whole-model aggregate.
- `backend/apps/spring_generator/tests/test_purity.py` — extend purity checks to the orchestrator if consistent with existing spy style.

Create:

- `backend/apps/spring_generator/tests/test_model_sources.py` — public API, aggregate order, exact singleton inclusion, empty model behavior, custom `base_package` propagation.
- `backend/apps/spring_generator/tests/test_model_source_collisions.py` — table/enum path collision, duplicate enum path collision, duplicate singleton guard if practical.

Do not modify for this slice:

- `backend/apps/relational_mapping/domain/schema.py`
- `backend/apps/spring_generator/domain/sources.py`
- `backend/apps/spring_generator/emit/context.py`
- `backend/apps/spring_generator/emit/inheritance_context.py`
- Any Jinja Java/YAML templates
- Django settings, Docker, Gradle, frontend, mobile, OpenAPI/Postman/Manifest files

## Focused test scenarios

- `generate_model_sources(RelationalModel(tables=(product,), enum_types=(status,)))` returns table files, then enum file, then two shared error files, then `application.yml`.
- Shared errors appear exactly once even when multiple tables exist.
- Project config appears exactly once even when multiple tables/enums exist.
- Custom `base_package` is passed to table, enum, and shared-error generation; `application.yml` remains package-independent.
- Repeated calls with the same model return equal `GeneratedSources` with byte-identical content and identical path order.
- A table and enum that both normalize to the same domain Java path raise `GeneratedSourcePathCollisionError` before returning an aggregate.
- `RelationalModel()` behavior follows the product decision above; recommended assertion is exactly three singleton files: two errors plus `application.yml`.
- No generated path is under forbidden `validation/` or Java `config/`, and no output includes OpenAPI, Postman, Manifest, Docker, frontend, or mobile artifacts.

## Exclusions

Explicitly out of scope:

- Java compilation, `javac`, Gradle execution, generated-project materialization, or filesystem writing.
- Docker services, Dockerfile/Compose changes, CI, or runtime smoke tests.
- OpenAPI, Postman collection, Domain Manifest, springdoc wiring, or generated metadata manifests.
- Filtering/search or generation metadata such as `searchable`, `sortable`, `crud`, or `readOnly`.
- Inheritance API expansion: no discriminator DTOs, services, controllers, subclass repositories, polymorphic REST API, or Java inheritance behavior beyond whatever `generate_table_sources` already emits.
- New frontend or mobile generation.
- New Java `config/` classes, profiles, logging config, security config, or runtime scaffolding.

## Risks and mitigations

- Risk: aggregate ordering becomes another implicit contract. Mitigation: specify and test one exact order.
- Risk: duplicate paths are silently overwritten if `as_mapping()` is used too early. Mitigation: detect collisions from the ordered `GeneratedFile` list before constructing/returning aggregate output.
- Risk: singleton generators accidentally run per table. Mitigation: tests with two tables should assert exactly two `/errors/` files and one `application.yml` path total.
- Risk: enum/table Java type collisions are missed. Mitigation: path-based collision tests using same normalized domain name.
- Risk: scope creep into generated-project materialization. Mitigation: keep output as `GeneratedSources` only and retain purity tests.

## Recommendation

Proceed to proposal with the bounded whole-model orchestrator slice, gated only on the five product decisions above. The strongest default is `generate_model_sources`, table-order then enum-order then singleton-order aggregation, exact path collision rejection via typed error, and empty-model singleton output.
