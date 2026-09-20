# Delta for Generated Project Verification

Verification key: **[pytest]** = automated, Docker-free, offline; **[manual]** = recorded gate run.

## MODIFIED Purpose

Defines how the in-memory Gradle project returned by `generate_project_sources` is materialized to disk and proven to compile with `gradle build --no-daemon` AND to boot against a throwaway Postgres and serve one CRUD round-trip. Covers the source writer, the sample model, the CLI, the runner-image tag, the compose chain, the boot smoke and the manual gate evidence. A green gate proves compilation, packaging, Spring context startup, JDBC wiring, the `ddl-auto` schema for the sample model and one CRUD round-trip; Flyway/`schema.sql`, actuator, Gradle wrapper and OpenAPI remain out of scope.

(Previously: "boot, schema, reserved words and name collisions are out of scope".)

## ADDED Requirements

### Requirement: Single Gate Command

`bash scripts/verify-generated-project.sh` MUST be the only command needed. It MUST run the compile step, then the boot smoke, as two sequential `docker compose run` steps (not `depends_on: jvm-verify`), and MUST exit 0 only if both pass. **[manual]**

#### Scenario: Compile failure skips smoke

- GIVEN a generated project that fails to compile
- WHEN the script runs
- THEN it exits non-zero and the boot smoke step is never started

#### Scenario: Both steps pass

- GIVEN the sample model and a working Docker daemon
- WHEN the script runs
- THEN compile output is visible, then the smoke runs, and the exit code is 0

### Requirement: Throwaway Database Lifecycle

Compose MUST define `gen-db` under profile `jvm-verify` only: image `postgres:16-alpine`, no published ports, tmpfs data directory, a `pg_isready` healthcheck, and credentials from `${GEN_DB_*:-default}` (defaults live only in compose). The script MUST remove it with a `trap` running `docker compose rm -sfv gen-db` on pass, fail or interrupt, and MUST NOT run `down`. The existing `db` and `redis` services MUST be untouched. **[manual]**

#### Scenario: No leak after failure

- GIVEN a run whose smoke step fails
- WHEN the script exits
- THEN `docker compose ps -a` lists no `gen-db` container and `db`/`redis` are unchanged

#### Scenario: Default up unaffected

- GIVEN the compose file
- WHEN `docker compose up` runs without `--profile`
- THEN neither `gen-db` nor `jvm-boot-smoke` starts and no port is published

### Requirement: Boot Smoke Execution

Service `jvm-boot-smoke` (profile `jvm-verify`, no ports, waiting for a healthy `gen-db`) MUST run the non-plain bootJar with `java -jar` inside the same `GRADLE_IMAGE`. Compose MUST supply `SPRING_APPLICATION_NAME`, `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, `JPA_DDL_AUTO=create-drop` and `SERVER_PORT`. Container paths MUST appear only in compose, never in the scripts. **[manual]**

#### Scenario: Plain jar not used

- GIVEN `build/libs` holds a bootJar and a `-plain` jar
- WHEN the smoke starts
- THEN the process launched is the bootJar

### Requirement: Readiness Wait

The smoke MUST poll `GET /api/customers/count` with a bounded interval and a hard timeout, and MUST fail fast, with a clear message, if the JVM process exits before ready. **[manual]**

#### Scenario: JVM dies early

- GIVEN a jar that crashes at startup
- WHEN the smoke polls
- THEN it exits non-zero immediately, not after the full timeout

#### Scenario: Timeout

- GIVEN a JVM alive but never answering 200
- WHEN the timeout elapses
- THEN the smoke exits non-zero with a timeout message

### Requirement: CRUD Round-Trip

After readiness, the smoke MUST on `/api/customers` do POST `{"fullName":...}` expecting 201 with an `id`, GET by id 200, DELETE 204, GET again 404. Any other status MUST exit non-zero naming the step. **[manual]**

#### Scenario: Full round-trip

- GIVEN a ready app
- WHEN the four calls run in order
- THEN statuses are 201, 200, 204, 404 and the exit code is 0

#### Scenario: Status mismatch

- GIVEN any call returns an unexpected status
- WHEN it is checked
- THEN the smoke exits non-zero and the gate fails

### Requirement: Negative Case

A wrong `GEN_DB_PASSWORD` given to the app only MUST make the gate exit non-zero; the run MUST be recorded. **[manual]**

#### Scenario: Bad credential

- GIVEN `GEN_DB_PASSWORD` mismatching the database
- WHEN the gate runs
- THEN the exit code is non-zero and `gen-db` is removed

### Requirement: Boot Change Isolation

The change MUST NOT alter default `up`/`exec`/`pytest` behavior, MUST NOT add a version literal to `versions.py` or `generation_runner`, and MUST NOT change generated sources (no actuator, no Flyway). **[pytest]** for sources and literals; **[manual]** for compose.

#### Scenario: Sources unchanged

- GIVEN the sample model before and after this change
- WHEN `generate_project_sources` runs
- THEN the output is identical

### Requirement: Generated Contract Pin

A Docker-free test MUST assert: the sample project exposes `/api/customers`; `CustomerRequestDto` has `fullName`; `CustomerResponseDto` has `id`; `application.yml` references the six env names. **[pytest]**

#### Scenario: Contract drift caught

- GIVEN a generator change renaming `fullName`
- WHEN `pytest -q` runs
- THEN the contract test fails offline

### Requirement: Fix-Forward Findings

A generator defect exposed by the first real boot MUST be recorded as a finding in the verify report. It MAY be fixed in this change only if small; otherwise it MUST become a follow-up change. **[manual]**

#### Scenario: Defect found

- GIVEN the first boot fails on a generator defect
- WHEN the verify report is written
- THEN the defect is listed with its disposition (fixed or follow-up)

## MODIFIED Requirements

### Requirement: Image Tag Derivation

The runner image tag `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}` MUST be computed by a function reading only `emit/versions.py`. The host script MUST obtain it from that function and export `GRADLE_IMAGE`. No version literal MAY appear in compose, env files or the script, except a non-version sentinel default. Compose MUST consume it as `${GRADLE_IMAGE:-<sentinel>}`. **[pytest]** for the function; **[manual]** for script and compose.

(Previously: compose consumed `${GRADLE_IMAGE:?}` and aborted when unset; shipped compose uses the sentinel default.)

#### Scenario: Tag follows versions.py

- GIVEN `GRADLE_VERSION` and `JAVA_VERSION` values in `versions.py`
- WHEN the function is called
- THEN it returns `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}` exactly

#### Scenario: Unset image uses sentinel

- GIVEN `GRADLE_IMAGE` is unset
- WHEN compose resolves `jvm-verify`
- THEN it resolves to the sentinel default, no version literal is present, and the host script always exports the real tag **[manual]**

### Requirement: Manual Gate Evidence

The verify report MUST record the exact gate command, its exit code, the `BUILD SUCCESSFUL` line, the four round-trip statuses (201, 200, 204, 404) and the negative-case exit code, from runs over the sample project. **[manual]**

(Previously: only the command, exit code and `BUILD SUCCESSFUL`.)

#### Scenario: Evidence recorded

- GIVEN completed positive and negative gate runs
- WHEN the verify report is written
- THEN it contains the command, exit code 0, `BUILD SUCCESSFUL`, the four statuses and the non-zero negative exit code
