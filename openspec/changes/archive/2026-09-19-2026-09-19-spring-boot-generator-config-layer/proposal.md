# Proposal: Spring Boot Generator Config Layer

Change: `2026-09-19-spring-boot-generator-config-layer`

## Intent

Add the first project-level Spring Boot configuration generator slice for Modelia's generated backend output. The generator must produce exactly one in-memory generated source file at `src/main/resources/application.yml` and must keep all deployable runtime values as required environment-variable placeholders with no literal defaults.

This closes the current generated-backend gap where table, enum, and shared error sources exist, but the generated Spring Boot project has no application resource configuration artifact.

## Product decision captured

Placeholders in the generated `application.yml` must have no defaults, for example `${SERVER_PORT}` rather than `${SERVER_PORT:8080}`. This is intentional: defaults can silently hardcode deployment assumptions such as ports, hosts, JDBC URLs, usernames, passwords, or topology-specific values. Requiring the runtime environment to provide the values keeps local, Docker, VM, cloud, and production deployments explicit.

## Scope

In scope:

- Add a pure project-singleton generator entry point that returns `GeneratedSources`.
- Generate exactly one file: `src/main/resources/application.yml`.
- Keep the config generator separate from `generate_table_sources(Table)` and from per-table generation.
- Mirror shared artifact generator conventions already used by `generate_shared_error_sources(*, base_package)`:
  - no filesystem writes;
  - no database access;
  - no subprocesses;
  - no Java compilation;
  - deterministic in-memory output;
  - Jinja template rendering through the existing renderer environment.
- Use required environment-variable placeholders without defaults for runtime/deployment values.
- Include the minimal Spring Boot runtime configuration needed for this slice:
  - `spring.application.name: ${SPRING_APPLICATION_NAME}`;
  - `spring.datasource.url: ${SPRING_DATASOURCE_URL}`;
  - `spring.datasource.username: ${SPRING_DATASOURCE_USERNAME}`;
  - `spring.datasource.password: ${SPRING_DATASOURCE_PASSWORD}`;
  - `spring.jpa.hibernate.ddl-auto: ${SPRING_JPA_HIBERNATE_DDL_AUTO}`;
  - one Hibernate database platform/dialect placeholder, selected during design to avoid duplicate or conflicting properties;
  - `server.port: ${SERVER_PORT}`.
- Update the Spring Boot generation OpenSpec in a later phase so this project-level resource is allowed while table-output restrictions remain unchanged.

Out of scope / non-goals:

- Whole-model orchestrator or invocation that assembles an entire generated project.
- Java compilation, Gradle execution, Docker execution, or runtime smoke tests.
- Broader `config/` directory scaffolding or Java `@Configuration` classes.
- Generated frontend or mobile output.
- OpenAPI, Postman, or Domain Manifest artifacts.
- Inheritance API behavior changes.
- DTO, service, controller, entity, repository, enum, or shared error behavior changes.
- Any change that makes `generate_table_sources` emit config/resource files.

## Affected areas

- `backend/apps/spring_generator/emit/renderer.py`
  - Add a new public singleton entry point for project config generation.
  - Reuse the existing Jinja environment and `GeneratedSources` return convention.

- `backend/apps/spring_generator/emit/templates/application.yml.j2`
  - Add a simple deterministic YAML template with required placeholder-only values.

- `backend/apps/spring_generator/tests/`
  - Add focused tests for file count, path, placeholder-only content, absence of literal deployment values, determinism, and purity.
  - Extend existing purity/determinism coverage where appropriate.

- `openspec/specs/spring-boot-generation/spec.md`
  - In the design/spec phase, permit this single project-level resource without weakening the existing requirement that table generation does not produce `validation/`, `config/`, or resources files.

## Requirements

- The new generator MUST be callable without a `Table`, `EnumType`, or whole relational model.
- The new generator MUST return `GeneratedSources` containing exactly one `GeneratedFile`.
- The generated file path MUST be exactly `src/main/resources/application.yml`.
- The generated content MUST contain no Java package declaration.
- The generated content MUST use only bare placeholder syntax for runtime values: `${ENV_VAR}`.
- The generated content MUST NOT include placeholder defaults such as `${SERVER_PORT:8080}`.
- The generated content MUST NOT hardcode deployable values such as `localhost`, `db`, `postgres`, `5432`, `8080`, `0.0.0.0`, `http://`, `https://`, `jdbc:`, usernames, or passwords.
- The generator MUST be deterministic and byte-identical across repeated calls.
- The generator MUST remain pure: no filesystem writes, no database access, no validation-engine calls, and no subprocesses.
- `generate_table_sources` MUST continue to emit only table-scoped Java artifacts and MUST NOT emit `application.yml`.
- `generate_shared_error_sources` MUST remain unchanged in behavior.

## Success criteria

- A call to the new project config generator returns one `GeneratedSources` object with one file at `src/main/resources/application.yml`.
- The file content includes the agreed Spring Boot YAML keys with required no-default environment placeholders.
- Tests prove the output has no hardcoded deployment values or placeholder defaults.
- Tests prove the output is deterministic and generated without DB access or validation calls.
- Existing table, enum, inheritance, and shared error generation tests continue to pass unchanged.
- The OpenSpec requirement boundary distinguishes project-level resources from per-table Java source generation.

## Risks

- Spring Boot 4.x configuration recommendations may change around Hibernate dialect/platform properties; the design phase should choose one property and avoid emitting duplicates.
- Overconfiguration could introduce behavior not requested by the model, especially logging, OpenAPI/springdoc, or `open-in-view` settings.
- Placeholder defaults would violate the deployment-safety decision by smuggling hardcoded local assumptions into generated code.
- A standalone singleton entry point can be forgotten by future orchestration; whole-model invocation is intentionally deferred and must be handled by a later change.
- Spec wording could accidentally allow config output from `generate_table_sources`; the spec update must preserve the per-table boundary.

## Rollback

Rollback is straightforward because the slice is additive and pure:

- Remove the project config generator entry point.
- Remove the `application.yml.j2` template.
- Remove associated tests and spec additions.
- No database migrations, runtime state, generated Java compilation, or persisted user data are affected.

## Next recommended phase

Proceed to design for `2026-09-19-spring-boot-generator-config-layer`, focusing on the exact public function name, the final Hibernate dialect/platform property, and the test matrix that guards no-default placeholders and no hardcoded deployment values.
