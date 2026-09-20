# Gate Evidence: Generated Project Compile Check

Recorded during apply (2026-09-19). Environment: Windows 11, Git Bash, Docker Desktop, Docker Compose v5.1.4. The gate is manual and compose-based (DD85); it is not part of `pytest`.

## 7.1 Positive gate run

- Command (repo root, Git Bash): `bash scripts/verify-generated-project.sh`
- Resolved `GRADLE_IMAGE`: `gradle:9.7.1-jdk21` (printed by the script as `verify-generated-project: GRADLE_IMAGE=[gradle:9.7.1-jdk21]`, derived from `emit/versions.py`)
- Final Gradle status line: `BUILD SUCCESSFUL in 47s` (run 1, cold; `5 actionable tasks: 5 executed`)
- Exit code: `0`
- A second consecutive run (target volume already populated, proving the harness `rm -rf` reset works): `BUILD SUCCESSFUL in 43s`, exit code `0`.

Output excerpt (run 1):

```
verify-generated-project: GRADLE_IMAGE=[gradle:9.7.1-jdk21]
 Container examen-1-software-generate-project-1 Started
 Container examen-1-software-generate-project-1 Waiting
 Container examen-1-software-generate-project-1 Exited
 Container examen-1-software-jvm-verify-run-9a72af9579d9 Created
> Task :compileJava
> Task :processResources
> Task :classes
> Task :resolveMainClassName
> Task :bootJar
> Task :jar
> Task :assemble
> Task :compileTestJava NO-SOURCE
> Task :processTestResources NO-SOURCE
> Task :testClasses UP-TO-DATE
> Task :test NO-SOURCE
> Task :check UP-TO-DATE
> Task :build

BUILD SUCCESSFUL in 47s
5 actionable tasks: 5 executed
```

Volume content after the run: 41 generated source files under `/generated/project` (excluding `build/` and `.gradle/`), matching the sample-model oracle.

## Phase 6 outcomes

| Item | Outcome |
|---|---|
| 6.1 `${GRADLE_IMAGE:?}` with `GRADLE_IMAGE` unset | BROKE ordinary commands: `docker compose config -q`, `docker compose exec -T backend true` and `docker compose ps -q` all exited 1 with `required variable GRADLE_IMAGE is missing a value`. Fallback applied: `image: ${GRADLE_IMAGE:-gradle.invalid/unset:GRADLE_IMAGE-not-set-run-scripts-verify-generated-project.sh}`. After the fallback `config -q` rc=0 and `exec -T backend true` rc=0 with the variable unset. |
| 6.2 clean tag capture | Confirmed: `od -c` of the raw stdout is exactly `gradle:9.7.1-jdk21\n`, with and without `-T`/`--no-deps`, no CR and no compose noise (build/log lines go to stderr). Fallback NOT required; the script keeps `--no-deps -T`, `tr -d '\r'` and `tail -n 1` as harmless defensive hardening. |
| 6.3 `service_completed_successfully` under `run --rm jvm-verify` | Confirmed: log shows `generate-project-1 Started`, `Waiting`, `Exited` before the Gradle banner; `docker inspect` reports `exited exit=0`. Fallback NOT required. |
| 6.4 `GRADLE_USER_HOME` as root | Confirmed: no `Could not create`, `permission` or `denied` line anywhere in either run. Fallback NOT required. |
| 6.5 stray containers | `docker compose ps -a` after a gate run lists one stopped `examen-1-software-generate-project-1 Exited (0)`; the `--rm` run containers are gone. The next gate run replaces it. No `down` added. Volume `examen-1-software_generated_project` persists by design. |
| Extra finding (deviation) | The backend `dev` image ships no source (the `backend` service bind-mounts `./backend:/app`). The first gate run failed with `ModuleNotFoundError: No module named 'apps'`. Fix: `generate-project` mounts `./backend:/app:ro` (read-only; the CLI writes only under `/generated`). |

## 7.2 Negative: `GRADLE_IMAGE` unset

Command: `env -u GRADLE_IMAGE docker compose --profile jvm-verify run --rm jvm-verify`. Exit code `1`. Excerpt:

```
 Image gradle.invalid/unset:GRADLE_IMAGE-not-set-run-scripts-verify-generated-project.sh Pulling
 Image gradle.invalid/unset:GRADLE_IMAGE-not-set-run-scripts-verify-generated-project.sh Error failed to resolve reference "gradle.invalid/unset:GRADLE_IMAGE-not-set-run-scripts-verify-generated-project.sh": ... lookup gradle.invalid: no such host
Error response from daemon: failed to resolve reference "gradle.invalid/unset:GRADLE_IMAGE-not-set-...": ... no such host
```

The failure names `GRADLE_IMAGE` (per the 6.1 fallback: pull failure, not interpolation failure). Note: because the pull happens after the dependency starts, `generate-project` did start and exit 0 (regenerating the volume) before the pull error; nothing dangerous runs.

## 7.3 Negative: non-empty target

Command: `docker compose --profile jvm-verify run --rm generate-project python -m apps.generation_runner.cli --target /generated/project`. Exit code `1`. stderr: `error: Target directory '/generated/project' is not empty; refusing to write over stale files`. Volume untouched (still 41 source files).

## 7.4 Profile isolation

`env -u GRADLE_IMAGE docker compose config --services` (no profile) lists `db redis backend frontend mailpit`; neither `generate-project` nor `jvm-verify`. With `--profile jvm-verify` both appear.

## Repository and Docker state after the gate

- `git status --short`: only `.gitignore`, `backend/config/settings.py`, `docker-compose.yml` modified; new `backend/apps/generation_runner/`, `scripts/`, `openspec/changes/generated-project-compile-check/`, and the pre-existing untracked `.pi/`. No `build/` or `.gradle/` in the repo (they live in the named volume).
- New Docker artifacts: named volume `examen-1-software_generated_project`, image `examen-1-software-generate-project` (dev build, layer-cached from the backend build), pulled image `gradle:9.7.1-jdk21`, stopped container `examen-1-software-generate-project-1`.
