# Exploration: generated-project-compile-check

Spec section 37 item 13, slice 2 of 3. Slice 1 (`spring-boot-project-scaffold`, commit `48456ae`) made `generate_project_sources(model, *, base_package)` return the full 41-file Gradle project as text. This slice turns the manual slice-0 spike into an automated compile check. Full copy also in Engram `sdd/generated-project-compile-check/explore` (obs 676).

## Current infrastructure (from real files)

- `docker-compose.yml` is the only compose file: `db` (postgres:16-alpine), `redis`, `backend`, `mailpit`, `frontend`. One named volume (`postgres_data`). No `profiles:`, no Docker socket, no JVM.
- `backend` builds `./backend` (`target: dev`), bind-mounts only `./backend:/app`, uses `env_file: ./backend/.env`. `backend/Dockerfile` is `python:3.12-slim`, root user. `entrypoint.sh` waits for Postgres, migrates, seeds when `DEBUG`, then `exec "$@"`; a one-shot run needs `entrypoint: []`.
- `backend/pyproject.toml` pytest config: `DJANGO_SETTINGS_MODULE`, `python_files`, `testpaths = ["config","apps"]`. No markers, no addopts. Tests run with `docker compose exec -T backend pytest -q` (764).
- `settings.py` reads `POSTGRES_*` without defaults, so anything calling `django.setup()` needs `backend/.env`.
- No `.github/`, no `scripts/`, no Makefile. Root `.gitignore` has `build/`, `.env`, `.codegraph/` but not `.gradle/`.

## Where the writer belongs

- Apps are one per domain (standing user preference), each a registration shell plus subpackages (`domain/`, `emit/`, `mapping/`, `tests/`) and `test_apps.py`.
- Cross-app production imports already follow pipeline order (`renderer.py` imports `relational_mapping.domain`). Cross-app test imports are avoided.
- Recommendation: new app `apps/generation_runner`. The writer package must not import `spring_generator` (guard test scanning imports). Glue (CLI, sample-model builder) lives in the same app outside the writer package and may import `spring_generator` and `relational_mapping`. CLI is `python -m apps.generation_runner.cli`, with no `django.setup()`.

## GeneratedSources shape

`domain/sources.py`: frozen `GeneratedFile(path: str, contents: str)` and `GeneratedSources(files: tuple[GeneratedFile, ...])`, plus `as_mapping()` (collapses duplicates, must not be used by the writer) and `file_by_path()`. The generator only rejects duplicate paths (`GeneratedSourcePathCollisionError`); nothing rejects absolute paths, `..` or backslashes, so the writer owns that.

Writer contract: type the input with a `typing.Protocol` (`.files`, `.path`, `.contents`); validate everything before writing anything; reject empty, absolute (`/x`, `C:\x`, `C:/x`), `.`/`..`/empty segments, backslash, NUL, trailing slash, exact and case-insensitive duplicates, and any resolved path escaping `target_dir`; write UTF-8 with `newline="\n"`; refuse a non-empty target directory (stale `.java` could give a false green); raise typed errors; return the tuple of written paths.

## Ways to get a JVM without the Docker socket

| Option | Verdict |
|---|---|
| A. Compose-native chain: profile `jvm-verify`, one-shot `generate-project` service (backend image, `entrypoint: []`, no `env_file`) writes into named volume `generated_project`; `jvm-verify` service runs `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}` on the same volume with `depends_on: generate-project: condition: service_completed_successfully`, `gradle build --no-daemon`. Run: `docker compose --profile jvm-verify run --rm jvm-verify` (exit code propagates). | Recommended |
| B. Host script driving compose (can compute the tag from `versions.py`) | Only if D2(a) |
| C. Bind mount under `./backend` (OneDrive locks, slow `build/`) | Rejected |
| D. JDK + Gradle in the backend image | Rejected |
| E. Testcontainers / `docker run` from pytest (needs socket) | Rejected |
| F. `docker cp` choreography (the spike method) | Superseded by A |

Consequence: the compile gate is a compose/script command, not a pytest test. Pure parts (writer, image-tag function, sample builder, guard tests) stay in pytest, so the default suite stays fast and offline. A `jvm` pytest marker would be dead configuration (no pytest test can start Gradle).

Unverified gotchas to confirm at apply time: root-written volume files vs the non-root `gradle` user (likely `user: root` on the build service); `GRADLE_USER_HOME` location; Git Bash path mangling of `/generated/project` (keep paths in YAML or `MSYS_NO_PATHCONV=1`); `docker compose run` auto-starts `depends_on`.

## Network, cache, runtime

First run needs plugins.gradle.org, Maven Central and a Docker Hub pull. Spike: 42-49 s cold, `--no-daemon`, 41 files. Cache: none is simplest; a named `gradle_cache` volume adds permission/stale-state risk. Offline is not achievable in this slice (needs a pre-warmed image); follow-up related to spec section 35 item 18. Gate: `gradle build --no-daemon` (no tests, `test` is NO-SOURCE).

## Sample model and the inheritance bug

Runner app needs its own builder (no cross-app test imports). Use `CanonicalUmlModel` + `map_to_relational` (the real pipeline). Spike model: `Customer`; `Purchase` (Decimal, enum, DateTime, Boolean, Integer, Text, many-to-one Customer); `Vehicle`/`Car`/`Truck` (Single Table); `Product`/`Tag` (N:M join table). Known defect `emit/inheritance_context.py:169` (`pascal_case(class_id)` instead of `discriminator_values[class_id]`) fails on uuid class ids; the builder uses readable ids with a comment pointing at the queued fix, and should switch to `new_id()` once fixed. A default-suite test runs `generate_project_sources(build_sample_model())` and asserts success, determinism, `build.gradle` presence and file count.

## Spec impact

No delta on `spring-boot-generation` (the scaffold requirement already says a pinned Gradle runner version must come from one module; purity binds only the `generate_*` functions). New capability `generated-project-verification`: path validation, encoding/atomicity, writer decoupled from generator, runner image derived from `versions.py`, compile-gate exit-code contract, default suite Docker-free, no Docker socket in the app container. Strict TDD covers the Python half; the compose/Gradle half is verified by a manual gate run recorded in the verify report.

## Scope boundary

In: `write_sources` + tests, import-free guard test, sample builder, CLI + image-tag function, profile-gated compose chain, gate docs, new spec, `docs/ai/*`.
Out: boot smoke test and `gen-db` (slice 3), Gradle wrapper, `.gitignore`/Dockerfile emission, offline/pre-warmed cache, DDL emitter, reserved-word/name-collision sanitizing, CI, the `inheritance_context.py:169` fix, springdoc/OpenAPI.

## Risks

Root vs non-root ownership in the volume (unverified); single-sourcing the image tag (compose cannot import Python); stale volume causing a false green (writer refuses non-empty target, harness clears the subdirectory); network flakiness (gate is opt-in, never in `pytest -q`); Git Bash path mangling and OneDrive (state in named volumes); green build proves compile and packaging only, not boot/schema/reserved words/name collisions; case-insensitive duplicate paths; Strict TDD cannot cover the infrastructure half; a `GRADLE_VERSION` bump to a tag absent from Docker Hub fails loudly at pull time; change exceeds 400 lines (`size:exception` single-PR already accepted).

## Open decisions (pre-proposal gate)

| # | Decision | Options | Recommendation | Status |
|---|---|---|---|---|
| D1 | Entry point | compose-only / host script / both | compose-only unless D2 needs a script | pending user (follows D2) |
| D2 | Image tag source (compose cannot read `versions.py`) | (a) host script computes `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}` via a one-line backend run; (b) checked-in env file + in-container drift-guard test (restates the literal); (c) hardcode in compose (violates DD62 and the spec) | (a) | pending user |
| D3 | Gradle cache | none / named volume | none | default |
| D4 | `jvm` marker | skip / register + `addopts -m "not jvm"` | skip | default |
| D5 | Fixture vs inheritance bug | readable ids now / fix bug first / skip inheritance | readable ids now; fix bug before slice 3 | default |
| D6 | App name | `generation_runner` / `project_materialization` / `generated_project_verification` | `generation_runner` | default |
| D7 | Register as Django app | yes / no | yes | default |
| D8 | Script shell (if D2(a)) | Git Bash only / plus PowerShell | Git Bash only | default |
