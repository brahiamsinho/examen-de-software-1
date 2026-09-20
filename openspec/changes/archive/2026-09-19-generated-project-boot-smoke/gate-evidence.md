# Gate Evidence: Generated Project Boot Smoke

Manual gate (DD85, DD101, DD102). Host: Windows 11, Git Bash, Docker Desktop.
Local date 2026-09-19 (UTC timestamps below are 2026-09-20T02:3x).
Sample model, base package `com.modelia.generated`. No generator source was changed.

## Environment

| Item | Value |
|---|---|
| Resolved `GRADLE_IMAGE` | `gradle:9.7.1-jdk21` (from `emit/versions.py` via `gradle_runner_image()`) |
| Selected jar | `build/libs/generated-backend-0.0.1-SNAPSHOT.jar` (the `-plain` jar was skipped) |
| JDK in image | OpenJDK 21.0.12 |
| `curl` probe (task 2.1) | `docker run --rm --entrypoint bash gradle:9.7.1-jdk21 -c 'curl --version'` -> `curl 8.18.0` present; `wget` also present. No `_http` fallback needed (DD99). |

## Positive run (final compose + scripts)

Command: `bash scripts/verify-generated-project.sh` (started 2026-09-20T02:38:22Z)

| Check | Observed |
|---|---|
| Compile step | `BUILD SUCCESSFUL in 40s` (5 actionable tasks: 5 executed) |
| gen-db | started, `Healthy` before the smoke (tmpfs `initdb` accepted; no `PGDATA` fallback needed, task 3.4 not required) |
| Readiness | `boot-smoke: ready after 4s` (earlier runs: 4s, 5s, 5s) |
| `POST /api/customers` | 201 |
| `GET /api/customers/{id}` | 200 |
| `DELETE /api/customers/{id}` | 204 |
| `GET /api/customers/{id}` again | 404 |
| Final line | `boot-smoke: PASS` |
| Script exit code | **0** |

The positive gate was run green three times (02:32:28Z with the initial compose, 02:37Z after fix F1, 02:38:22Z after fix F2; the last one is the run tabulated above). No Maven Central flake occurred, so no rerun was needed for that reason.

## Negative run

Command: `GEN_DB_PASSWORD=wrong bash scripts/verify-generated-project.sh`

| Check | Observed |
|---|---|
| Compile step | `BUILD SUCCESSFUL` (compile does not touch the database) |
| Failing stage | smoke, `boot-smoke: FAIL: the JVM exited before becoming ready` |
| Script exit code | **4** (the JVM-died-before-ready path, DD98) |
| Root cause in the app log | `FATAL: password authentication failed for user "gensmoke"` |
| Credential leak | the failure dump contains no occurrence of the string `wrong` (checked with a count of 0); the dump shows the app log only, never the environment |

## Cleanup and isolation

| Check | Observed |
|---|---|
| `docker ps -a` after the positive run | no `gen-db` container; `db`, `redis`, `backend`, `frontend`, `mailpit` all `Up` and unchanged |
| `docker ps -a` after the negative run | no `gen-db` container (EXIT trap ran `rm -sfv gen-db`; `down` never used) |
| Pre-existing leftover | the stopped `generate-project-1` container (dependency of `jvm-verify`) remains after every gate run; this predates the change (compile-check gate) |
| Published ports | `docker compose --profile jvm-verify config`: only `backend`, `frontend`, `mailpit` declare `ports:`; `gen-db`, `jvm-boot-smoke`, `jvm-verify`, `generate-project` declare none |
| Default up unaffected | `docker compose config --services` -> `mailpit redis db backend frontend` (no `gen-db`, no `jvm-boot-smoke`); with the profile the three JVM/gate services appear |
| Full backend suite | 836 passed (see the apply-progress artifact) |

## Findings (task 5.4)

No generator defect was exposed: the first real boot of the sample project created its schema via `ddl-auto=create-drop` and served the full CRUD round-trip. Two defects were found in the **harness design** itself and fixed forward in this change (both small):

| # | Finding | Disposition |
|---|---|---|
| F1 | The design's compose used one variable, `GEN_DB_PASSWORD`, for both `gen-db` and the app. `GEN_DB_PASSWORD=wrong bash ...` therefore changed both sides consistently and the negative run **passed with exit 0** (observed at 02:35Z), so the gate could not fail on a bad credential. | Fixed: `gen-db` now reads `GEN_DB_SERVER_PASSWORD` (default `gensmoke`); the app keeps `GEN_DB_PASSWORD`. The negative run then exits 4. |
| F2 | A Spring stack trace pushed the root cause out of the 60-line failure tail, leaving the negative-run dump undiagnosable. | Fixed: the failure dump first lists `FATAL` / `Caused by` lines (last 5), then the tail. |

Both are compose/script changes, not pytest-reachable (DD101), so they are proven only by the runs above.
