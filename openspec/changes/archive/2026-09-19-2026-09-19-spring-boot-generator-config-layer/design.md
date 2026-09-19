# Design: Spring Boot Generator Config Layer

Change: `2026-09-19-spring-boot-generator-config-layer`

## Executive summary

Add one pure project-singleton Spring Boot configuration generator that returns a `GeneratedSources` containing exactly one in-memory file at `src/main/resources/application.yml`. The generator is separate from all per-table, enum, inheritance, and shared-error generation. It uses the existing Jinja environment and typed generated-source contract, emits only required no-default environment placeholders, includes `JPA_DDL_AUTO`, and emits no Hibernate dialect or database platform setting.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| DD1 | Public entry point: `generate_project_config_sources() -> GeneratedSources`. | Mirrors `generate_shared_error_sources(*, base_package)` as a project-singleton public API while avoiding `Table`, `EnumType`, relational model, orchestration, or Java package inputs. |
| DD2 | The entry point takes no parameters. | The file path and content are fixed by spec; accepting an application name or package would invite hardcoded runtime values or irrelevant Java-package coupling. |
| DD3 | Source implementation path: `backend/apps/spring_generator/emit/renderer.py`. | This is the existing public Spring generator API surface and owns the shared Jinja `_ENVIRONMENT`. |
| DD4 | Template path: `backend/apps/spring_generator/emit/templates/application.yml.j2`. | Keeps rendering with the same template root and avoids Python string assembly in `emit/`. |
| DD5 | Template context shape is an empty mapping: `{}`. | All emitted placeholders are static literal YAML text; no runtime value, model value, package, filesystem value, or environment lookup is needed. |
| DD6 | Stable file order is a one-item tuple: `("src/main/resources/application.yml",)`. | The generator returns exactly one `GeneratedFile`, so deterministic order is explicit and byte-stable. |
| DD7 | YAML emits exactly the bounded keys from the accepted delta. | Prevents overconfiguration and keeps this slice limited to project runtime config. |
| DD8 | Use `spring.jpa.hibernate.ddl-auto: ${JPA_DDL_AUTO}` exactly. | The delta spec supersedes the exploratory candidate name and the user explicitly requested `JPA_DDL_AUTO`. |
| DD9 | Emit no `spring.jpa.database-platform` and no `hibernate.dialect`. | The accepted delta forbids explicit dialect/platform without later official-source evidence. |
| DD10 | No per-table behavior changes. | `generate_table_sources` must remain a table-scoped Java generator and must not emit `application.yml` or resources. |

## Public API contract

```python
def generate_project_config_sources() -> GeneratedSources:
    ...
```

Contract:

- Callable without `Table`, `EnumType`, relational model, `base_package`, application name, or orchestration object.
- Returns `GeneratedSources(files=(GeneratedFile(path="src/main/resources/application.yml", contents=<rendered_yaml>),))`.
- Performs no filesystem writes, database access, validation-engine calls, subprocess calls, Java compilation, Gradle execution, network access, or environment-variable inspection.
- Reuses `_ENVIRONMENT.get_template("application.yml.j2")` from `renderer.py`.
- Does not call `_validate_base_package`, because no Java package is accepted or emitted.

## Generated YAML contract

Template file: `backend/apps/spring_generator/emit/templates/application.yml.j2`

Exact intended content shape:

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
      ddl-auto: ${JPA_DDL_AUTO}
server:
  port: ${SERVER_PORT}
```

Rules:

- No Java `package` declaration.
- No placeholder defaults such as `${SERVER_PORT:8080}`.
- No hardcoded deployable literals such as `localhost`, `db`, `postgres`, `5432`, `8080`, `0.0.0.0`, `http://`, `https://`, `jdbc:`, usernames, or passwords.
- No dialect/platform key.
- No OpenAPI, Postman, Manifest, frontend, mobile, logging, Docker, Java `@Configuration`, `validation/`, or `config/` settings.

## Data flow

1. Caller invokes `generate_project_config_sources()`.
2. `renderer.py` retrieves `application.yml.j2` from the existing `_ENVIRONMENT`.
3. The template is rendered with no dynamic context: `template.render()` or `template.render({})`.
4. The rendered content is wrapped in `GeneratedFile(path="src/main/resources/application.yml", contents=...)`.
5. The file is returned inside `GeneratedSources(files=(...,))`.

No model, database, filesystem output, environment lookup, subprocess, or validation layer participates in this flow.

## File changes for implementation phase

Create/modify only these implementation files:

| Path | Action | Responsibility |
|------|--------|----------------|
| `backend/apps/spring_generator/emit/renderer.py` | Modify | Add `generate_project_config_sources()` beside `generate_shared_error_sources()` and reuse `_ENVIRONMENT`. |
| `backend/apps/spring_generator/emit/templates/application.yml.j2` | Create | Static YAML template containing the six required no-default placeholders. |
| `backend/apps/spring_generator/tests/test_project_config_sources.py` | Create | Focused contract tests for path, content, exclusions, stable order, and generator boundary. |
| `backend/apps/spring_generator/tests/test_purity.py` | Modify | Add config generator purity checks beside table and shared-error checks. |
| `backend/apps/spring_generator/tests/test_determinism.py` | Modify | Add repeated-call byte identity check for config generation. |

Do not modify for this slice:

- `backend/apps/spring_generator/domain/sources.py`
- `backend/apps/spring_generator/emit/context.py`
- `backend/apps/spring_generator/emit/inheritance_context.py`
- `backend/apps/spring_generator/emit/errors.py`
- Per-table templates
- Django settings, Docker files, frontend, mobile, relational mapping, or whole-model orchestration

## Exact stable file order

For `generate_project_config_sources()`:

```text
1. src/main/resources/application.yml
```

This order is independent of table, enum, inheritance, and shared error generation. Combined generation order is not introduced in this slice because a whole-project orchestrator remains out of scope.

Existing per-table order remains unchanged:

```text
1. domain/<E>.java
2. persistence/<E>Repository.java
3. application/dto/<E>RequestDto.java
4. application/dto/<E>ResponseDto.java
5. application/<E>Service.java
6. api/<E>Controller.java
```

Existing shared-error order remains unchanged:

```text
1. errors/ResourceNotFoundException.java
2. errors/GlobalExceptionHandler.java
```

## Focused TDD matrix

| Test file | Test | Assertions |
|-----------|------|------------|
| `test_project_config_sources.py` | `test_returns_exactly_one_application_yml_file` | `len(sources.files) == 1`; only path is `src/main/resources/application.yml`; returned object is `GeneratedSources`. |
| `test_project_config_sources.py` | `test_application_yml_contains_no_java_package_declaration` | Content does not contain `package ` or Java package syntax. |
| `test_project_config_sources.py` | `test_application_yml_contains_required_no_default_placeholders` | Content contains the six exact lines for `SPRING_APPLICATION_NAME`, `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, `JPA_DDL_AUTO`, and `SERVER_PORT`. |
| `test_project_config_sources.py` | `test_application_yml_contains_no_placeholder_defaults` | Regex rejects `${NAME:...}` and similar colon-default placeholder forms. |
| `test_project_config_sources.py` | `test_application_yml_contains_no_hardcoded_deployable_values` | Reject `localhost`, `db`, `postgres`, `5432`, `8080`, `0.0.0.0`, `http://`, `https://`, `jdbc:` and obvious username/password literals outside placeholder names. |
| `test_project_config_sources.py` | `test_application_yml_omits_dialect_and_platform` | Reject `dialect`, `database-platform`, and `hibernate.dialect`. |
| `test_project_config_sources.py` | `test_application_yml_omits_excluded_scopes` | Reject OpenAPI, springdoc, Postman, Manifest, frontend, mobile, logging, Docker, and `@Configuration` settings. |
| `test_project_config_sources.py` | `test_project_config_generator_emits_no_table_or_shared_error_artifacts` | Only resource path exists; no path under `domain/`, `persistence/`, `application/`, `api/`, `errors/`, `validation/`, or `config/`. |
| `test_project_config_sources.py` | `test_table_generation_does_not_emit_resources` | `generate_table_sources(...)` paths do not equal `src/main/resources/application.yml` and do not start with `src/main/resources/`. |
| `test_project_config_sources.py` | `test_shared_error_generation_does_not_emit_resources` | `generate_shared_error_sources(...)` paths do not start with `src/main/resources/` and remain exactly two error files. |
| `test_determinism.py` | `test_project_config_generation_is_byte_identical` | Two calls compare equal; one path in same order; contents byte-identical. |
| `test_purity.py` | `test_project_config_generation_succeeds_with_no_db_access` | Passing test without `db`/`django_db` proves no DB connection; one file returned. |
| `test_purity.py` | `test_project_config_generation_never_calls_validation_engine` | `apps.uml_modeling.validation.engine.validate` spy is not called. |
| `test_purity.py` | `test_project_config_generation_does_not_inspect_environment_or_run_subprocesses` | Spies/patches for `os.getenv`, `os.environ.get`, and subprocess entry points are not called if practical within existing test style. |

## Boundary and exclusions

This design intentionally excludes:

- Whole-model generator orchestration.
- Any file writer or generated-project materializer.
- Java compilation, Gradle execution, Docker execution, and runtime smoke tests.
- Hibernate dialect/platform configuration.
- Springdoc/OpenAPI, Postman, Domain Manifest, frontend, mobile, logging, Docker, and Java `@Configuration` scaffolding.
- Changes to inheritance API behavior.
- Changes to DTO, service, controller, entity, repository, enum, shared error, validation, or per-table generation behavior.

## Rollout plan

1. Add failing tests for the public API, exact YAML content, exclusions, purity, determinism, and generation boundary.
2. Add `application.yml.j2` with only the six required placeholder-backed settings.
3. Add `generate_project_config_sources()` in `renderer.py` using the existing `_ENVIRONMENT` and `GeneratedSources` contract.
4. Run the focused Spring generator tests and the existing suite segments that cover table, enum, inheritance, and shared-error generation.

## Risks

| Risk | Mitigation |
|------|------------|
| Future orchestrator forgets to call the singleton generator. | Keep orchestration explicitly out of scope and document this entry point as a project-singleton API. |
| Placeholder defaults sneak in for local convenience. | Tests reject colon-default placeholder syntax and known deployable literals. |
| Dialect/platform setting gets reintroduced from exploration notes. | Tests explicitly reject dialect/platform keys; accepted delta requires omission. |
| Table generation boundary weakens. | Tests assert `generate_table_sources` emits no resources path and no `application.yml`. |
| Static template later grows unrelated config. | Exclusion tests reject unsupported scopes such as OpenAPI, logging, Docker, and Java configuration. |
