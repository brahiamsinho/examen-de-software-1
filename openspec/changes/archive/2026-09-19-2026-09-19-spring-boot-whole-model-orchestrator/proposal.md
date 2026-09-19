# Proposal: Spring Boot whole-model source orchestrator

Change: `2026-09-19-spring-boot-whole-model-orchestrator`

## Intent

Add a pure aggregate generator for Spring Boot source artifacts:

```python
def generate_model_sources(
    model: RelationalModel,
    *,
    base_package: str = "com.modelia.generated",
) -> GeneratedSources:
    ...
```

The function should walk a complete `RelationalModel`, delegate to the existing table, enum, shared-error, and project-config generators, and return one deterministic in-memory `GeneratedSources` aggregate.

This closes the current project-level gap between the relational mapper and the Spring Boot generator: callers can generate all currently supported source text for a whole model without materializing files, compiling Java, or invoking any runtime tooling.

## Scope

### In scope

- Add the public `generate_model_sources(model, *, base_package="com.modelia.generated")` API.
- Preserve the existing pure, filesystem-free, DB-free generator style.
- Aggregate generated files in this exact order:
  1. all table artifacts, in `model.tables` order, preserving each table generator's internal file order;
  2. all enum artifacts, in `model.enum_types` order;
  3. shared error artifacts exactly once;
  4. project config artifacts exactly once.
- Treat global artifacts as project singletons:
  - shared errors are generated once per aggregate;
  - `src/main/resources/application.yml` is generated once per aggregate.
- Emit global artifacts even for an empty `RelationalModel`.
- Detect exact duplicate generated output paths across the complete aggregate.
- Raise a typed generator error for duplicate output paths.
- Return no partial aggregate when any exact duplicate output path is detected.
- Keep `base_package` propagation limited to generators that already accept it: table sources, enum source, and shared errors. Project config remains package-independent.

### Out of scope

- Generated-project materialization or filesystem writing.
- Java compilation, Gradle execution, Docker, CI, or runtime smoke tests.
- OpenAPI generation.
- Postman collection generation.
- Domain Manifest generation.
- Filtering/search metadata or generated filtering APIs.
- Inheritance API expansion beyond whatever `generate_table_sources` already emits.
- Frontend generation.
- Mobile generation.
- New Java `config/` classes or broader Spring runtime scaffolding.
- Changes to the relational mapper contract.

## Affected areas

- `backend/apps/spring_generator/emit/renderer.py`
  - Add `generate_model_sources`.
  - Add small private aggregation/collision helpers if useful.
  - Delegate to existing lower-level generators rather than duplicating rendering behavior.

- `backend/apps/spring_generator/emit/errors.py`
  - Add a typed duplicate-path generator error under the existing `UngeneratableSourceError` family.

- `backend/apps/spring_generator/tests/`
  - Add coverage for aggregate order, singleton inclusion, empty model behavior, custom package propagation, determinism, purity, and duplicate path rejection.

## Behavior details

### Aggregate order

The aggregate order is a product contract:

1. tables;
2. enums;
3. shared errors;
4. project config.

The orchestrator should not sort artifacts alphabetically. It should preserve the already deterministic order supplied by `RelationalModel.tables`, `RelationalModel.enum_types`, and the existing lower-level generators.

### Global artifacts

Global means generated once per whole generated project, not once per table or enum:

- `generate_shared_error_sources(base_package=base_package)` contributes the shared error files once.
- `generate_project_config_sources()` contributes `src/main/resources/application.yml` once.

An empty model still represents a project-level generation request, so it should return the global artifacts only.

### Duplicate output paths

Before returning a `GeneratedSources` aggregate, the orchestrator must scan the ordered generated files for exact duplicate `GeneratedFile.path` values.

If any path appears more than once:

- raise the new typed duplicate-path generator error;
- do not return a partial `GeneratedSources`;
- do not overwrite, deduplicate, or keep first/last silently.

This rule covers table/table, table/enum, enum/enum, and singleton duplication bugs using the path contract that already encodes Java package and generated simple names.

## Risks and mitigations

- **Risk: aggregate order becomes unclear or unstable.**
  - Mitigation: document and test the exact order: tables, enums, globals.

- **Risk: duplicate paths are hidden by mapping-style conversion.**
  - Mitigation: detect duplicate paths from the ordered file list before constructing or exposing any mapping behavior.

- **Risk: singleton artifacts accidentally run per table.**
  - Mitigation: tests with multiple tables assert exactly one shared-error set and exactly one `application.yml`.

- **Risk: this slice drifts into project materialization or compilation.**
  - Mitigation: keep the output type as `GeneratedSources` only and add no filesystem, Docker, JVM, Gradle, or CI behavior.

- **Risk: semantic Java conflicts beyond exact paths remain undetected.**
  - Mitigation: accept exact path detection for this slice; broader semantic validation belongs to future compilation/materialization work.

## Rollback

Rollback is straightforward because the change is additive and pure:

- remove the `generate_model_sources` API;
- remove the duplicate-path error type if unused elsewhere;
- remove the new tests;
- keep existing table, enum, shared-error, and project-config generators unchanged.

No database migrations, generated files on disk, runtime services, or deployment configuration are introduced by this proposal.

## Success criteria

- `generate_model_sources(RelationalModel(...))` returns a deterministic `GeneratedSources` aggregate.
- Table artifacts appear before enum artifacts.
- Shared errors appear exactly once.
- `src/main/resources/application.yml` appears exactly once.
- `RelationalModel()` returns the global artifacts only.
- Custom `base_package` affects table, enum, and shared-error Java paths/content consistently.
- Exact duplicate output paths raise the typed duplicate-path generator error.
- Duplicate-path failure returns no partial aggregate.
- Existing lower-level generator behavior remains unchanged.
- No materialization, compilation, Docker, Gradle, OpenAPI, Postman, Manifest, filtering, inheritance API, frontend, or mobile behavior is added.

## Proposal question round

No additional question round is needed for this proposal because the orchestrator supplied the confirmed product decisions for this phase: API name, aggregate order, singleton semantics, empty-model behavior, duplicate-path handling, and explicit exclusions.
