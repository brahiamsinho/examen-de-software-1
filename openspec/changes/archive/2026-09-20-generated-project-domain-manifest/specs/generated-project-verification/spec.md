# Delta for Generated Project Verification

## MODIFIED Purpose

Defines how the in-memory Gradle project returned by `generate_project_sources` is materialized to disk and proven to compile with `gradle build --no-daemon` AND to boot against a throwaway Postgres, serve one CRUD round-trip, serve its OpenAPI document, have that document exported and converted to a Postman collection, and have a Domain Manifest generated from the same model. Covers the source writer, the sample model, the CLI, the runner-image tag, the compose chain, the boot smoke, the Postman export step, the Domain Manifest step and the manual gate evidence. A green gate proves compilation, packaging, Spring context startup, JDBC wiring, the `ddl-auto` schema for the sample model, one CRUD round-trip, that `GET /v3/api-docs` serves an OpenAPI document listing `/api/customers`, that the captured document converts to a Postman collection, and that `docs/domain-manifest.json` is produced; Flyway/`schema.sql`, actuator, Gradle wrapper, Swagger UI, Domain Manifest metadata from section 33, auth and id-chained collections remain out of scope.

(Previously: the main spec Purpose ended "... one CRUD round-trip; Flyway/`schema.sql`, actuator, Gradle wrapper and OpenAPI remain out of scope", already stale after the springdoc and Postman changes, and did not mention the Domain Manifest.)

## MODIFIED Requirements

### Requirement: Compose Chain Contract

Compose MUST define profile `jvm-verify` with a one-shot `generate-project` service (backend image, `entrypoint: []`, no `env_file`) and a `jvm-verify` service running `gradle build --no-daemon`, both on named volume `generated_project`. It MUST also define a one-shot `generate-postman` service under the same profile with the same stanza as `generate-project` (backend image, `entrypoint: []`, no `env_file`, no database, volume `generated_project`) whose `command` is a literal array running `python -m apps.postman_export.cli` on the exported document. It MUST also define a one-shot `generate-manifest` service under the same profile with the same stanza (backend image, `entrypoint: []`, no `env_file`, no database, no `depends_on`, no `rm -rf`, mounts `./backend:/app:ro` and `generated_project:/generated`) whose `command` is a literal array running `python -m apps.domain_manifest.cli --out-dir` into the `docs` directory of the generated project. `jvm-verify` MUST depend on `generate-project` with `service_completed_successfully`, and the harness MUST clear the target subdirectory before generation. The gate exit code MUST propagate to the host script. No Docker socket MAY be mounted into the backend container, and no Gradle cache volume is defined. **[manual]**

(Previously: `generate-project`, `jvm-verify` and `generate-postman`; no `generate-manifest`.)

#### Scenario: Default up unaffected

- GIVEN the compose file with the new profile
- WHEN `docker compose up` runs without `--profile`
- THEN none of the `jvm-verify` services, including `generate-postman` and `generate-manifest`, starts

#### Scenario: Failure propagates

- GIVEN a generated project that fails to compile, or a failing `generate-project`
- WHEN the entry script runs the chain
- THEN the script exits non-zero and Gradle does not run after a failed generation

#### Scenario: Postman service shape

- GIVEN the compose file
- WHEN `generate-postman` is inspected
- THEN it is under profile `jvm-verify`, has no `env_file` and no DB dependency, and its command is a literal array

#### Scenario: Manifest service shape

- GIVEN the compose file
- WHEN `generate-manifest` is inspected
- THEN it is under profile `jvm-verify`, has no `env_file`, no `depends_on` and no `rm -rf`, mounts `./backend:/app:ro` and `generated_project:/generated`, and its command is a literal array

### Requirement: Manual Gate Evidence

The verify report MUST record the exact gate command, its exit code, the `BUILD SUCCESSFUL` line, the four round-trip statuses (201, 200, 204, 404), the negative-case exit code, the evidence that the static OpenAPI file was written by the smoke, the `generate-postman` result (exit 0 and the produced collection and environment file names), and the `generate-manifest` result (exit 0 and the produced `domain-manifest.json`), from runs over the sample project. It MUST also record one negative check proving that a failing manifest step fails the gate (its non-zero exit code). The change MUST also record the captured fixture provenance (springdoc 3.1.1 and capture date). **[manual]**

(Previously: no `generate-manifest` result and no manifest negative check.)

#### Scenario: Evidence recorded

- GIVEN completed positive and negative gate runs
- WHEN the verify report is written
- THEN it contains the command, exit code 0, `BUILD SUCCESSFUL`, the four statuses, the non-zero negative exit code, the export evidence, the `generate-postman` result and the `generate-manifest` result

#### Scenario: Manifest negative check recorded

- GIVEN the manifest step temporarily made to fail
- WHEN the gate runs and the change is reverted afterwards
- THEN the run is recorded with a non-zero exit code and the gate is shown to exit 0 again after the revert

### Requirement: Single Gate Command

`bash scripts/verify-generated-project.sh` MUST be the only command needed. It MUST run the compile step, then the boot smoke, then the `generate-postman` step, then the `generate-manifest` step, as four sequential `docker compose run` steps (not `depends_on: jvm-verify`), and MUST exit 0 only if all four pass. A springdoc document shape the converter cannot handle MUST fail the gate at the third step, and a failing manifest CLI (non-zero exit) MUST fail the gate at the fourth step. **[manual]**

(Previously: three steps, compile, boot smoke and `generate-postman`.)

#### Scenario: Compile failure skips later steps

- GIVEN a generated project that fails to compile
- WHEN the script runs
- THEN it exits non-zero and neither the boot smoke, the postman step nor the manifest step is started

#### Scenario: Smoke failure skips postman and manifest

- GIVEN a smoke that fails
- WHEN the script runs
- THEN it exits non-zero and neither the postman step nor the manifest step is started

#### Scenario: All four steps pass

- GIVEN the sample model and a working Docker daemon
- WHEN the script runs
- THEN compile output is visible, then the smoke runs, then the collection and environment files are produced from the exported document, then `docs/domain-manifest.json` is produced, and the exit code is 0

#### Scenario: Unhandled document shape

- GIVEN an exported document the converter rejects
- WHEN the third step runs
- THEN the converter exits 1, the gate exits non-zero and the manifest step is not started

#### Scenario: Manifest step failure

- GIVEN the manifest CLI exits non-zero
- WHEN the fourth step runs
- THEN the gate exits non-zero

### Requirement: Boot Change Isolation

The change MUST NOT alter default `up`/`exec`/`pytest` behavior. The generated sources MUST NOT change at all relative to the previous baseline (the 41-file sample oracle is unchanged), MUST NOT include the Domain Manifest, and MUST NOT gain actuator, Flyway, a Swagger UI starter, `application.yml` keys or Java configuration classes. No new version constant MUST be added anywhere; `SPRINGDOC_VERSION` remains the only springdoc constant and lives only in `emit/versions.py`, not in `generation_runner`, `postman_export`, `domain_manifest`, compose or scripts. No app other than `postman_export` MAY import it, and no app MAY import `domain_manifest`; `domain_manifest` MAY import only `spring_generator.emit.naming` (plus `generation_runner.samples.sample_model` in its CLI glue). **[pytest]** for sources and literals; **[manual]** for compose.

(Previously: sources unchanged and the new app `postman_export` isolated; no mention of `domain_manifest`, the Manifest exclusion from generated sources, or the 41-file oracle.)

#### Scenario: Generated sources unchanged

- GIVEN the sample model before and after this change
- WHEN `generate_project_sources` runs
- THEN the outputs are identical, still 41 files, and none is a manifest file

#### Scenario: No version literal outside versions.py

Proof: **[manual]** for `domain_manifest`, compose and scripts (a recorded `rg 3.1.1` scan found no match; the automated scan covers `postman_export` only). **[pytest]** for `postman_export`.

- GIVEN `generation_runner`, `postman_export`, `domain_manifest`, compose and scripts
- WHEN scanned for `3.1.1`
- THEN no match is found (the fixture provenance note is documentation, not source)

#### Scenario: Default behavior unaffected

- GIVEN the change applied
- WHEN `docker compose up` and `pytest -q` run with defaults
- THEN neither requires the new service, Docker, network or a JVM

#### Scenario: One-way import boundary

- GIVEN every app module
- WHEN a guard test scans imports
- THEN no app imports `domain_manifest` and `domain_manifest` imports only the allowed naming module
