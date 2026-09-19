# Delta for Spring Boot Generation

## ADDED Requirements

### Requirement: Whole-Model Source Aggregation

The system MUST provide a public pure function `generate_model_sources(model: RelationalModel, *, base_package: str = "com.modelia.generated") -> GeneratedSources` that accepts a complete `RelationalModel` and returns one in-memory `GeneratedSources` aggregate. The aggregate MUST contain generated files in this deterministic order: all table artifacts in `model.tables` order while preserving each table generator's internal file order; then all enum artifacts in `model.enum_types` order; then shared error artifacts; then the project singleton `src/main/resources/application.yml`. The aggregate MUST NOT sort artifacts alphabetically or reorder files beyond this contract.

#### Scenario: Normal model aggregates tables then enums then globals

- GIVEN a `RelationalModel` with tables `(Product, Order)` and enum types `(order_status,)`
- WHEN `generate_model_sources(model, base_package="com.example.generated")` is invoked
- THEN the returned `GeneratedSources.files` order starts with all `Product` table files in that table generator's order
- AND then contains all `Order` table files in that table generator's order
- AND then contains the `order_status` enum file
- AND then contains the shared error files
- AND ends with `src/main/resources/application.yml`

#### Scenario: Inheritance table keeps its table generator boundary inside the aggregate

- GIVEN a `RelationalModel` whose first table is a supported discriminator-backed `Vehicle` table and whose second table is a non-discriminator `Product` table
- WHEN `generate_model_sources(model)` is invoked
- THEN the aggregate begins with the `Vehicle` table artifacts exactly as `generate_table_sources(Vehicle)` defines them, including root entity, subclass entities, and root repository ordering
- AND the `Product` table artifacts appear only after all `Vehicle` table artifacts
- AND no inheritance DTO, service, controller, subclass repository, filtering API, or inheritance API expansion is added by whole-model aggregation

### Requirement: Whole-Model Singleton Artifacts

For every successful `generate_model_sources` invocation, the system MUST include the shared error source set exactly once and the project configuration source set exactly once. The shared error generation contract MUST receive the caller's `base_package`; the project configuration contract MUST remain package-independent. An empty `RelationalModel` MUST still return the project-level global artifacts only.

#### Scenario: Shared errors and application YAML are included exactly once

- GIVEN a `RelationalModel` with multiple tables and multiple enum types
- WHEN `generate_model_sources(model, base_package="com.example.generated")` is invoked
- THEN exactly one `ResourceNotFoundException.java` path is present
- AND exactly one `GlobalExceptionHandler.java` path is present
- AND exactly one `src/main/resources/application.yml` path is present
- AND shared error package paths and content use `com.example.generated`
- AND `application.yml` contains no Java package dependency

#### Scenario: Empty model yields globals

- GIVEN an empty `RelationalModel` with no tables and no enum types
- WHEN `generate_model_sources(model)` is invoked
- THEN the returned `GeneratedSources` contains only the shared error files and `src/main/resources/application.yml`
- AND the shared error files appear before `src/main/resources/application.yml`

### Requirement: Whole-Model Duplicate Path Rejection

Before returning a whole-model aggregate, the system MUST reject any exact duplicate `GeneratedFile.path` across all generated table, enum, shared error, and project configuration artifacts. Duplicate path rejection MUST raise a typed generator error under the existing `UngeneratableSourceError` family. On duplicate path failure, the system MUST NOT return a partial `GeneratedSources`, MUST NOT overwrite any file, MUST NOT deduplicate files, and MUST NOT silently keep the first or last occurrence.

#### Scenario: Duplicate exact output path fails atomically

- GIVEN a `RelationalModel` containing two source artifacts that would produce the same exact generated output path
- WHEN `generate_model_sources(model)` is invoked
- THEN a typed duplicate-path generator error is raised
- AND no `GeneratedSources` aggregate is returned
- AND no partial result is exposed to the caller

### Requirement: Whole-Model Determinism and Purity

`generate_model_sources` MUST be a pure function of the provided `RelationalModel` and `base_package`. For the same inputs, it MUST return equal `GeneratedSources` values with identical file paths, identical file ordering, and byte-identical content. It MUST NOT write or materialize files, inspect environment variables, open database connections, access the network, run subprocesses, compile Java, execute Gradle, use Docker, or invoke validation routines.

#### Scenario: Repeated whole-model generation is deterministic

- GIVEN the same `RelationalModel` value and the same `base_package`
- WHEN `generate_model_sources` is invoked twice
- THEN both returned `GeneratedSources` values are equal
- AND every corresponding file has the same path and byte-identical content

#### Scenario: Whole-model generation remains filesystem-free and runtime-free

- GIVEN a valid in-memory `RelationalModel` and no database or project directory available to the test process
- WHEN `generate_model_sources(model)` is invoked
- THEN generation succeeds using only in-memory inputs
- AND no filesystem write, generated-project materialization, environment read, database access, network access, subprocess, Java compilation, Gradle execution, Docker interaction, or validation call occurs

### Requirement: Existing Generator Contracts Are Preserved

Whole-model generation MUST preserve all existing table, enum, shared-error, and project-configuration generator contracts. It MUST NOT change lower-level generated paths, generated content, file ordering inside each lower-level generator result, supported inheritance table behavior, unsupported-shape typed errors, package propagation rules, or project configuration placeholders. It MUST NOT add OpenAPI, Postman, Domain Manifest, filtering/search metadata, generated filtering APIs, inheritance API expansion, frontend output, mobile output, Java `config/` classes, filesystem writing, project materialization, compilation, Docker behavior, or Gradle behavior.

#### Scenario: Lower-level generator outputs are unchanged inside the aggregate

- GIVEN a supported `Table`, a supported `EnumType`, the shared error source set, and the project configuration source set
- WHEN each lower-level generator is invoked directly and the same inputs are also generated through `generate_model_sources`
- THEN the corresponding files inside the whole-model aggregate have the same paths, ordering within their own generator boundary, and byte-identical content as the direct lower-level generator outputs
- AND the whole-model aggregate contains no out-of-scope OpenAPI, Postman, Manifest, filtering, frontend, mobile, Java `config/`, materialization, compilation, Docker, or Gradle artifact
