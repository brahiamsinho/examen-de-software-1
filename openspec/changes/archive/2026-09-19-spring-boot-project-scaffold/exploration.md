# Exploration: generated-backend-compile-verification (§37 item 13)

Umbrella exploration for all of item 13. This folder is named after its first
slice, `spring-boot-project-scaffold`; slices 2 and 3 get their own changes later.

The explorer had no Docker, JVM or generator access, so the sections below are
reasoned from source and from official pages fetched on 2026-09-19. The
"Slice 0 spike results" section at the end replaces the main predictions with
observed facts.

## Slice 0 spike results (observed 2026-09-19, throwaway containers, nothing committed)

Setup: a sample model mapped with `map_to_relational` and rendered with
`generate_model_sources` (41 files), plus a hand-written `build.gradle`,
`settings.gradle` and `Application.java`, built in `gradle:9.7.1-jdk21` and booted
against `postgres:16-alpine`. Model: `Customer`; `Purchase` (Decimal, enum, DateTime,
Boolean, Integer, Text, many-to-one `Customer`); `Vehicle`/`Car`/`Truck`
(Single Table); `Product`/`Tag` (N:M join table).

- The image tag `gradle:9.7.1-jdk21` exists on Docker Hub.
- `gradle build --no-daemon` -> BUILD SUCCESSFUL in 49 s (Boot 4.1.1, Java 21).
  Predictions 2-5 held: with `spring-boot-starter-validation` included, the generated
  `jakarta.validation`, `Page`/`Pageable` and `ProblemDetail` code all compile.
- The working `build.gradle` uses only the `java` and `org.springframework.boot`
  4.1.1 plugins plus `implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)`
  (no `io.spring.dependency-management` needed), `mavenCentral()`, Java toolchain 21,
  starters `spring-boot-starter-webmvc`, `-data-jpa`, `-validation` and runtime
  `org.postgresql:postgresql`. No wrapper, no springdoc.
- Boot: `java -jar` started in 3.8 s (Hibernate 7.4.5, Tomcat 11.0.24), found the 6
  expected JPA repositories, connected to Postgres 16. Only WARN:
  `spring.jpa.open-in-view` (prediction 9).
- Smoke chain against the running app: `GET /customers/count` 200 (`0`), `POST` 201,
  `GET` by id 200, `GET ?page=0&size=2` 200 with `content`/`totalElements`, `PUT` 200,
  `DELETE` 204, `GET` after delete 404 with a `ProblemDetail` body, invalid `POST` 400
  with an `errors` map; the FK is a flat `customerId` and the enum round-trips.
  `Page<T>` serialized without a failure (the response body is a full `PageImpl`
  JSON); whether Spring Data logged its "Serializing PageImpl instances as-is" WARN was
  NOT checked, because the log was read before the requests were made (prediction 8).
- Schema Hibernate created with `JPA_DDL_AUTO=create-drop`: `purchase.status` is
  `varchar(255)` plus a CHECK constraint (NOT the native PG ENUM, as predicted);
  `vehicle.class_type` is `varchar(31)` (prediction 11 held; discriminator values are
  the verbatim class names); subclass columns are nullable and root columns NOT NULL.
- Cosmetic: `total` serializes as `10.5` on POST and `10.5000` on GET (numeric(19,4)).
- Predictions 6 (simple-name collisions), 7 (unquoted SQL reserved words), 8 and 10
  were NOT exercised: the fixture deliberately avoids them.

**New defect found (not in the predictions), in the archived inheritance cycle:**
`emit/inheritance_context.py:169` names each subclass entity with
`pascal_case(class_id)` (the UML element id), not the class name. Real ids are uuid4 hex
or UUIDs, and 10 of 16 start with a digit, so `generate_model_sources` raised
`InvalidJavaIdentifierError` on a model whose class ids came from `new_id()`. Every
inheritance test passes readable ids (`"vehicle"`, `"car"`, `"truck"`), which is why
the suite never caught it. The class name is available as `discriminator_values[class_id]`
(the verbatim UML class name). The spike worked around it by giving those three classes
readable ids. This needs its own small change (it also contradicts the archived
inheritance spec text) and is independent of the scaffold.

### Oracle files (verbatim, these three built and booted in the spike)

`build.gradle`:

```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '4.1.1'
}

group = 'com.modelia.generated'
version = '0.0.1-SNAPSHOT'

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)
    implementation 'org.springframework.boot:spring-boot-starter-webmvc'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    runtimeOnly 'org.postgresql:postgresql'
}
```

`settings.gradle`:

```groovy
rootProject.name = 'generated-backend'
```

`src/main/java/com/modelia/generated/Application.java`:

```java
package com.modelia.generated;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

## Current State

- `generate_model_sources(RelationalModel, *, base_package)` (renderer.py) returns an
  in-memory `GeneratedSources`: table sources, enums, shared errors, then
  `src/main/resources/application.yml`. Every path is under
  `src/main/java/<pkg>/{domain,persistence,application,application/dto,api,errors}/`
  or is `application.yml`.
- **Absent:** `build.gradle(.kts)`, `settings.gradle`, Gradle wrapper, a
  `@SpringBootApplication` class, a Dockerfile. Nothing can compile today.
- Spec constraints (`openspec/specs/spring-boot-generation/spec.md`):
  - "Package and File Path Layout": Java only under the six layer directories;
    `validation/` and Java `config/` forbidden.
  - "Existing Generator Contracts Are Preserved": the whole-model aggregate MUST NOT
    add a Docker or Gradle artifact, so the scaffold needs a new entry point.
  - "Whole-Model Determinism and Purity": no filesystem, env, subprocess, Gradle or
    Docker inside the generator. A writer/runner is a separate concern.
- Infrastructure: compose has `db` (postgres:16-alpine, Modelia's own schema), `redis`,
  `backend` (python:3.12-slim, no JVM, no Docker socket), `mailpit`, `frontend`.
  `pyproject.toml` has no markers or `addopts`. No `.github/` (no CI). Source is
  bind-mounted from a OneDrive path.
- Mapper facts: every table (join tables included) has a synthetic UUID `id` PK;
  Single Table hierarchies use `class_type` VARCHAR(255); inheritance tables get
  entities plus the root repository only (no HTTP surface); names are `snake_case`
  and unquoted in `@Table`/`@Column`.

## Q1. What a compilable Gradle project needs

| Need | Present | Placement |
|---|---|---|
| `build.gradle` (Boot plugin, Java 21, starters, postgres driver) | No | project root, new scaffold generator |
| `settings.gradle` | No | project root |
| `@SpringBootApplication` class | No | root base package `src/main/java/<pkg>/Application.java` |
| Gradle wrapper | No | the jar is binary and `GeneratedFile.contents` is `str`: cannot be emitted; defer |
| `.gitignore` | No | optional |
| Dockerfile | No | out of scope (the runner has its own image) |

The main class must sit in the root base package (`@SpringBootApplication` scans its own
package downward). Putting it in `config/` is wrong: `config/` is forbidden and a class
in `<pkg>.config` would not scan `domain`/`api`. It needs a spec delta: the root-package
application class is the single allowed Java file outside the layers; `config/` and
`validation/` stay forbidden.

Proposed entry points (pure, deterministic, Jinja + `.format()`, LibCST guard applies):
- `generate_project_scaffold_sources(*, base_package)` -> `build.gradle`, `settings.gradle`,
  `Application.java`, optionally `.gitignore`.
- `generate_project_sources(model, *, base_package)` composes `generate_model_sources`
  plus the scaffold and reuses the duplicate-path check. `generate_model_sources` stays
  byte-identical.
- Pin `SPRING_BOOT_VERSION` and `JAVA_VERSION` in one module (`emit/versions.py`).

Defaults (unverified): Groovy DSL, `group = base_package`,
`rootProject.name = "generated-backend"`, `version = "0.0.1-SNAPSHOT"`, Java toolchain 21,
main class `Application`, only `mavenCentral()` (a corporate mirror belongs in a Gradle
init script outside the project).

## Q2. Dependency and version reality

| Item | Finding | Source |
|---|---|---|
| Spring Boot | 4.1.1 stable; 4.2.0-M1 is a milestone | spring.io/projects/spring-boot |
| Java | Boot 4.1.1 supports Java 17 to 26, so 21 is fine | docs.spring.io/spring-boot/system-requirements.html |
| Gradle | 8.14+ or 9.x; latest 9.7.1, last 8.x is 8.14.5 | gradle.org/releases |
| Plugin | `id 'org.springframework.boot' version '4.1.1'` | docs.spring.io/spring-boot/gradle-plugin/getting-started.html |
| `-parameters` | added by Boot's Gradle plugin; the generated `@PathVariable UUID id` needs it | docs.spring.io/spring-boot/gradle-plugin/reacting.html |
| Starters (Boot 4 renamed them) | `spring-boot-starter-webmvc` (not `starter-web`), `-data-jpa`, `-validation`, runtime `org.postgresql:postgresql` | start.spring.io output + Boot 4.0 Migration Guide |
| Stack | Hibernate 7.x, Jakarta Persistence 3.2, Jakarta Validation 3.1, Jackson 3 (`tools.jackson`) | Boot 4.0/4.1 release notes |
| springdoc | `springdoc-openapi-starter-webmvc-ui` 3.1.1 is the Boot 4 line; Boot 4.1 + Jackson 3 compatibility NOT confirmed | springdoc.org |
| Runner image | `gradle:<version>-jdk<N>`; the exact tag `gradle:9.7.1-jdk21` was not confirmed on Docker Hub | docs.gradle.org/current/userguide/docker.html |

Recommendations: pin Boot 4.1.1 and Gradle 9.7.1 (fallback 8.14.5); exclude springdoc this
cycle (OpenAPI is out of scope, compatibility unproven); use the start.spring.io Gradle
project as the oracle for the plugin/BOM wiring.

Predicted compile or boot failures (from reading code, not running it):

| # | Prediction | Cause | Likelihood |
|---|---|---|---|
| 1 | Nothing compiles | no build file, no main class | certain |
| 2 | `jakarta.validation` missing | Entity/RequestDto/Controller import it; data-jpa does not bring it | certain if the starter is omitted |
| 3 | `GenerationType.UUID`, `@Enumerated`, `@Inheritance`, `@JoinColumn` fine | Jakarta Persistence 3.2 is a superset | low |
| 4 | `ProblemDetail`, `@RestControllerAdvice`, `Page`/`Pageable` imports | same packages in Spring 7 / Data 4 as far as known | low, unverified |
| 5 | Jackson 3 | templates import no Jackson types | low |
| 6 | Simple-name import collisions (a UML class named `Service`, `Page`, `Valid`, `Entity`, `Table`, `Column`, `Id`) | `naming._validate` only guards Java reserved words | medium for such names |
| 7 | Boot failure on SQL reserved words (`order`, `user`): unquoted `@Table(name=...)` | already accepted debt | high for such names |
| 8 | `Page<T>` serialization WARN unless `spring.data.web.pageable.serialization-mode=via_dto` | Controller returns `Page<...>` | warn only |
| 9 | `open-in-view` WARN | Boot default | harmless |
| 10 | Deleting a parent with children -> unhandled FK violation 500 | `CASCADE` not expressed in JPA | semantic gap, follow-up |
| 11 | Discriminator default length 31 | `@DiscriminatorColumn` has no length | edge |

## Q3. Boot-time correctness beyond compilation

- Enums: `@Enumerated(EnumType.STRING)` yields varchar(255) plus a check constraint under
  Hibernate DDL, not the native PG ENUM in the RelationalModel. Native needs
  `@JdbcTypeCode(SqlTypes.NAMED_ENUM)`. Irrelevant while Hibernate creates the schema.
- `JPA_DDL_AUTO`: no DDL emitter exists, so `validate`/`none` would fail or leave an empty
  DB. Use `create-drop` against a throwaway database, supplied by the runner.
- A DDL emitter and schema-equivalence with the RelationalModel are out of scope; this
  cycle proves mapping validity and boot only.
- Single Table inheritance: a successful boot proves the hierarchy mapping; there is no
  HTTP surface for it.
- All six config env vars are required with no defaults; a missing one fails startup.

## Q4. Where the verification runner lives

| Approach | Pros | Cons | Effort |
|---|---|---|---|
| **(a) compose profile + host-driven script** (recommended) | no Docker socket in the app container; fits the compose stack; steps are debuggable; named volume avoids OneDrive | needs a host script; not runnable from `pytest` alone | medium |
| (b) Testcontainers / `docker run` from tests | one `pytest` command | mounts the Docker socket (root-equivalent), new dependency, OneDrive/Windows path quirks | high + a security decision |
| (c) compile-only first, boot second | fast feedback | a phasing, not an architecture | low |
| (d) static Java lint in Python | no JVM | does not prove compile/boot | low |

Recommended: (a) phased as (c). Writer = separate app (`apps/generation_runner/`,
`write_sources(GeneratedSources, target_dir)`, rejects absolute paths and `..`, LF,
idempotent). Named volumes `generated_projects` and `gradle_cache`. JVM service in a
`jvm-verify` compose profile (`gradle:<ver>-jdk21`, no published ports). Dedicated
throwaway `gen-db` (postgres:16-alpine, tmpfs), not a database on Modelia's `db`. The
app receives the six env vars from the compose profile. A smoke pytest in `backend`
targets `GENERATED_APP_BASE_URL` and never touches Docker; a `jvm` marker plus env gate
keeps it out of the default `pytest -q` (685 tests stay fast). First run needs Maven
Central and plugins.gradle.org; offline verification needs a pre-warmed Gradle cache
(deferred). Time estimates (not measured): cold 2-5 min, warm compile 30-60 s, boot 10-25 s.

## Q5. Definition of done

- Compile gate: `gradle build --no-daemon` exits 0 (compileJava, processResources, bootJar
  exists) and the written file set equals `generate_project_sources(...)`.
- Boot gate: the app starts against a fresh `gen-db` with the six env vars and
  `JPA_DDL_AUTO=create-drop`; the port answers in time.
- Smoke gate: `GET /api/<plural>/count` returns 200 with `0` for every resource, plus one
  CRUD chain (POST parent 201, POST child with `parentId` and enum 201, GET by id 200,
  `GET ?page=0&size=2` 200, PUT 200, DELETE 204 then GET 404 `ProblemDetail`, invalid
  POST 400).
- Fixture (through `map_to_relational` + the full generator; avoid SQL reserved words and
  simple-name collisions): `Customer`; `Purchase` (Decimal, enum `PurchaseStatus`,
  DateTime, Boolean, Integer, Text; many-to-one `Customer`); `Vehicle` with `Car` and
  `Truck`; `Product` and `Tag` (N:M join table). The runner app needs its own fixture
  builder (no cross-app `tests` imports).

## Q6. Scoping

| Slice | Content | Infra |
|---|---|---|
| 0 (spike, not an SDD change) | write generator output for a small model plus a hand-written start.spring.io-style `build.gradle`, run `gradle build` in a `gradle:jdk21` container | Docker only |
| **1 `spring-boot-project-scaffold`** (propose first) | pure `generate_project_scaffold_sources` + `generate_project_sources`, `emit/versions.py`, spec delta | none |
| 2 `generated-project-compile-check` | writer app, `jvm-verify` profile, host script, `jvm` marker | JVM image, volumes, Maven Central |
| 3 `generated-project-boot-smoke` | `gen-db`, boot, smoke client, fixture | adds Postgres |
| Later | pre-warmed offline image, DDL emitter/schema equivalence, sanitizing colliding names and reserved words, production runner | separate cycles |

## Affected Areas (slice 1)

`spring_generator/emit/renderer.py` (two new public functions), `emit/templates/`
(`build.gradle.j2`, `settings.gradle.j2`, `Application.java.j2`, optional `gitignore.j2`),
`emit/versions.py` (new), `openspec/specs/spring-boot-generation/spec.md` (Project
Scaffold requirement; modified layout and preserved-contracts requirements), new tests
(determinism, purity, no-concat, no hardcoded URL/host/port), `docs/ai/*`.
Slices 2-3: new `apps/generation_runner/`, `docker-compose.yml`, `pyproject.toml`
markers, a host script, smoke tests, the fixture builder.

## Risks

- Every compile/boot claim is a prediction; slice 0 is the only way to confirm.
- Boot 4.x moves fast; springdoc 3.1.1 + Boot 4.1 unproven; pin and re-verify on bumps.
- No Gradle wrapper (binary) in generated projects.
- Simple-name and SQL-reserved-word collisions will hit real user models.
- Mounting the Docker socket into the app container is a root-equivalent risk; avoid.
- With `create-drop`, green means mapping + boot, not schema equivalence.
- OneDrive: keep generated output and Gradle state in named volumes.
- The first run needs internet.

## Open Questions

Real decisions for the user: (1) Maven Central/plugin portal access at verification time,
and whether offline is a hard requirement now; (2) host-driven compose profile
acceptable, no Docker socket in this cycle; (3) which slice first (recommended: slice 1,
preceded by the manual spike); (4) ship a Gradle wrapper or require system Gradle;
(5) springdoc-openapi now or in the OpenAPI cycle.

Defaults: Groovy DSL, `group = base_package`, `rootProject.name = "generated-backend"`,
Java 21, main class `Application`; Boot 4.1.1 and Gradle 9.7.1 (tag to confirm); dedicated
`gen-db`; `JPA_DDL_AUTO=create-drop`; opt-in `jvm` marker + env gate; the fixture above;
`generate_model_sources` untouched.

## Ready for Proposal

Yes for slice 1 (`spring-boot-project-scaffold`); questions 1-2 must be answered before
proposing slices 2-3.

## Sources

spring.io/projects/spring-boot; docs.spring.io/spring-boot/system-requirements.html;
docs.spring.io/spring-boot/gradle-plugin/getting-started.html and /reacting.html;
github.com/spring-projects/spring-boot/wiki (4.0 Migration Guide, 4.0 and 4.1 Release
Notes); repo1.maven.org spring-boot-starter-webmvc and springdoc metadata; start.spring.io
(bootVersion=4.1.1, Java 21, web,data-jpa,validation,postgresql); gradle.org/releases;
docs.gradle.org/current/userguide/docker.html; springdoc.org; Spring Data
`EnableSpringDataWebSupport.PageSerializationMode`; thorben-janssen.com/hibernate-enum-mappings;
vladmihalcea.com best way to map an enum with JPA and Hibernate.
