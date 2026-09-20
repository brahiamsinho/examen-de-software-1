# Exploration: generated-project-boot-smoke

> Faithful copy of Engram observation `sdd/generated-project-boot-smoke/explore` (obs #691).
> The explore phase ran without the Write tool, so this file was persisted by the propose phase.

**What**: Exploration of §37 item 13 slice 3 (boot smoke of the generated Spring app against throwaway Postgres `gen-db`).

**Current state**: Generated project already has full CRUD: per table Entity (UUID @GeneratedValue), Repository, Request/ResponseDto, Service, RestController at /api/<kebab-plural-table> (POST 201, GET/{id}, PUT/{id}, DELETE/{id} 204, GET list, GET /count), GlobalExceptionHandler (404/400 ProblemDetail). build.gradle.j2: webmvc, data-jpa, validation, postgresql (runtimeOnly); NO actuator; no Flyway/schema.sql, only spring.jpa.hibernate.ddl-auto=${JPA_DDL_AUTO}. application.yml requires 6 env vars with no defaults (pytest-enforced): SPRING_APPLICATION_NAME, SPRING_DATASOURCE_URL/USERNAME/PASSWORD, JPA_DDL_AUTO, SERVER_PORT. rootProject.name=generated-backend; bootJar + plain jar both in build/libs. Sample Customer(fullName) -> /api/customers, request body {"fullName":...}, response has id.

**Recommendation**: No generator change. Smoke = wait on GET /api/customers/count (proves context+table), then POST 201 / GET 200 / DELETE 204 / GET 404. Run `java -jar` (non-plain bootJar) inside the same GRADLE_IMAGE (curl present in gradle jdk21-noble base) via new compose service jvm-boot-smoke (profile jvm-verify, mounts generated_project + ./scripts:/scripts:ro, runs scripts/boot-smoke.sh, no published ports) + gen-db (postgres:16-alpine, pg_isready healthcheck, tmpfs data, no ports). Script chains after compile gate; `docker compose run` does NOT stop deps so trap must `rm -sfv gen-db` (never `down`). Two sequential run steps (not depends_on jvm-verify) so Gradle logs stay visible. Only pytest addition: Docker-free contract test pinning /api/customers, fullName, id, env names; compose/bash half proven by manual gate run (DD85 precedent).

**Open decisions**: chain into existing verify script vs new script (rec: extend); throwaway creds literals vs ${GEN_DB_*:-default} (rec: env default); ddl-auto create-drop (rec); scope = Hibernate ddl-auto only, Flyway/actuator/wrapper/OpenAPI deferred.

**Risks**: Maven Central flake, first real boot may expose generator defects (Single Table DDL, enum, reserved words, Hibernate 7/Boot 4.1), cold JVM startup, leaked gen-db if script killed, spec drift (spec says ${GRADLE_IMAGE:?} but compose uses :-sentinel; Purpose says boot out of scope).

**Size**: ~620 lines total (~180 code+tests), fits 800 budget.

**Note**: all four open decisions above were resolved in the confirmed pre-proposal handoff; see `proposal.md`.
