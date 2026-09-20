# Delta for Generated Project Verification

## MODIFIED Purpose

Defines how the in-memory Gradle project returned by `generate_project_sources` is materialized to disk and proven to compile with `gradle build --no-daemon` AND to boot against a throwaway Postgres, serve one CRUD round-trip and serve its OpenAPI document. Covers the source writer, the sample model, the CLI, the runner-image tag, the compose chain, the boot smoke and the manual gate evidence. A green gate proves compilation, packaging, Spring context startup, JDBC wiring, the `ddl-auto` schema for the sample model, one CRUD round-trip and that `GET /v3/api-docs` serves an OpenAPI document listing `/api/customers`; Flyway/`schema.sql`, actuator, Gradle wrapper, Swagger UI, static OpenAPI export, Postman, Domain Manifest and operationId/tag tuning remain out of scope.

(Previously: "... and one CRUD round-trip; Flyway/`schema.sql`, actuator, Gradle wrapper and OpenAPI remain out of scope.")

## ADDED Requirements

### Requirement: OpenAPI Document Served

After readiness, the smoke MUST `GET /v3/api-docs` and expect status 200, and the response body MUST contain both `openapi` and `/api/customers`, checked in pure bash (no `jq`). A non-200 status MUST exit with the smoke's existing HTTP-mismatch exit code (6), and a 200 body missing either fragment MUST exit with the new document-content exit code (7); both messages MUST name the step. **[manual]**

#### Scenario: Document served

- GIVEN a ready app built with the springdoc starter
- WHEN the smoke requests `/v3/api-docs`
- THEN the status is 200, the body contains `openapi` and `/api/customers`, and the gate exit code is 0

#### Scenario: Negative check fails the gate

- GIVEN the assertion temporarily changed to require a bogus path fragment
- WHEN the gate runs
- THEN the smoke exits non-zero (7), the run is recorded, and the assertion is reverted afterwards

#### Scenario: Document endpoint broken

- GIVEN `/v3/api-docs` returns a non-200 status
- WHEN the smoke checks it
- THEN it exits non-zero naming the step and the gate fails

## MODIFIED Requirements

### Requirement: Boot Change Isolation

The change MUST NOT alter default `up`/`exec`/`pytest` behavior. The generated sources MUST NOT gain actuator, Flyway, a Swagger UI starter, `application.yml` keys or Java configuration classes. `SPRINGDOC_VERSION` MUST be the only new version constant and MUST live only in `emit/versions.py`, not in `generation_runner`, compose or scripts. **[pytest]** for sources and literals; **[manual]** for compose.

(Previously: MUST NOT add a version literal to `versions.py` or `generation_runner`, and MUST NOT change generated sources at all.)

#### Scenario: Only the springdoc line is added to the sources

- GIVEN the sample model before and after the springdoc change
- WHEN `generate_project_sources` runs
- THEN the only difference is the springdoc dependency line in `build.gradle`
- AND no actuator, Flyway, Swagger UI, `application.yml` or Java config output appears

#### Scenario: No version literal outside versions.py

- GIVEN `generation_runner`, compose and scripts
- WHEN scanned for `3.1.1`
- THEN no match is found

### Requirement: Generated Contract Pin

A Docker-free test MUST assert: the sample project exposes `/api/customers`; `CustomerRequestDto` has `fullName`; `CustomerResponseDto` has `id`; `application.yml` references the six env names; and the sample `build.gradle` contains the `org.springdoc:springdoc-openapi-starter-webmvc-api` coordinate. The `/v3/api-docs` literal inside `scripts/boot-smoke.sh` cannot be pinned from pytest, because the test process cannot reach `scripts/` (DD101, DD106); it is proven only by the recorded manual gate and its negative check. **[pytest]**

(Previously: only the first four assertions.)

#### Scenario: Contract drift caught

- GIVEN a generator change renaming `fullName`
- WHEN `pytest -q` runs
- THEN the contract test fails offline

#### Scenario: OpenAPI pin drift caught

- GIVEN the springdoc coordinate removed from the generated `build.gradle`
- WHEN `pytest -q` runs
- THEN the contract test fails offline

### Requirement: Fix-Forward Findings

A generator defect exposed by the first real boot MUST be recorded as a finding in the verify report. It MAY be fixed in this change only if small; otherwise it MUST become a follow-up change. This includes a springdoc 3.1.1 incompatibility with Boot 4.1.1 (for example an interaction with the generated `@RestControllerAdvice`). **[manual]**

(Previously: no springdoc example.)

#### Scenario: Defect found

- GIVEN the first boot fails on a generator defect
- WHEN the verify report is written
- THEN the defect is listed with its disposition (fixed or follow-up)

#### Scenario: springdoc incompatibility

- GIVEN `/v3/api-docs` fails on Boot 4.1.1 with springdoc 3.1.1
- WHEN the verify report is written
- THEN it records the finding; a small fix is applied in this change, otherwise work stops and a follow-up change is opened
