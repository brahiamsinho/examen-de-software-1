# Tasks: Generated Project Compile Check

Slice 2 of 3 (spec section 37 item 13). Design decisions DD75-DD86. Test commands run only in Docker from the container workdir `/app` (= `backend/`): `docker compose exec -T backend pytest -q <path>`.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1130 (writer+domain ~130, tests ~380, sample builder ~150, CLI+image ~65, compose+script ~75, spec ~200, docs ~80, misc ~50) |
| 400-line budget risk | High |
| Chained PRs recommended | No (single PR under the already-accepted `size:exception`) |
| Suggested split | Single PR, 8 work units applied in order |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | App shell, errors, Protocols, import guard | PR 1 | `docker compose exec -T backend pytest -q apps/generation_runner/tests/test_apps.py apps/generation_runner/tests/test_writer_decoupling.py` | N/A: pure Python | `apps/generation_runner/` + 1 line in `settings.py` |
| 2 | `write_sources` writer | PR 1 | `docker compose exec -T backend pytest -q apps/generation_runner/tests/test_write_sources.py` | N/A: tmp_path filesystem only | `writer/`, `tests/test_write_sources.py` |
| 3 | Runner image tag + sample model | PR 1 | `docker compose exec -T backend pytest -q apps/generation_runner/tests/test_runner_image.py apps/generation_runner/tests/test_sample_model.py` | N/A: pure Python | `runner_image.py`, `samples/` |
| 4 | CLI | PR 1 | `docker compose exec -T backend pytest -q apps/generation_runner/tests/test_cli.py` | subprocess of `python -m apps.generation_runner.cli` | `cli.py` |
| 5 | Harness files (`.gitignore`, compose, script) | PR 1 | N/A (manual, DD85) | `bash scripts/verify-generated-project.sh` | 3 files; `docker volume rm <project>_generated_project` |
| 6 | Resolve "To Confirm at Apply" empirically | PR 1 | N/A (manual) | Real compose runs per item | compose/script fallbacks only |
| 7 | Manual gate run + negative checks | PR 1 | N/A (manual) | `bash scripts/verify-generated-project.sh` | evidence only, no files |
| 8 | Regression + docs | PR 1 | `docker compose exec -T backend pytest -q` | full suite (baseline 764; spring_generator 317) | `docs/ai/*` |

Settled decisions: `writer/` and `domain/` never import `apps.spring_generator` (DD75/DD76); no container path in Python (DD84); no version literal anywhere but `emit/versions.py` (DD80); no `jvm` marker, no Docker socket (DD85). Test order inside each Python unit is RED test task, then GREEN task, then refactor.

## Phase 1: App shell, errors, guard (Unit 1)

- [x] 1.1 RED: create `backend/apps/generation_runner/tests/__init__.py` and `tests/test_apps.py`: `apps.get_app_config("generation_runner")` has name `apps.generation_runner`, label `generation_runner`. Fails: app absent.
- [x] 1.2 GREEN: create `backend/apps/generation_runner/__init__.py`, `apps.py` (`GenerationRunnerConfig`, mirror `backend/apps/spring_generator/apps.py` (read-only)), `domain/__init__.py`, `samples/__init__.py`; add `"apps.generation_runner"` to `INSTALLED_APPS` in `backend/config/settings.py`.
- [x] 1.3 RED: create `tests/test_writer_decoupling.py`: AST-walk every `.py` under `writer/` and `domain/` (assert both dirs contain files, no vacuous pass), no `Import`/`ImportFrom` naming `apps.spring_generator`; subprocess imports `apps.generation_runner.writer` and asserts `"apps.spring_generator" not in sys.modules`.
- [x] 1.4 RED: in `tests/test_write_sources.py` add error-hierarchy tests: four subclasses derive from `GeneratedSourceWriteError`; each carries the offending value (`path`/`target`) and a non-empty message.
- [x] 1.5 GREEN: create `domain/errors.py` (DD77): `GeneratedSourceWriteError`, `InvalidGeneratedPathError(path, reason)`, `DuplicateGeneratedPathError`, `EscapingGeneratedPathError`, `NonEmptyTargetDirectoryError`.
- [x] 1.6 GREEN: create `domain/protocols.py` (DD76): `GeneratedFileLike`, `GeneratedSourcesLike` as plain `typing.Protocol` (not `runtime_checkable`), zero `apps.spring_generator` imports.

## Phase 2: Writer (Unit 2)

- [x] 2.1 RED: `tests/test_write_sources.py` shape rejections, one parametrized case each: `""`, NUL, backslash, `/abs`, `C:\x`, `C:/x`, trailing `/`, `.`, `..`, empty segment (`a//b`), `a/../../x`; each asserts `InvalidGeneratedPathError` and an empty `tmp_path`.
- [x] 2.2 RED: same file: exact duplicate and case-only duplicate (`A/Foo.java` vs `a/foo.java`, message contains "differs only by case") raise `DuplicateGeneratedPathError`; nothing written; duplicate check runs only after all shape checks pass.
- [x] 2.3 RED: same file, target rules: non-empty target raises `NonEmptyTargetDirectoryError` and stale `Old.java` is untouched; missing and empty targets accepted; a non-empty target wins over an invalid path (DD78 order).
- [x] 2.4 RED: same file, atomicity: nine valid files then one `..` path raises and `tmp_path` stays empty; a missing target directory is not created on failure.
- [x] 2.5 RED: same file, happy path: contents with `é` and `\n` are UTF-8 bytes with `b"\r" not in`, nested parent dirs created, returned tuple holds absolute paths in input order; a plain stub object (`SimpleNamespace`) satisfying the Protocol is accepted.
- [x] 2.6 RED: same file, step-4 escape: step 1 refuses any non-empty target, so a symlink cannot pre-exist in a valid target. Test the escape helper directly with a symlinked subdirectory in `tmp_path`, plus an end-to-end case monkeypatching the resolve step; both raise `EscapingGeneratedPathError`, nothing written. (Design gap: recorded in 7.6.)
- [x] 2.7 GREEN: create `writer/filesystem.py` (`write_sources`, DD78 order: target, shape, duplicates, escape, write; `newline="\n"`, `encoding="utf-8"`) and `writer/__init__.py` re-exporting it. All of 1.3, 1.4, 2.1-2.6 pass.
- [x] 2.8 REFACTOR: extract private helpers per validation step, document the accepted mid-write `OSError` non-rollback in the docstring; rerun `apps/generation_runner` tests, all green.

## Phase 3: Runner image and sample model (Unit 3)

- [x] 3.1 RED: create `tests/test_runner_image.py`: `gradle_runner_image()` equals `f"gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}"` built from constants imported from `apps.spring_generator.emit.versions`; no version literal in the test.
- [x] 3.2 GREEN: create `runner_image.py` (DD80) importing only those two constants.
- [x] 3.3 RED: create `tests/test_sample_model.py`: `generate_project_sources(build_sample_relational_model(), base_package=...)` succeeds; two calls equal; contains `build.gradle` and `settings.gradle`; exact file count 41; model covers scalar types, an enum, a many-to-one, a Single Table hierarchy, an N:M join table; inheritance class ids are readable (non-uuid); module docstring names `apps/spring_generator/emit/inheritance_context.py:169`.
- [x] 3.4 GREEN: create `samples/sample_model.py` (DD81): `build_sample_model()` (`CanonicalUmlModel`, readable ids) and `build_sample_relational_model()` (`map_to_relational`); docstring names the line-169 defect and the switch to `new_id()`; reference spike shape in `exploration.md` (read-only).
- [x] 3.5 GREEN: if the first RED run disagrees with 41, adjust the count once and record the evidence in the apply-progress artifact; otherwise mark done as confirmed.

## Phase 4: CLI (Unit 4)

- [x] 4.1 RED: create `tests/test_cli.py` (subprocess, `sys.executable -m apps.generation_runner.cli`, cwd `backend/`, `DJANGO_SETTINGS_MODULE` and `POSTGRES_*` removed from env): `--target tmp_path/out` exits 0 with 41 files on disk; non-empty target exits 1, stderr has a message, no `Traceback`, target unmodified; missing `--target` exits 2; invalid `--base-package` exits 1.
- [x] 4.2 RED: same file: a `python -c` subprocess replaces `django.setup` with a function that raises, then `runpy`-runs the CLI as `__main__`; exit 0 proves `django.setup` was never called (DD79).
- [x] 4.3 GREEN: create `cli.py` (DD79): argparse `--target` (required) and `--base-package` (default `com.modelia.generated`), `main()` catching `GeneratedSourceWriteError` and generation `ValueError` to stderr with exit 1; no `django` import, no `/generated/project` literal (DD84).

## Phase 5: Harness files (Unit 5)

- [x] 5.1 Append `.gradle/` to `.gitignore` (DD86); `build/` already ignored.
- [x] 5.2 Add to `docker-compose.yml`: top-level named volume `generated_project`; service `generate-project` (backend image, `profiles: [jvm-verify]`, `entrypoint: []`, `user: root`, no `env_file`, volume `/generated`, command `sh -c 'rm -rf /generated/project && python -m apps.generation_runner.cli --target /generated/project'`, literal only); service `jvm-verify` (`image: ${GRADLE_IMAGE:?}`, `profiles: [jvm-verify]`, `user: root`, `working_dir: /generated/project`, `gradle build --no-daemon`, `depends_on: generate-project: condition: service_completed_successfully`). No `docker.sock`, no Gradle cache volume.
- [x] 5.3 Create `scripts/verify-generated-project.sh` (DD82): `set -euo pipefail`, `MSYS_NO_PATHCONV=1`, compute tag via `GRADLE_IMAGE=gradle:bootstrap docker compose run --rm generate-project python -c "...gradle_runner_image()"`, empty-tag guard, print resolved `GRADLE_IMAGE`, export, then `docker compose --profile jvm-verify run --rm jvm-verify`; no version literal, no inline container path.

## Phase 6: Resolve "To Confirm at Apply" (Unit 6, dedicated, empirical)

- [x] 6.1 Added item (DD82 implication): with `GRADLE_IMAGE` unset, run `docker compose config -q` and `docker compose exec -T backend true`. If interpolation of `${GRADLE_IMAGE:?}` aborts these ordinary commands, the default workflow and the test command break, contradicting "Default up unaffected". Fallback: use a sentinel default in the `image:` value so it fails at pull time naming `GRADLE_IMAGE`, and update the negative check 7.2 accordingly.
- [x] 6.2 Design item 3: `echo "[$GRADLE_IMAGE]"` in the script shows no stray CR or compose noise. Fallback: `tr -d '\r'` and `-T`/`--no-deps` on the `run`.
- [x] 6.3 Design item 1: gate log shows `generate-project` exit 0 before Gradle starts under `run --rm jvm-verify`. Fallback: two explicit steps `run --rm generate-project` then `run --rm jvm-verify` in the script.
- [x] 6.4 Design item 2: no `Could not create ... .gradle` or permission error under `user: root`. Fallback: `GRADLE_USER_HOME: /tmp/gradle-home` on `jvm-verify`.
- [x] 6.5 Design item 4: `docker compose ps -a` after a gate run; document any stopped `generate-project` container in the session note; do not add `down`.
- [x] 6.6 Record each outcome (confirmed or fallback applied, with evidence) in the apply-progress artifact; apply any fallback edits to `docker-compose.yml` or `scripts/verify-generated-project.sh`; note the 2.6 symlink test-seam gap and its resolution.

## Phase 7: Manual gate run (Unit 7, MANUAL, DD85)

- [x] 7.1 Run `bash scripts/verify-generated-project.sh` from the repo root in Git Bash. Expected: `BUILD SUCCESSFUL`, `echo $?` prints `0`. Record in apply-progress and the verify report evidence: exact command, resolved `GRADLE_IMAGE`, final Gradle status line, exit code, output excerpt.
- [x] 7.2 Negative: run `env -u GRADLE_IMAGE docker compose --profile jvm-verify run --rm jvm-verify`. Expected: fails loudly naming `GRADLE_IMAGE` before any container starts (or per the 6.1 fallback: pull failure naming it). Record output excerpt and exit code.
- [x] 7.3 Negative: `docker compose --profile jvm-verify run --rm generate-project python -m apps.generation_runner.cli --target /generated/project` (target now non-empty). Expected: non-zero exit, stderr message, volume untouched. Record it.
- [x] 7.4 Run `docker compose config --services` without the profile: neither `generate-project` nor `jvm-verify` listed. Record it.

## Phase 8: Regression and docs (Unit 8)

- [x] 8.1 Run `docker compose exec -T backend pytest -q apps/spring_generator`: 317 pre-existing tests green, unmodified.
- [x] 8.2 Run `docker compose exec -T backend pytest -q`: 764 pre-existing plus new runner tests all green; report the exact new total.
- [x] 8.3 Confirm default-suite isolation: no `jvm` marker in `backend/pyproject.toml`; no `docker.sock` in `docker-compose.yml`; no version literal in `apps/generation_runner/`, compose or the script.
- [x] 8.4 Update `docs/ai/DECISIONS_LOG.md` (DD75-DD86).
- [x] 8.5 Update `docs/ai/CURRENT_STATE.md` (gate exists, slice 2 of 3, sample-model workaround) and `docs/ai/NEXT_STEPS.md` (slice 3 boot smoke, line-169 defect fix, gate command).
- [x] 8.6 Update `docs/ai/HANDOFF_LATEST.md` (gate command, evidence, archived list, DD range to DD86).
- [x] 8.7 Create `docs/ai/sessions/2026-09-19-agent-generated-project-compile-check.md`.

## Spec coverage

Writer Path Validation: 1.4, 2.1, 2.2, 2.6. Atomicity: 2.4. Encoding and Output: 2.5. Non-Empty Target: 2.3. Writer Decoupling: 1.3, 2.5. Sample Model: 3.3-3.5. CLI Behavior: 4.1, 4.2, 7.3. Image Tag Derivation: 3.1, 6.2, 7.2. Compose Chain Contract: 5.2, 6.3-6.5, 7.1, 7.4. Default Suite Isolation: 8.2, 8.3. Manual Gate Evidence: 7.1.

Total: 42 tasks (P1 6, P2 8, P3 5, P4 3, P5 3, P6 6, P7 4, P8 7). All sequential within a unit; units 2, 3 and 4 depend only on Unit 1 and could run in parallel, but the single-writer PR applies them in order.

## Apply notes (phases 5-8)

- 6.1 broke ordinary compose commands; fallback applied (sentinel default image naming `GRADLE_IMAGE`); check 7.2 became a pull failure naming it. 6.2-6.5 confirmed, no fallback. Extra fix: `generate-project` mounts `./backend:/app:ro` (dev image ships no source). Evidence: `gate-evidence.md`.
- 2.6/6.6 symlink gap: DD78 step 1 refuses any non-empty target, so a real pre-existing symlink is unreachable through `write_sources`; covered by the `_reject_escaping_paths` helper test plus a monkeypatched `_resolve` end-to-end test.
- Flag for verify: the CLI catches `(GeneratedSourceWriteError, ValueError)` only; a generator `UngeneratableSourceError` would surface as a traceback (not widened here).
- Full suite: 820 passed (764 + 56 new); `apps/spring_generator` 317 passed.
