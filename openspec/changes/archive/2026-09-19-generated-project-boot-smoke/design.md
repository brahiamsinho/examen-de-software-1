# Design: Generated Project Boot Smoke

Slice 3 of 3 (spec §37 item 13). Inputs: `proposal.md`, `exploration.md`. Decisions continue the project sequence from **DD92** (last used: DD91, `spring-generator-inheritance-subclass-naming`; the runner/gate decisions are DD75–DD86).

## Technical Approach

The compile gate (DD82/DD83) already leaves a built project in the `generated_project` volume. This slice adds a JVM run and one HTTP round-trip against a throwaway Postgres, without touching the generator. Two new profile-gated services (`gen-db`, `jvm-boot-smoke`) join the same `jvm-verify` profile; `scripts/verify-generated-project.sh` gains a second sequential `run` step and a cleanup trap. All runtime logic lives in `scripts/boot-smoke.sh`, executed **inside** the Gradle image from a read-only mount, so the host needs no JDK, no curl and no ports. The Python half adds exactly one Docker-free contract test that pins the literals the script hardcodes about the generated app.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD92 | Two services under the **existing** `jvm-verify` profile: `gen-db` (postgres:16-alpine) and `jvm-boot-smoke` (`${GRADLE_IMAGE:-<sentinel>}`), both without published ports; the JVM curls `127.0.0.1` inside its own container. | A new `jvm-smoke` profile; publishing 8080 to the host; a host-side `java -jar`. | A second profile would double the flag on every command for zero isolation gain — both services are already inert under plain `up`. No published port means no host port conflict and no reachable surface; loopback inside one container is the smallest possible exposure. Reusing `${GRADLE_IMAGE:-…}` (same sentinel form as `jvm-verify`, DD82) keeps one `export` in the script covering both services and preserves the "whole-file interpolation" fix. |
| DD93 | Credentials and DB name from `${GEN_DB_NAME\|USER\|PASSWORD:-…}` with throwaway defaults, consumed **only** by compose (never `backend/.env`, never committed in a file); `JPA_DDL_AUTO: create-drop`; Postgres data on `tmpfs`. | Literal credentials in compose; reusing `POSTGRES_*` from the app stack; a persistent named volume; `ddl-auto: update`. | Defaults make the gate runnable on a fresh clone with one command, while the `${…:-}` form still allows the negative case (`GEN_DB_PASSWORD=wrong …`) with no file edit. Reusing `POSTGRES_*` would couple the gate to the developer's real stack and let a smoke run point at the dev database. `tmpfs` guarantees each run starts schemaless, so `create-drop` is proving the *generated* DDL, not a leftover schema. |
| DD94 | The script runs **two sequential** `docker compose … run --rm` steps (`jvm-verify`, then `jvm-boot-smoke`). `jvm-boot-smoke` does **not** declare `depends_on: jvm-verify`. | `depends_on: jvm-verify: service_completed_successfully`; one combined service. | `run` attaches only to the named service, so a compile failure inside a dependency prints little and surfaces as a start error rather than Gradle's own output. Two steps keep `BUILD FAILED` on screen and make `set -e` the propagation mechanism — the same shape DD83's fallback anticipated. |
| DD95 | Cleanup is an `EXIT` trap running `docker compose --profile jvm-verify rm -sfv gen-db \|\| true` — compose's service-scoped `rm`, never `docker compose down`. | `down`; `docker rm -f gen-db` with a `container_name`; no cleanup. | `run` never stops its dependencies, so `gen-db` outlives both the pass and the fail path. `down` would stop the developer's `db`/`redis`/`backend` — unacceptable. `rm -sfv` names one **service literal**, so it can only ever touch this project's `gen-db` and its anonymous volumes; a `container_name` would additionally make two checkouts collide. An `EXIT` trap does not overwrite `$?`, so the gate's exit code survives cleanup. |
| DD96 | `scripts/boot-smoke.sh` is mounted read-only (`./scripts:/scripts:ro`) and invoked as `command: ["bash", "/scripts/boot-smoke.sh"]`, with `working_dir: /generated/project` and `user: root`. | Baking the script into a new image; `command: ["/scripts/boot-smoke.sh"]`; `sh -c`. | Naming the interpreter removes any dependence on the executable bit, which Git on Windows does not reliably carry. `:ro` means a rogue JVM cannot rewrite the harness. `root` matches DD83 (the generated tree is root-owned). A dedicated image would add a build to a gate whose whole point is to need nothing new. |
| DD97 | Jar selection: glob `build/libs/*.jar`, skip `*-plain.jar`, require exactly one survivor. **No version literal anywhere in the script.** | `generated-backend-0.0.1-SNAPSHOT.jar`; `ls \| head -1`; `find … -newest`. | DD62 keeps versions in `emit/versions.py` alone; a literal here would silently break on the next bump and reintroduce exactly the drift that constant exists to prevent. "Exactly one" turns a stale or duplicated artifact into a loud failure instead of booting the wrong jar. |
| DD98 | Start the JVM in the background, then poll `GET /api/customers/count` until 2xx, failing fast on `kill -0 "$APP_PID"` and hard-stopping at a deadline (`SMOKE_READY_TIMEOUT`, default 180s). The dying JVM is reaped by the same `EXIT` trap. | `sleep 60` then assert; `curl --retry`; an actuator health probe. | `/count` is the strongest readiness signal available without actuator (out of scope): it proves the context started, the datasource connected **and** `ddl-auto` created the table. `kill -0` turns the whole class of context-startup failures — including the negative case — into a ~10s failure instead of a full-timeout wait, and distinguishes "app died" from "app slow". A fixed sleep is both flakier and slower. |
| DD99 | One `_http` seam: every network call goes through a single function; `assert_status <expected> <method> <path> [json]` compares and dumps the body + app log on mismatch. Typed exit codes (below). | Inline `curl` at each step; `curl --fail` only. | Isolating curl in one function makes the "curl absent" fallback a one-function swap instead of a rewrite. Distinct exit codes let the verify report state *which* stage failed without parsing prose. |
| DD100 | The created id is extracted in **pure bash** (strip spaces, split on `"id":"`), then validated against `^[0-9a-fA-F-]{36}$` before it is interpolated into any URL. curl is always called with an argument list — no `eval`, no `sh -c`. | `jq`; `sed`/`grep`; using the response body unchecked. | `jq` is not in the Gradle image and installing it needs network at run time. Jackson emits `{"id":"…"}` with no spaces; normalising whitespace first makes the parse robust without a dependency. The shape check is the injection boundary: the only value flowing from an HTTP response into a command is proven to be a UUID's character set first. |
| DD101 | The **only** pytest addition is `tests/test_boot_smoke_contract.py`, asserting on `generate_project_sources(build_sample_relational_model())`. The compose/bash half is proven by the recorded gate run (DD85 precedent). | A pytest shelling out to `docker compose`; a test parsing `docker-compose.yml`/`boot-smoke.sh`. | Tests run with `/app` = `backend/`, so `docker-compose.yml` and `scripts/` are **not reachable from the test process** — a coupling test is impossible here, not merely undesirable. The test therefore pins the generated-side literals and carries a comment naming `scripts/boot-smoke.sh`; the script↔generator agreement is proven end-to-end by the gate, which is the strongest evidence available. |
| DD102 | The negative case is one extra manual invocation, `GEN_DB_PASSWORD=wrong bash scripts/verify-generated-project.sh`, recorded in `gate-evidence.md` with its exit code and the failing stage. | A permanent second compose service; skipping the negative case. | It exercises DD98's `kill -0` path and proves the gate can actually fail — a gate never observed red is not evidence. One env prefix needs no file, no service and no code. |

## Compose (exact keys, DD92/DD93/DD96)

```yaml
  gen-db:
    image: postgres:16-alpine
    profiles: [jvm-verify]
    environment:
      POSTGRES_DB: ${GEN_DB_NAME:-gensmoke}
      POSTGRES_USER: ${GEN_DB_USER:-gensmoke}
      POSTGRES_PASSWORD: ${GEN_DB_PASSWORD:-gensmoke}
    tmpfs:
      - /var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 3s
      timeout: 3s
      retries: 20

  jvm-boot-smoke:
    image: ${GRADLE_IMAGE:-gradle.invalid/unset:GRADLE_IMAGE-not-set-run-scripts-verify-generated-project.sh}
    profiles: [jvm-verify]
    user: root
    working_dir: /generated/project
    volumes:
      - generated_project:/generated
      - ./scripts:/scripts:ro
    environment:
      SPRING_APPLICATION_NAME: generated-backend-smoke
      SPRING_DATASOURCE_URL: jdbc:postgresql://gen-db:5432/${GEN_DB_NAME:-gensmoke}
      SPRING_DATASOURCE_USERNAME: ${GEN_DB_USER:-gensmoke}
      SPRING_DATASOURCE_PASSWORD: ${GEN_DB_PASSWORD:-gensmoke}
      JPA_DDL_AUTO: create-drop
      SERVER_PORT: "8080"
    depends_on:
      gen-db:
        condition: service_healthy
    command: ["bash", "/scripts/boot-smoke.sh"]
```

The six `environment` keys are exactly the six names `application.yml` interpolates with no default (pytest-enforced by the existing scaffold tests, re-pinned by DD101).

## `scripts/boot-smoke.sh` (DD96–DD100)

```
set -euo pipefail
BASE_URL=${SMOKE_BASE_URL:-http://127.0.0.1:${SERVER_PORT:-8080}}
1. resolve jar   : for f in build/libs/*.jar; skip *-plain.jar; exactly one → $JAR   (else exit 3)
2. launch        : java -jar "$JAR" >/tmp/boot-smoke-app.log 2>&1 &  APP_PID=$!
                   trap cleanup EXIT INT TERM   # kill -0 → kill → wait; dump log tail if $? != 0
3. readiness     : until _http GET /api/customers/count is 2xx
                     ! kill -0 $APP_PID          → exit 4    (JVM died: the negative case lands here)
                     now >= start+TIMEOUT        → exit 5
                     sleep 2
4. POST   /api/customers  {"fullName":"boot-smoke"}  → assert 201
5. id            := pure-bash parse of "id":"…" ; must match ^[0-9a-fA-F-]{36}$   (else exit 6)
6. GET    /api/customers/$id                          → assert 200
7. DELETE /api/customers/$id                          → assert 204
8. GET    /api/customers/$id                          → assert 404
9. echo "boot-smoke: PASS" ; exit 0
```

`until _http …; do` keeps the failing probe out of `set -e`'s reach. `_http` is the single curl call site (DD99): `curl -sS -o "$BODY" -w '%{http_code}' -X "$METHOD" [-H 'Content-Type: application/json' -d "$JSON"] "$BASE_URL$PATH"`, with the status captured by a separate assignment so `set -e` still sees curl's own exit status.

**Body contract, verified against the templates**: `CustomerRequestDto` is built by `build_request_dto_context`, which drops the PK column and names every field `camel_case(column.name)` → the single field is `fullName`; `RequestDto.java.j2` emits a no-arg constructor plus getters/setters, so Jackson binds `{"fullName":"boot-smoke"}`. `CustomerResponseDto` keeps the PK → `id`. `Controller.java.j2` + `build_controller_context` give `@RequestMapping("/api/customers")` with `POST ""`→`CREATED`, `GET "/{id}"`, `DELETE "/{id}"`→`NO_CONTENT`, `GET "/count"`. The 404 comes from `GlobalExceptionHandler`.

| Exit | Meaning |
|---|---|
| 0 | Round-trip passed |
| 2 | `/generated/project/build/libs` missing (compile step not run) |
| 3 | Zero or more than one boot jar |
| 4 | JVM exited before readiness (context startup failure — e.g. wrong password) |
| 5 | Readiness deadline exceeded |
| 6 | HTTP status mismatch, or id absent/malformed |

## `scripts/verify-generated-project.sh` changes (DD94/DD95)

Unchanged: `set -euo pipefail`, `export MSYS_NO_PATHCONV=1`, `cd` to repo root, the `GRADLE_IMAGE` bootstrap resolution, the empty-tag guard, `export GRADLE_IMAGE` (now consumed by **both** JVM services). Added:

```bash
cleanup() { docker compose --profile jvm-verify rm -sfv gen-db >/dev/null 2>&1 || true; }
trap cleanup EXIT
…
docker compose --profile jvm-verify run --rm jvm-verify        # step 1: compile (unchanged)
docker compose --profile jvm-verify run --rm jvm-boot-smoke    # step 2: boot smoke
```

## Data Flow

    verify-generated-project.sh (host, Git Bash)   trap EXIT → compose rm -sfv gen-db
       │ export GRADLE_IMAGE (from emit/versions.py, DD80)
       ├─ run --rm jvm-verify ──→ generate-project (completed_successfully) ──→ gradle build
       │                                              volume generated_project:/generated
       └─ run --rm jvm-boot-smoke
             depends_on gen-db: service_healthy (pg_isready, tmpfs data)
             bash /scripts/boot-smoke.sh   (/scripts:ro)
                java -jar build/libs/<boot>.jar  &
                   └─ JDBC → gen-db:5432, ddl-auto=create-drop → schema
                loopback HTTP: /count → POST 201 → GET 200 → DELETE 204 → GET 404
             exit code ──→ compose ──→ script exit code

## File Changes

| File | Action | ~Lines | Description |
|---|---|---|---|
| `scripts/boot-smoke.sh` | Create | 110 | DD96–DD100 |
| `scripts/verify-generated-project.sh` | Modify | +8 | DD94 second step, DD95 trap |
| `docker-compose.yml` | Modify | +38 | DD92/DD93 two services |
| `backend/apps/generation_runner/tests/test_boot_smoke_contract.py` | Create | 95 | DD101 |
| `openspec/changes/.../specs/generated-project-verification/spec.md` | Create | 120 | Delta: boot in scope; `${GRADLE_IMAGE:-…}` drift fix |
| `openspec/changes/.../gate-evidence.md` | Create | 45 | DD102 evidence |
| `docs/ai/{CURRENT_STATE,HANDOFF_LATEST,NEXT_STEPS,DECISIONS_LOG}.md` + session note | Modify | 70 | DD92–DD102 |

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit (pytest, offline) | `test_boot_smoke_contract.py`: controller carries `@RequestMapping("/api/customers")`, `@GetMapping("/count")`, `POST ""`+`HttpStatus.CREATED`, `GET/DELETE "/{id}"`+`NO_CONTENT`; `CustomerRequestDto` declares `fullName` and **no** `id`; `CustomerResponseDto` declares `id`; `application.yml` interpolates exactly the six env names | Call `generate_project_sources(build_sample_relational_model(), base_package=…)` in-process and assert on `sources.files` contents — no Docker, no network, RED first |
| Gate (manual, DD85/DD101) | Compile + boot + CRUD round-trip; cleanup; negative case | `bash scripts/verify-generated-project.sh` → exit 0; `GEN_DB_PASSWORD=wrong bash scripts/verify-generated-project.sh` → non-zero (expected stage: exit 4); `docker ps -a` after both shows no `gen-db` |

**What is proven by what (honest split).** pytest proves that every literal `boot-smoke.sh` hardcodes *about the generated application* — URL path, request key, response key, status codes, env-var names — matches what the generator emits today, and it will go red the day the generator drifts. pytest proves **nothing** about compose wiring, the JDBC URL, jar selection, curl availability, the JVM actually booting, Hibernate DDL succeeding, real HTTP responses, or the cleanup trap: the test process cannot even read `docker-compose.yml` or `scripts/` (DD101). Those are proven **only** by the recorded gate run in `gate-evidence.md`, which must state: date, exact command, resolved `GRADLE_IMAGE`, each observed status code, the final script exit code, the negative run's exit code and stage, and `docker ps -a` output showing no surviving `gen-db`.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED test |
|---|---|---|---|
| Documentation-like paths | **N/A** — nothing classifies repo files by name/extension | — | — |
| Git repository selection / commit / push / PR | **N/A** — no VCS or PR automation | — | — |
| Destructive shell in the harness | **Applicable** — cleanup removes a container | DD95: `docker compose --profile jvm-verify rm -sfv gen-db`, a **literal service name**, never interpolated, never `down`, never `docker volume rm`; DD83's `rm -rf /generated/project` is unchanged | Gate evidence: `db`/`redis`/`backend` still running after a failing gate run |
| Shell argument composition | **Applicable** — Git Bash path mangling; container paths | `MSYS_NO_PATHCONV=1` retained; no container path passed inline (all in compose); `set -euo pipefail` in both scripts; jar path quoted | Gate evidence: script prints the resolved `GRADLE_IMAGE` and the selected jar before launching |
| Response data reaching a command | **Applicable** — the created id is interpolated into request URLs | DD100: pure-bash parse + `^[0-9a-fA-F-]{36}$` shape check before use; curl invoked with an argument list, never `eval`/`sh -c` | Gate evidence (the check is in-container); exit 6 on a malformed id |
| Secrets in process arguments / logs | **Applicable** — a DB password exists | DD93: password travels as a compose `environment` value, never in argv; the failure dump prints the **app log only**, not the environment; credentials are throwaway and the store is `tmpfs` | Gate evidence: failure dump inspected once for credential leakage |
| Network exposure | **Applicable** — an HTTP server starts | DD92: no `ports:` on either service; the server is reached over container loopback only | Gate evidence: `docker compose ps` shows no published port |

## To Confirm at Apply

| Item | Verification step | Fallback |
|---|---|---|
| `curl` exists in `GRADLE_IMAGE` | `docker compose --profile jvm-verify run --rm --no-deps jvm-boot-smoke bash -c 'curl --version'` **before** writing the round-trip | Swap the single `_http` function (DD99): first try `wget -S -O-`; if also absent, a bash `/dev/tcp/127.0.0.1/8080` HTTP/1.1 request reading the status line — zero new dependencies, no image mutation, no network at run time |
| Postgres `initdb` accepts a `tmpfs` data dir | Step 2 log must show `database system is ready`, not a permissions error | Add `PGDATA: /var/lib/postgresql/data/pgdata` so `initdb` creates a subdirectory it owns |
| `create-drop` schema survives until the round-trip | `/count` returns 200 rather than a missing-relation 500 | None needed — a failure here is a real generator finding, recorded per the proposal's risk row |
| `docker compose rm` accepts a profiled service | Run the gate, then `docker ps -a` | Add `--profile jvm-verify` (already planned) or fall back to `docker rm -sf "$(docker compose ps -aq gen-db)"` |
| Readiness budget on a cold JVM + first `ddl-auto` | Observe the ready time in the gate log | Raise `SMOKE_READY_TIMEOUT` (env knob, no code change) |

## Migration / Rollout

No migration. Purely additive: both new services are inert without `--profile jvm-verify`, the new test is Docker-free and offline, and `docker compose up` / `pytest -q` are unchanged. Rollback per the proposal (revert the commit); no volume cleanup is needed because `gen-db` stores nothing on disk.

## Open Questions

- [ ] None blocking. Every unknown is in **To Confirm at Apply** with a concrete check and a concrete fallback.
