# Proposal: Generated Project Boot Smoke

## Intent

The gate proves the generated Spring project **compiles**, not that it **runs** — compilation cannot catch a broken JPA mapping, an unmappable DDL type, a reserved-word column, or a dead context. §37 item 13 (slice 3 of 3) closes that gap: boot the jar against a throwaway Postgres and do one real CRUD round-trip, so green means a *working* backend.

## Scope

### In Scope

- Extend `scripts/verify-generated-project.sh` into one gate: compile, then boot smoke (sequential `docker compose run` steps; trap `rm -sfv gen-db`, never `down`).
- New `scripts/boot-smoke.sh`: `java -jar` the non-plain bootJar inside `GRADLE_IMAGE`, wait on `GET /api/customers/count`, then POST 201 / GET 200 / DELETE 204 / GET 404.
- Compose, profile `jvm-verify` only: `gen-db` (postgres:16-alpine, `pg_isready`, tmpfs, no ports) and `jvm-boot-smoke` (no ports). Credentials via `${GEN_DB_*:-default}`, compose-only. `JPA_DDL_AUTO=create-drop`.
- Docker-free contract pytest in `backend/apps/generation_runner/tests/`.
- Spec delta fixing existing drift in `generated-project-verification`.

### Out of Scope

- Any generator/template change (fix-forward only if a defect found is small; else a follow-up change).
- Actuator, Flyway/schema.sql, Gradle wrapper, OpenAPI, published ports, CI wiring.
- Anything beyond boot + JDBC wiring + ddl-auto schema for the sample model + one CRUD round-trip.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `generated-project-verification`: the gate additionally proves boot and a CRUD round-trip; Purpose no longer excludes boot/schema; compose consumes `${GRADLE_IMAGE:-sentinel}` (matches shipped compose), not `${GRADLE_IMAGE:?}`.

## Approach

Reuse the existing chain. Compile step unchanged; a second `run` step starts `jvm-boot-smoke` with a healthy `gen-db`, mounting `generated_project` plus `./scripts:/scripts:ro`. Steps stay sequential (not `depends_on: jvm-verify`) so Gradle output stays visible and failure propagates by exit code.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `scripts/verify-generated-project.sh` | Modified | Chain boot smoke after compile; gen-db cleanup trap |
| `scripts/boot-smoke.sh` | New | Boot jar + curl CRUD round-trip |
| `docker-compose.yml` | Modified | `gen-db`, `jvm-boot-smoke` under `jvm-verify` |
| `backend/apps/generation_runner/tests/` | New | Docker-free contract test |
| `openspec/specs/generated-project-verification/spec.md` | Modified | Delta: boot in scope, drift fix |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| First real boot exposes a generator defect | High | Record as finding; fix-forward only if small, else follow-up change |
| `curl` absent from `GRADLE_IMAGE` | Low | Verify at apply; fall back to a JDK-only probe |
| Leaked `gen-db` container | Medium | `trap` with `rm -sfv gen-db` |
| Maven Central / cold-JVM flake | Medium | Bounded readiness polling with a clear timeout message |

## Rollback Plan

Revert the change commit. Compile gate, default `up` and `pytest -q` are untouched by construction: new services sit behind the `jvm-verify` profile, the new test is Docker-free.

## Dependencies

- Docker and network access for the manual gate run (image pull + Gradle resolution).

## Success Criteria

- [ ] One command runs compile + boot smoke and exits 0 on the sample model.
- [ ] Round-trip observed: POST 201, GET 200, DELETE 204, GET 404.
- [ ] Negative case recorded (wrong `GEN_DB_PASSWORD` → non-zero exit).
- [ ] No `gen-db` container survives a passing or failing run.
- [ ] `pytest -q` stays green, Docker-free and offline.
