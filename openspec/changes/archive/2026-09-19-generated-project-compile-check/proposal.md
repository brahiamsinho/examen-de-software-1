# Proposal: Generated Project Compile Check

Spec section 37 item 13, slice 2 of 3. Input: `exploration.md` in this folder.

## Intent

`generate_project_sources(model, *, base_package)` returns a 41-file Gradle project **as text**. Nothing proves that text compiles. The only evidence is a manual slice-0 spike. Every future generator slice therefore ships blind: a broken import, a bad identifier or a malformed `build.gradle` is invisible to `pytest -q`. This slice materializes those sources to disk and runs `gradle build --no-daemon` over them as a repeatable, opt-in gate.

## Scope

### In Scope

- `write_sources(sources, target_dir)` in new app `apps/generation_runner` — path re-validation, UTF-8 `newline="\n"`, refuses a non-empty target, typed errors, returns written paths.
- Guard test asserting the writer package imports nothing from `apps.spring_generator`.
- Sample-model builder (own app, `CanonicalUmlModel` + `map_to_relational`) and a default-suite test that generates from it.
- CLI `python -m apps.generation_runner.cli` plus an image-tag function derived from `emit/versions.py`.
- Profile-gated compose chain (`generate-project` one-shot → `jvm-verify`) over a named `generated_project` volume.
- Host bash entry script computing `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}` and driving compose.
- Gate documentation, new spec, `docs/ai/*` updates.

### Out of Scope

- Boot smoke test and `gen-db` (slice 3); Gradle wrapper; `.gitignore`/Dockerfile emission.
- Offline/pre-warmed Gradle cache; DDL emitter; reserved-word/name-collision sanitizing; CI wiring.
- The `emit/inheritance_context.py:169` fix (queued as its own change); springdoc/OpenAPI.

## Capabilities

### New Capabilities

- `generated-project-verification`: path validation and traversal refusal, encoding/atomicity, writer decoupled from the generator, runner image derived from `versions.py`, compile-gate exit-code contract, default suite Docker-free, no Docker socket in the app container.

### Modified Capabilities

- None. No delta on `spring-boot-generation` — the scaffold requirement already pins the runner version to one module, and purity binds only the `generate_*` functions.

## Approach

Exploration Approach 1 (Option A, compose-native chain) with the D2 script in front.

1. `emit/versions.py` stays the single source of truth. A host bash script (Git Bash only, D8) runs a one-line backend command to compute the image tag and exports it; compose consumes it as `${GRADLE_IMAGE:?}` so an unset value fails loudly. No literal is repeated in compose or an env file.
2. The script runs the profile-gated chain: one-shot `generate-project` (backend image, `entrypoint: []`, no `env_file`) clears and repopulates a subdirectory of the named `generated_project` volume via the CLI; `jvm-verify` runs `gradle build --no-daemon` on the same volume under `depends_on: service_completed_successfully`. The exit code propagates to the script.
3. No Docker socket is mounted into the backend container. The pure half (writer, image-tag function, sample builder, guard test) is ordinary pytest and stays fast and offline.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/generation_runner/` | New | App shell, `domain/`, writer package, `cli.py`, sample builder, `tests/` |
| `backend/config/settings.py` | Modified | Register app in `INSTALLED_APPS` (D7) |
| `docker-compose.yml` | Modified | `jvm-verify` profile, two services, `generated_project` volume |
| `scripts/` | New | Git Bash entry script computing the tag and driving compose |
| `openspec/specs/` (via change) | New | `generated-project-verification` spec |
| `docs/ai/*`, `.gitignore` | Modified | Gate docs, state/handoff/decisions, `.gradle/` ignore |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Root-written volume files vs non-root `gradle` user | High | `user: root` on the generate service (and on `jvm-verify` if needed); confirm `GRADLE_USER_HOME` at apply time |
| Stale volume → false green | Med | Writer refuses a non-empty target; harness clears the subdirectory before generating |
| Git Bash path mangling of `/generated/project` | Med | Keep container paths in YAML; `MSYS_NO_PATHCONV=1` on any inline path |
| Network dependence (Docker Hub, Maven Central, plugin portal) | Med | Gate is opt-in and never part of `pytest -q`; failure is a gate failure, not a suite failure |
| Strict TDD covers only the Python half | High | Compose/Gradle half verified by a manual gate run whose command and exit code are recorded in the verify report |
| `GRADLE_VERSION` bump to a tag absent from Docker Hub | Low | Fails loudly at pull time; tag derived from `versions.py`, never hand-edited |
| Green build proves compile/package only | Med | Documented explicitly; boot/schema coverage deferred to slice 3 |
| Case-insensitive duplicate paths on Windows volumes | Low | Writer rejects exact and case-insensitive duplicates before writing anything |

## Rollback Plan

Self-contained and additive. Revert the PR: delete `backend/apps/generation_runner/`, remove it from `INSTALLED_APPS`, drop the `jvm-verify` profile block, the two services and the `generated_project` volume from `docker-compose.yml`, delete the script and the new spec, then `docker volume rm` the orphaned volume. No existing module is modified in behavior, so `pytest -q` and `docker compose up` return to their current state with no migration or data impact.

## Dependencies

- Archived `spring-boot-project-scaffold` (`generate_project_sources`, `emit/versions.py`) — done.
- Docker Engine + Compose v2 on the host; Git Bash for the entry script (D8).
- Network access on first gate run (Docker Hub, plugins.gradle.org, Maven Central).
- Sample builder uses readable inheritance ids (D5) until `emit/inheritance_context.py:169` is fixed.

## Review Workload Forecast

| Bucket | Est. lines |
|---|---|
| Writer + domain + typed errors | ~130 |
| Writer/validation tests | ~210 |
| Sample builder + its test | ~200 |
| CLI + image-tag function + tests | ~120 |
| App shell, guard test, settings | ~70 |
| Compose + script | ~100 |
| Spec + docs | ~300 |
| **Total** | **~1130** |

- Decision needed before apply: No (`size:exception` already accepted)
- Chained PRs recommended: No (single PR, per accepted `size:exception`)
- 400-line budget risk: High

## Success Criteria

- [ ] `write_sources` rejects absolute paths, `..`/`.`/empty segments, backslash, NUL, trailing slash, exact and case-insensitive duplicates, and any path escaping `target_dir` — each with a typed error and no partial write.
- [ ] Writer writes UTF-8 with `newline="\n"` and refuses a non-empty target directory.
- [ ] Guard test proves the writer package imports nothing from `apps.spring_generator`.
- [ ] Default `pytest -q` stays Docker-free, offline and fast; no new markers.
- [ ] The image tag is computed from `emit/versions.py`; no literal version appears in compose, env files or the script.
- [ ] One documented command runs the gate end to end and propagates the Gradle exit code.
- [ ] A manual gate run produces `BUILD SUCCESSFUL` on the 41-file sample project, recorded with its command and exit code in the verify report.
- [ ] No Docker socket is mounted into the backend container.
