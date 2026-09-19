# Exploration: Spring Boot Generator Config Layer

Change: `2026-09-19-spring-boot-generator-config-layer`
Phase: explore
Artifact store: openspec
Date: 2026-09-19

## Executive summary

Modelia's Spring Boot generator is ready for a small project-level configuration slice, but only as a pure, filesystem-free source generator. The existing generator already has a project-singleton pattern in `generate_shared_error_sources(*, base_package) -> GeneratedSources`; the config slice should mirror that pattern rather than attach configuration to `generate_table_sources(Table)`. The bounded first slice should generate exactly one project-level resource, `src/main/resources/application.yml`, using environment-variable placeholders for all deployable/runtime values and no literal host, port, JDBC URL, username, password, or deployment URL. It should not introduce a whole-model orchestrator, Java compilation, OpenAPI, Postman, Domain Manifest, inheritance API behavior, or generated frontend/mobile output.

## Current generator architecture

- `backend/apps/spring_generator/domain/sources.py` defines the frozen output model: `GeneratedFile(path, contents)` and `GeneratedSources(files=...)`; both are in-memory only.
- `backend/apps/spring_generator/emit/renderer.py` is the public API surface and owns the single Jinja `Environment` rooted at `backend/apps/spring_generator/emit/templates/`.
- `generate_table_sources(table, *, base_package="com.modelia.generated")` validates the package, rejects unsupported table shapes, and emits table-scoped Java source.
- Non-inheritance tables emit six files in fixed order: `domain/`, `persistence/`, `application/dto/Request`, `application/dto/Response`, `application/Service`, `api/Controller`.
- Discriminator-backed Single Table inputs branch to inheritance rendering and emit only root/subclass domain classes plus the root repository.
- `generate_enum_source(enum_type, *, base_package)` emits one standalone Java enum under `domain/`.
- `generate_shared_error_sources(*, base_package)` emits project-singleton `errors/ResourceNotFoundException.java` and `errors/GlobalExceptionHandler.java` independent of any table.
- `backend/apps/spring_generator/emit/context.py` centralizes branching and import selection; templates are data-driven.
- `backend/apps/spring_generator/emit/inheritance_context.py` is a precedent for a focused context sibling module when a concern becomes too specialized for `context.py`.

## Shared artifact and singleton patterns

The config layer is a project-level artifact, like shared errors, not a per-table artifact. The clean product/API shape is therefore a new sibling entry point in `emit/renderer.py`, likely:

```python
def generate_project_config_sources(*, application_name: str = "modelia-generated") -> GeneratedSources
```

Open product decision: whether this entry point should also accept an application name, and if so what whitelist applies. `base_package` is not useful for `application.yml` because the file path and contents do not depend on Java packages.

Reusable patterns:

- Return `GeneratedSources`, even for a single file, matching `generate_shared_error_sources`.
- Keep the function pure: no filesystem writes, DB access, subprocesses, Docker access, Java tooling, or validation-engine calls.
- Use Jinja templates under `backend/apps/spring_generator/emit/templates/`, not Django app-root templates.
- Keep deterministic byte-identical output across repeated calls.
- Extend purity and no-concat guard expectations rather than adding a runtime parser or YAML dependency.

## Canonical Spring Boot generation spec

Evidence from `openspec/specs/spring-boot-generation/spec.md` and `product-04-next-django.md`:

- Product §22 requires generated backends to target Java 21 LTS, Spring Boot 4.x, Spring Web MVC, Spring Data JPA, Hibernate, Jakarta Validation, Jackson, springdoc-openapi, PostgreSQL, and Gradle.
- Product §22 names `config/` as part of the generated backend's conceptual structure, but current OpenSpec explicitly forbids `config/` output for previous slices.
- The active spec currently says generated files are placed only under `domain/`, `persistence/`, `application/`, `application/dto/`, `api/`, and `errors/`, and that `validation/` and `config/` are not produced by those slices.
- A config slice must update the spec with a new project-level resource path; previous table-slice restrictions should remain true for `generate_table_sources`.
- `src/main/resources/application.yml` is not a Java package layer and should be specified separately from the Java source layout.

## Current templates

Existing templates under `backend/apps/spring_generator/emit/templates/`:

- `Entity.java.j2`
- `InheritanceEntity.java.j2`
- `Repository.java.j2`
- `Enum.java.j2`
- `RequestDto.java.j2`
- `ResponseDto.java.j2`
- `Service.java.j2`
- `Controller.java.j2`
- `ResourceNotFoundException.java.j2`
- `GlobalExceptionHandler.java.j2`

Likely new template:

- `backend/apps/spring_generator/emit/templates/application.yml.j2`

Template conventions to preserve:

- No source string assembly in Python by `+`, `str.join`, `%`, or f-strings inside `emit/`; `test_no_concat_guard.py` enforces this with LibCST.
- Keep branching in Python context builders or simple renderer arguments, not in complicated Jinja control flow.
- Be careful with Jinja `trim_blocks`/`lstrip_blocks`; prefer simple static YAML here.

## Project environment and Docker configuration

Main Modelia environment evidence:

- `docker-compose.yml` uses environment files, Compose service names, and no committed secrets.
- Django backend config demonstrates the desired deployability pattern: values come from env files or Compose `environment`, not literals in source.
- `backend/env.example` documents environment variables for Postgres, Redis, CORS, CSRF/session, email, and frontend base URL.
- Compose service-name lesson: inside a container, `localhost` is the container itself; runtime hosts/ports must be externalized.

Generated backend implication:

- `application.yml` must not hardcode `localhost`, `db`, `postgres`, `5432`, `8080`, JDBC URLs, usernames, passwords, or public API URLs.
- It may reference environment variables such as `${SPRING_DATASOURCE_URL}` because deployment topology belongs to the generated app's runtime environment.
- Avoid creating generated Docker Compose, Dockerfile, Gradle, or env example in this first slice; those belong to later infrastructure/compiler cycles.

## Bounded first slice recommendation

In scope:

1. Add a project-singleton config generation entry point in `backend/apps/spring_generator/emit/renderer.py`.
2. Add a deterministic Jinja template for exactly one file: `src/main/resources/application.yml`.
3. Use only environment-variable placeholders for deployable runtime values.
4. Add tests under `backend/apps/spring_generator/tests/` for path, contents, determinism, purity, and no host/port/URL literals.
5. Update `openspec/specs/spring-boot-generation/spec.md` to allow this config project resource while keeping `generate_table_sources` table outputs unchanged.

Out of scope:

- Whole-model orchestrator or generated-project writer.
- Java compilation, Gradle project generation, Docker generation, or runtime smoke tests.
- OpenAPI, Postman, Domain Manifest.
- Inheritance DTO/service/controller/API behavior.
- Generated frontend/mobile.
- Validation layer generation.
- Spring `@Configuration` Java classes unless a later product decision requires them.

## Candidate application.yml shape

A minimal first slice can require these keys:

```yaml
spring:
  application:
    name: ${SPRING_APPLICATION_NAME}
  datasource:
    url: ${SPRING_DATASOURCE_URL}
    username: ${SPRING_DATASOURCE_USERNAME}
    password: ${SPRING_DATASOURCE_PASSWORD}
  jpa:
    hibernate:
      ddl-auto: ${SPRING_JPA_HIBERNATE_DDL_AUTO}
    properties:
      hibernate:
        dialect: ${SPRING_JPA_DATABASE_PLATFORM}
server:
  port: ${SERVER_PORT}
```

Potentially useful but should be explicit product decisions, not silently added:

- `springdoc` keys, because OpenAPI is explicitly out of this slice.
- `spring.jpa.open-in-view`, because it is an architectural behavior choice, not an environment placeholder.
- SQL logging keys, because they can leak data and should not be emitted without a logging policy.
- Default values inside placeholders, e.g. `${SERVER_PORT:8080}`; the user's rule says no literal host/port/URL, so the safest first slice uses placeholders without literal defaults.

## Exact likely source paths

Create/modify:

- `backend/apps/spring_generator/emit/renderer.py` — add the public singleton entry point and render path.
- `backend/apps/spring_generator/emit/templates/application.yml.j2` — new YAML template.
- Optional only if validation is needed: `backend/apps/spring_generator/emit/config_context.py` — small frozen context for application name and env-var names. For a static placeholder-only file, this may be unnecessary.
- `openspec/specs/spring-boot-generation/spec.md` — add a requirement for project-level Spring configuration generation.

Do not modify for this slice unless tests expose a real need:

- `backend/apps/spring_generator/emit/context.py` — config is not table context.
- `backend/apps/spring_generator/domain/sources.py` — `GeneratedSources` already fits.
- `backend/apps/spring_generator/emit/errors.py` — no table/enum rejection needed unless accepting a configurable application name with invalid characters.
- Any Django settings, Docker Compose, frontend, mobile, or relational mapper file.

## Exact likely test paths

Create:

- `backend/apps/spring_generator/tests/test_config_sources.py`

Extend:

- `backend/apps/spring_generator/tests/test_purity.py` — new config entry point succeeds without DB and never calls validation.
- `backend/apps/spring_generator/tests/test_determinism.py` — repeated config generation is byte-identical and path order is stable if using `GeneratedSources`.
- `backend/apps/spring_generator/tests/test_no_concat_guard.py` — should remain unchanged but must stay green.

Possible assertions for `test_config_sources.py`:

- returns exactly one file at `src/main/resources/application.yml`.
- content contains no Java `package` line.
- content contains `spring.application.name`, `spring.datasource.url`, username, password, JPA Hibernate ddl-auto, Hibernate dialect, and `server.port`.
- each runtime value uses `${ENV_VAR}` placeholder syntax.
- content does not contain `localhost`, `http://`, `https://`, `jdbc:`, `5432`, `8080`, `0.0.0.0`, `postgres://`, or committed credentials.
- `generate_table_sources` still emits no `/config/` file and no resources file.
- `generate_shared_error_sources` remains exactly two `errors/` files.

## Product decisions to resolve before propose/design

1. **Entry point name and parameters:** should it be `generate_project_config_sources()` with no arguments, or should it accept `application_name`?
2. **Required config keys:** confirm the first slice's key set: datasource URL/username/password, JPA ddl-auto, Hibernate dialect/platform, application name, and server port.
3. **Placeholder defaults:** confirm that placeholders must not include literal defaults such as `${SERVER_PORT:8080}`.
4. **Application name source:** if `spring.application.name` is required, should it be `${SPRING_APPLICATION_NAME}` only, or may the generator bake in a sanitized model/project name? The user's no-hardcoding rule favors the placeholder-only version.
5. **Hibernate dialect property name:** choose between `spring.jpa.database-platform` and `spring.jpa.properties.hibernate.dialect`; avoid emitting both unless a later Spring Boot 4 compatibility check says so.

## Risks

- **Spring Boot version risk:** Spring Boot 4.x may alter recommended Hibernate dialect/property defaults; no Java compilation/runtime check exists yet.
- **Overconfiguration risk:** adding nonessential JPA/logging/springdoc settings could create product behavior not requested by the model.
- **False hardcoding risk:** placeholder defaults like `${SERVER_PORT:8080}` may violate the user's no-literal-port constraint.
- **API naming risk:** a project-level entry point without a future orchestrator may be called zero or multiple times; orchestration remains a later concern.
- **Spec boundary risk:** previous spec text forbids `config/`; the change must precisely allow `application.yml` without making table generators emit config.

## Next recommended phase

Proceed to `sdd-propose` for `2026-09-19-spring-boot-generator-config-layer`, but first resolve one product-risk question: should the generated `application.yml` use only bare environment placeholders with no defaults for all runtime values, including `SERVER_PORT`, or may safe local defaults be included?
