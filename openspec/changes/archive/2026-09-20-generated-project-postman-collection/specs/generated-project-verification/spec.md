# Delta for Generated Project Verification

## MODIFIED Purpose

Defines how the in-memory Gradle project returned by `generate_project_sources` is materialized to disk and proven to compile with `gradle build --no-daemon` AND to boot against a throwaway Postgres, serve one CRUD round-trip, serve its OpenAPI document, and have that document exported and converted to a Postman collection. Covers the source writer, the sample model, the CLI, the runner-image tag, the compose chain, the boot smoke, the Postman export step and the manual gate evidence. A green gate proves compilation, packaging, Spring context startup, JDBC wiring, the `ddl-auto` schema for the sample model, one CRUD round-trip, that `GET /v3/api-docs` serves an OpenAPI document listing `/api/customers`, and that the captured document converts to a Postman collection; Flyway/`schema.sql`, actuator, Gradle wrapper, Swagger UI, Domain Manifest, auth and id-chained collections remain out of scope.

(Previously: "... static OpenAPI export, Postman, Domain Manifest and operationId/tag tuning remain out of scope.")

## MODIFIED Requirements

### Requirement: Boot Smoke Execution

Service `jvm-boot-smoke` (profile `jvm-verify`, no ports, waiting for a healthy `gen-db`) MUST run the non-plain bootJar with `java -jar` inside the same `GRADLE_IMAGE`. Compose MUST supply `SPRING_APPLICATION_NAME`, `SPRING_DATASOURCE_URL`, `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, `JPA_DDL_AUTO=create-drop` and `SERVER_PORT`. Container paths MUST appear only in compose, never in the scripts. After the `/v3/api-docs` status and needle checks pass and before the PASS message, the smoke MUST copy the already-fetched response body (no new HTTP call) to a static file at a path relative to its working directory, creating the parent directory first; a failed copy MUST exit with the new export exit code 8 and a message naming the step. Existing exit codes 0, 2, 3, 4, 5, 6 and 7 MUST be unchanged. **[manual]**

(Previously: no export; the smoke ended with the needle checks and PASS.)

#### Scenario: Plain jar not used

- GIVEN `build/libs` holds a bootJar and a `-plain` jar
- WHEN the smoke starts
- THEN the process launched is the bootJar

#### Scenario: Document exported

- GIVEN a ready app whose `/v3/api-docs` checks passed
- WHEN the smoke reaches the export step
- THEN the fetched body exists as a static file at the relative path and the gate exit code is 0

#### Scenario: Export failure

- GIVEN the export path cannot be written
- WHEN the smoke copies the body
- THEN it exits 8 naming the step and PASS is not logged

#### Scenario: Export ordering

- GIVEN the smoke script
- WHEN a contract check inspects it
- THEN the export follows the needle checks, precedes PASS, and issues no HTTP call between the last check and the copy

### Requirement: Compose Chain Contract

Compose MUST define profile `jvm-verify` with a one-shot `generate-project` service (backend image, `entrypoint: []`, no `env_file`) and a `jvm-verify` service running `gradle build --no-daemon`, both on named volume `generated_project`. It MUST also define a one-shot `generate-postman` service under the same profile with the same stanza as `generate-project` (backend image, `entrypoint: []`, no `env_file`, no database, volume `generated_project`) whose `command` is a literal array running `python -m apps.postman_export.cli` on the exported document. `jvm-verify` MUST depend on `generate-project` with `service_completed_successfully`, and the harness MUST clear the target subdirectory before generation. The gate exit code MUST propagate to the host script. No Docker socket MAY be mounted into the backend container, and no Gradle cache volume is defined. **[manual]**

(Previously: only `generate-project` and `jvm-verify`; no `generate-postman`.)

#### Scenario: Default up unaffected

- GIVEN the compose file with the new profile
- WHEN `docker compose up` runs without `--profile`
- THEN none of the `jvm-verify` services, including `generate-postman`, starts

#### Scenario: Failure propagates

- GIVEN a generated project that fails to compile, or a failing `generate-project`
- WHEN the entry script runs the chain
- THEN the script exits non-zero and Gradle does not run after a failed generation

#### Scenario: Postman service shape

- GIVEN the compose file
- WHEN `generate-postman` is inspected
- THEN it is under profile `jvm-verify`, has no `env_file` and no DB dependency, and its command is a literal array

### Requirement: Single Gate Command

`bash scripts/verify-generated-project.sh` MUST be the only command needed. It MUST run the compile step, then the boot smoke, then the `generate-postman` step, as three sequential `docker compose run` steps (not `depends_on: jvm-verify`), and MUST exit 0 only if all three pass. A springdoc document shape the converter cannot handle MUST fail the gate at the third step. **[manual]**

(Previously: two steps, compile then boot smoke.)

#### Scenario: Compile failure skips smoke

- GIVEN a generated project that fails to compile
- WHEN the script runs
- THEN it exits non-zero and neither the boot smoke nor the postman step is started

#### Scenario: Smoke failure skips postman

- GIVEN a smoke that fails
- WHEN the script runs
- THEN it exits non-zero and the postman step is never started

#### Scenario: All three steps pass

- GIVEN the sample model and a working Docker daemon
- WHEN the script runs
- THEN compile output is visible, then the smoke runs, then the collection and environment files are produced from the exported document, and the exit code is 0

#### Scenario: Unhandled document shape

- GIVEN an exported document the converter rejects
- WHEN the third step runs
- THEN the converter exits 1 and the gate exits non-zero

### Requirement: Manual Gate Evidence

The verify report MUST record the exact gate command, its exit code, the `BUILD SUCCESSFUL` line, the four round-trip statuses (201, 200, 204, 404), the negative-case exit code, the evidence that the static OpenAPI file was written by the smoke, and the `generate-postman` result (exit 0 and the produced collection and environment file names), from runs over the sample project. The change MUST also record the captured fixture provenance (springdoc 3.1.1 and capture date). **[manual]**

(Previously: command, exit code, `BUILD SUCCESSFUL`, the four statuses and the negative-case exit code.)

#### Scenario: Evidence recorded

- GIVEN completed positive and negative gate runs
- WHEN the verify report is written
- THEN it contains the command, exit code 0, `BUILD SUCCESSFUL`, the four statuses, the non-zero negative exit code, the export evidence and the `generate-postman` result

### Requirement: Boot Change Isolation

The change MUST NOT alter default `up`/`exec`/`pytest` behavior. The generated sources MUST NOT change at all relative to the previous baseline, and MUST NOT gain actuator, Flyway, a Swagger UI starter, `application.yml` keys or Java configuration classes. No new version constant MUST be added anywhere; `SPRINGDOC_VERSION` remains the only springdoc constant and lives only in `emit/versions.py`, not in `generation_runner`, `postman_export`, compose or scripts. No app other than `postman_export` MAY import it. **[pytest]** for sources and literals; **[manual]** for compose.

(Previously: allowed only the springdoc dependency line as a source difference and referred to the springdoc change; now the sources must be unchanged and the new app must stay isolated.)

#### Scenario: Generated sources unchanged

- GIVEN the sample model before and after this change
- WHEN `generate_project_sources` runs
- THEN the outputs are identical

#### Scenario: No version literal outside versions.py

- GIVEN `generation_runner`, `postman_export`, compose and scripts
- WHEN scanned for `3.1.1`
- THEN no match is found (the fixture provenance note is documentation, not source)

#### Scenario: Default behavior unaffected

- GIVEN the change applied
- WHEN `docker compose up` and `pytest -q` run with defaults
- THEN neither requires the new service, Docker, network or a JVM
