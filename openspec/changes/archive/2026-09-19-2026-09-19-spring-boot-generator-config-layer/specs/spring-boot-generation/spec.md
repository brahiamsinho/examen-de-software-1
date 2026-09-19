# Delta for Spring Boot Generation

## ADDED Requirements

### Requirement: Project Singleton Application YAML Generation

The system MUST provide a pure project-singleton Spring Boot configuration generator entry point that is independent of `Table`, `EnumType`, relational model, orchestration, and per-table generation inputs. The entry point MUST return the existing generated-source typed contract as `GeneratedSources` containing exactly one `GeneratedFile`. That file's path MUST be exactly `src/main/resources/application.yml`, and its content MUST be YAML resource text with no Java package declaration.

The generated `application.yml` MUST contain exactly the bounded project runtime configuration for this slice:

- `spring.application.name: ${SPRING_APPLICATION_NAME}`
- `spring.datasource.url: ${SPRING_DATASOURCE_URL}`
- `spring.datasource.username: ${SPRING_DATASOURCE_USERNAME}`
- `spring.datasource.password: ${SPRING_DATASOURCE_PASSWORD}`
- `spring.jpa.hibernate.ddl-auto: ${JPA_DDL_AUTO}`
- `server.port: ${SERVER_PORT}`

The generator MUST use required environment-variable placeholders with no defaults for every emitted runtime value. The generator MUST NOT emit placeholder defaults such as `${SERVER_PORT:8080}`. The generator MUST NOT hardcode deployable values, including `localhost`, `db`, `postgres`, `5432`, `8080`, `0.0.0.0`, `http://`, `https://`, `jdbc:`, usernames, or passwords. The generator MUST NOT emit an explicit Hibernate dialect or platform setting unless a later accepted specification is backed by official source evidence.

#### Scenario: Project config generator emits exactly one application YAML file

- GIVEN the project singleton Spring Boot configuration generator is invoked without a `Table`, without an `EnumType`, and without a whole relational model
- WHEN the returned `GeneratedSources` is inspected
- THEN it contains exactly one `GeneratedFile`
- AND that file path is exactly `src/main/resources/application.yml`
- AND that file content contains no Java package declaration

#### Scenario: Application YAML contains only required no-default placeholders

- GIVEN the project singleton Spring Boot configuration generator is invoked
- WHEN the generated `application.yml` content is inspected
- THEN it contains `spring.application.name: ${SPRING_APPLICATION_NAME}`
- AND it contains `spring.datasource.url: ${SPRING_DATASOURCE_URL}`
- AND it contains `spring.datasource.username: ${SPRING_DATASOURCE_USERNAME}`
- AND it contains `spring.datasource.password: ${SPRING_DATASOURCE_PASSWORD}`
- AND it contains `spring.jpa.hibernate.ddl-auto: ${JPA_DDL_AUTO}`
- AND it contains `server.port: ${SERVER_PORT}`
- AND it contains no placeholder with a default value

#### Scenario: Application YAML omits unsupported configuration scopes

- GIVEN the project singleton Spring Boot configuration generator is invoked
- WHEN the generated `application.yml` content is inspected
- THEN it contains no Hibernate dialect or database platform property
- AND it contains no OpenAPI, Postman, Manifest, frontend, mobile, logging, Docker, or Java `@Configuration` scaffolding settings

### Requirement: Project Config Generation Purity and Determinism

The project singleton Spring Boot configuration generator MUST be deterministic and byte-identical across repeated invocations. It MUST be filesystem-free and side-effect-free: it MUST NOT write files, read files, access a database, call validation-engine routines, run subprocesses, compile Java, execute Gradle, inspect runtime environment variables, or perform network access.

#### Scenario: Repeated config generation is byte-identical

- GIVEN the project singleton Spring Boot configuration generator is invoked twice in the same test process
- WHEN the two returned `GeneratedSources` values are compared
- THEN they contain the same single path in the same order
- AND the corresponding `application.yml` content is byte-identical

#### Scenario: Config generation performs no filesystem or external effects

- GIVEN filesystem writes, database access, validation calls, subprocess execution, environment inspection, and network access are guarded by test doubles or spies
- WHEN the project singleton Spring Boot configuration generator is invoked
- THEN no guarded operation is called
- AND generation still returns the single in-memory `application.yml` file

### Requirement: Project Config Boundary from Table Generation

Project-level Spring Boot resource generation MUST remain separate from per-table generation. `generate_table_sources(table, *, base_package)` MUST NOT emit `src/main/resources/application.yml` and MUST NOT emit any project configuration or resource file. The project singleton configuration generator MUST NOT emit Java source, DTOs, services, controllers, repositories, entities, enums, shared errors, OpenAPI, Postman, Manifest, frontend, or mobile artifacts.

#### Scenario: Table generation does not emit application YAML

- GIVEN any supported non-discriminator `Table`
- WHEN `generate_table_sources(table, *, base_package)` is invoked
- THEN no emitted path is `src/main/resources/application.yml`
- AND no emitted path is under `src/main/resources/`

#### Scenario: Inheritance table generation does not emit application YAML

- GIVEN any supported discriminator-backed `Table`
- WHEN `generate_table_sources(table, *, base_package)` is invoked
- THEN no emitted path is `src/main/resources/application.yml`
- AND no emitted path is under `src/main/resources/`

#### Scenario: Project config generator emits no table-scoped artifacts

- GIVEN the project singleton Spring Boot configuration generator is invoked
- WHEN the returned paths are inspected
- THEN no emitted path is under `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, `errors/`, `validation/`, or `config/`
- AND no emitted artifact is an entity, repository, DTO, service, controller, enum, shared error, OpenAPI, Postman, Manifest, frontend, or mobile file

## MODIFIED Requirements

### Requirement: Package and File Path Layout

Generated Java files MUST be placed only under the `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, and `errors/` subdirectories of the §22 layout (`domain/persistence/application/api/validation/errors/config`). The `validation/` and `config/` subdirectories MUST NOT be produced by this slice. For non-discriminator tables, `generate_table_sources(table, *, base_package)` MUST emit exactly six files per call, in fixed layer order: `domain/<E>.java`, `persistence/<E>Repository.java`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, `api/<E>Controller.java`. For supported discriminator-backed tables, `generate_table_sources(table, *, base_package)` MUST emit only `domain/` entity classes and the root `persistence/` repository according to the inheritance artifact boundary. A separate `generate_shared_error_sources(*, base_package)` entry point, taking no `Table`, MUST emit exactly two per-project Java files: `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java`. A separate project singleton configuration generator entry point MUST emit exactly one resource file at `src/main/resources/application.yml`. `generate_table_sources` MUST NOT emit any file under `errors/` or `src/main/resources/`.

(Previously: project-level resource generation was not allowed by this layout requirement; the requirement only described table Java files and shared error Java files.)

#### Scenario: A non-discriminator table yields six layered files under domain, persistence, application, and api

- GIVEN the `Product` table generated end to end via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN exactly six files exist, one each at `domain/`, `persistence/`, `application/dto/<E>RequestDto.java`, `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`, and `api/<E>Controller.java`, in that fixed order

#### Scenario: A discriminator-backed table yields only domain and root persistence files

- GIVEN a supported discriminator-backed `Vehicle` table generated via `generate_table_sources`
- WHEN the set of emitted file paths is inspected
- THEN every emitted path is under `domain/` or is the root repository under `persistence/`
- AND no DTO, service, controller, shared error, validation, config, resource, or application YAML path is emitted

#### Scenario: Error sources are emitted only by the shared entry point

- GIVEN `generate_shared_error_sources(base_package=...)` is invoked
- WHEN the returned files are inspected
- THEN exactly two files exist under `errors/`, and no file under `errors/` is produced by any `generate_table_sources` call

#### Scenario: Validation and config directories remain forbidden

- GIVEN the `Product` table generated end to end, the shared error sources generated once, and the project singleton configuration generated once
- WHEN the combined set of emitted file paths is inspected
- THEN no file exists under `validation/` or `config/`

#### Scenario: Project application YAML is emitted only by the project singleton configuration generator

- GIVEN table generation, shared error generation, enum generation, and project singleton configuration generation are each invoked through their own entry point
- WHEN all returned file paths are inspected
- THEN only the project singleton configuration generator emits `src/main/resources/application.yml`
- AND no other generator emits a path under `src/main/resources/`
