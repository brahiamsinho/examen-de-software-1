# Tasks: Generated Project Boot Smoke

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~620 (script 110, test 95, compose 38, verify +8, evidence 45, docs 70, delta spec 120, tasks/other) |
| 400-line budget risk | High (project budget 800; ~620 fits) |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

Note: `size:exception` must be accepted before apply (already accepted per orchestrator context).

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Contract pin test | PR 1 | `docker compose exec -T backend pytest -q apps/generation_runner/tests/test_boot_smoke_contract.py` | N/A (offline) | delete the test file |
| 2 | Compose + scripts + gate evidence | PR 1 | N/A (not pytest-reachable, DD101) | `bash scripts/verify-generated-project.sh` (exit 0) and `GEN_DB_PASSWORD=wrong bash ...` (non-zero) | revert compose/scripts; no volumes to clean |
| 3 | docs/ai refresh | PR 1 | N/A (docs) | structural readback | docs files only |

## Phase 1: Contract test (Strict TDD, DD101)

- [x] 1.1 Create `backend/apps/generation_runner/tests/test_boot_smoke_contract.py`: asserts on `generate_project_sources(build_sample_relational_model())` files: `@RequestMapping("/api/customers")`, `@GetMapping("/count")`, `POST ""`+`CREATED`, `GET/DELETE "/{id}"`+`NO_CONTENT`; `CustomerRequestDto` has `fullName`, no `id`; `CustomerResponseDto` has `id`; `application.yml` has exactly the six env names. Comment names the boot-smoke script. Spec: Generated Contract Pin.
- [x] 1.2 Run it: `docker compose exec -T backend pytest -q apps/generation_runner/tests/test_boot_smoke_contract.py`. HONEST STATUS: this is characterization, not RED-first, because it pins existing generator output and passes immediately. Prove it can fail: temporarily rename `fullName` in the assertion, observe red, revert. Spec: Contract drift caught, Sources unchanged.

## Phase 2: Apply-time probe (before any round-trip code)

- [x] 2.1 Probe with plain Docker (no compose service needed): `docker run --rm --entrypoint bash "$GRADLE_IMAGE" -c 'curl --version'`, image tag from the script's resolution. Record result for gate-evidence. Fallback (DD99): swap only `_http` to `wget -S -O-`, else bash `/dev/tcp` HTTP/1.1. Decision recorded before 4.1. Spec: To Confirm at Apply.

## Phase 3: Compose (DD92, DD93, DD96)

- [x] 3.1 Add `gen-db` to `docker-compose.yml` (postgres:16-alpine, profile `jvm-verify`, `GEN_DB_*` defaults, tmpfs, `pg_isready` healthcheck, no ports). Spec: Throwaway Database Lifecycle.
- [x] 3.2 Add `jvm-boot-smoke` to `docker-compose.yml` (`${GRADLE_IMAGE:-sentinel}`, root, six env keys, `/scripts:ro`, `depends_on gen-db: service_healthy`, `bash /scripts/boot-smoke.sh`, no ports). Spec: Boot Smoke Execution.
- [x] 3.3 Check `docker compose config` and plain `docker compose config --services` unchanged for `db`/`redis`/`backend`. Spec: Default up unaffected.
- [x] 3.4 If the probe (2.1) or first run shows `initdb` tmpfs permission errors, add `PGDATA` subdir (design fallback). Not needed: tmpfs initdb worked without PGDATA.

## Phase 4: Scripts (DD94, DD95, DD97-DD100)

- [x] 4.1 Create `scripts/boot-smoke.sh`: `set -euo pipefail`, jar glob skipping `-plain` (exit 2/3), background `java -jar`, readiness poll with `kill -0` (exit 4) and `SMOKE_READY_TIMEOUT` (exit 5). Spec: Plain jar not used, Readiness Wait.
- [x] 4.2 In `scripts/boot-smoke.sh`: single `_http` seam, `assert_status`, POST 201, pure-bash id parse + `^[0-9a-fA-F-]{36}$` check (exit 6), GET 200, DELETE 204, GET 404, `PASS` line. Spec: CRUD Round-Trip, Status mismatch.
- [x] 4.3 Modify `scripts/verify-generated-project.sh`: `cleanup` EXIT trap (`rm -sfv gen-db`, never `down`) plus second `run --rm jvm-boot-smoke` step after compile. Spec: Single Gate Command, No leak after failure.

## Phase 5: Manual gate (DD85, DD102)

- [x] 5.1 Run `bash scripts/verify-generated-project.sh`; create `openspec/changes/generated-project-boot-smoke/gate-evidence.md`: date, command, resolved `GRADLE_IMAGE`, selected jar, `BUILD SUCCESSFUL`, statuses 201/200/204/404, ready time, exit 0, curl probe, `docker compose ps` (no published port). Spec: Manual Gate Evidence.
- [x] 5.2 Run `GEN_DB_PASSWORD=wrong bash scripts/verify-generated-project.sh`; record exit code, failing stage (expected 4), no credential in the dump. Spec: Bad credential.
- [x] 5.3 Record `docker ps -a` (no `gen-db` after both runs; `db`/`redis`/`backend` untouched) and default-up check. Spec: No leak, Default up unaffected.
- [x] 5.4 If the first real boot exposes a generator defect, record it as a finding in gate-evidence with disposition; fix forward only if small, else a follow-up change. Spec: Fix-Forward Findings. Two harness-design findings (F1, F2) fixed forward; no generator defect.

## Phase 6: Full regression

- [x] 6.1 Run `docker compose exec -T backend pytest -q` (whole backend); record the pass count. Spec: Boot Change Isolation.

## Phase 7: Docs (AGENTS.md rule)

- [x] 7.1 Update `docs/ai/CURRENT_STATE.md`, `docs/ai/HANDOFF_LATEST.md`, `docs/ai/NEXT_STEPS.md`.
- [x] 7.2 Append DD92-DD102 to `docs/ai/DECISIONS_LOG.md`.
- [x] 7.3 Create `docs/ai/sessions/2026-09-19-agent-generated-project-boot-smoke.md`.
