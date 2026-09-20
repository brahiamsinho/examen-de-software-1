# Design: Generated Project Compile Check

Slice 2 of 3 (spec §37 item 13). Inputs: `proposal.md`, `exploration.md`. Decisions continue the project sequence from DD75 (last archived cycle ended at DD74).

## Technical Approach

`generate_project_sources(model, *, base_package) -> GeneratedSources` (DD74) already guarantees POSIX-relative paths and LF text. This slice adds the *only* two things missing between that text and a compiler: a filesystem writer that re-validates every path, and a JVM. The writer, its errors and its input Protocol are a pure, `spring_generator`-free package inside a new Django app `apps.generation_runner`; the glue (CLI, sample-model builder, image-tag function) sits in the same app outside that package and may import the generator. The JVM never enters the backend image and never reaches a Docker socket: a profile-gated compose pair writes into a named volume and builds it with `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}`, driven by one host bash script that computes that tag from `emit/versions.py` (DD62 stays the single source of truth).

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD75 | New app `apps/generation_runner/` splits into **pure** (`domain/errors.py`, `domain/protocols.py`, `writer/filesystem.py`) and **glue** (`cli.py`, `runner_image.py`, `samples/sample_model.py`). The decoupling guard covers `writer/**` and `domain/**` only. | Writer inside `spring_generator`; a top-level `apps/project_writer` plus a separate runner app; one flat module. | One app per domain is the standing convention, and the generator's purity invariant (DD74: no writer, no `spring_generator` → runner edge) survives only if the direction is enforced. Splitting *inside* one app keeps the guard a two-directory scan instead of a cross-app dependency rule, while the glue can freely import the generator because nothing imports the glue. |
| DD76 | The writer types its input with `typing.Protocol` (`GeneratedSourcesLike.files`, `GeneratedFileLike.path/.contents`), not `runtime_checkable`, no `isinstance`. | `from apps.spring_generator.domain.sources import GeneratedSources`; `Any`; a duplicated dataclass. | A structural type gives full static checking with **zero** import edge — that is the whole mechanism that makes DD75's guard passable. Not `runtime_checkable` because `isinstance` on a Protocol only checks attribute presence, which buys nothing over the validation that follows and invites a false sense of type safety. |
| DD77 | Typed errors in `domain/errors.py`: base `GeneratedSourceWriteError`, subclasses `InvalidGeneratedPathError`, `DuplicateGeneratedPathError`, `EscapingGeneratedPathError`, `NonEmptyTargetDirectoryError`. Each carries the offending value. | Reusing `ValueError`/`OSError`; one error class with a `reason` string; reusing `GeneratedSourcePathCollisionError` from the generator. | Four failure modes have four different operator responses (fix the generator, fix a name collision, security incident, clear the target). Reusing the generator's collision error would be exactly the import DD75 forbids. A shared base lets the CLI catch one thing and exit 1. |
| DD78 | `write_sources(sources, target_dir) -> tuple[Path, ...]` validates **everything before writing anything**, in this fixed order: (1) target emptiness, (2) per-file shape in `files` order, (3) duplicates over the whole tuple, (4) resolved-escape check, (5) write. | Streaming validate-and-write; `os.path.normpath` only; writing to a temp dir then moving. | Ordering is cheapest-and-most-total first: a non-empty target refuses the whole call before a single path is parsed, and shape errors are pure string work that never touches the filesystem. The escape check runs last because it is the only step that resolves against the real filesystem. Temp-dir-then-move was rejected: the target is a volume mountpoint subdirectory, and a cross-device rename is a new failure mode for no gain. |
| DD79 | CLI `python -m apps.generation_runner.cli --target <dir> [--base-package …]`, **no** `django.setup()` and no `DJANGO_SETTINGS_MODULE`. Exit 0 success, 1 any `GeneratedSourceWriteError` or generation error (message to stderr, no traceback), 2 argparse usage. | A Django management command; `django.setup()` for symmetry with other entry points. | A management command would drag in `config.settings`, which reads `POSTGRES_*` with no defaults — the one-shot service would then need `backend/.env`, and the gate would break on a fresh clone. Plain `__main__` keeps the service `env_file`-free. A subprocess test with the settings variable unset proves it rather than assuming it. |
| DD80 | `runner_image.gradle_runner_image() -> str` returns `f"gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}"`, imported from `emit/versions.py`. No version literal appears in this app, the compose file, the script or any test. | A compose `.env` file with the tag; a literal in the script; a drift-guard test restating the literals. | DD62 says one place. A checked-in env file or a guard test restates the literal and recreates the bump-drift failure mode the constant exists to prevent — the test asserts against the imported constants, never against `"9.7.1"`. |
| DD81 | `samples/sample_model.py` builds the spike model with **readable** `ElementId` strings (`"customer"`, `"vehicle"`, …), carrying a module docstring naming `apps/spring_generator/emit/inheritance_context.py:169` and the switch to `new_id()` once fixed. | `new_id()` now; skipping the inheritance classes; fixing the defect in this slice. | That line renders `pascal_case(class_id)` where it must read `discriminator_values[class_id]`, so a uuid4 hex id yields an invalid Java discriminator literal. Dropping inheritance would remove Single-Table coverage from the only project the gate ever compiles; fixing it here is scope creep on a queued change. A named, documented workaround is the honest middle. |
| DD82 | Host entry `scripts/verify-generated-project.sh` (Git Bash, D8): computes the tag with a one-line `docker compose run` on `generate-project` prefixed by a throwaway `GRADLE_IMAGE=gradle:bootstrap`, exports the real value, then runs `docker compose --profile jvm-verify run --rm jvm-verify`. | Computing the tag inside compose (impossible); `docker compose config` parsing; a PowerShell twin. | Compose interpolates the **whole** file before running any service, so `${GRADLE_IMAGE:?}` on `jvm-verify` aborts even a `generate-project`-only run — the bootstrap value satisfies interpolation and is never pulled because that service is not started. `generate-project` is used for the computation (not `backend`) precisely because it has no `env_file`, so the gate works without `backend/.env`. |
| DD83 | Two profile-gated services over named volume `generated_project` mounted at `/generated`; `generate-project` runs `sh -c 'rm -rf /generated/project && python -m …'`; `jvm-verify` runs `gradle build --no-daemon` in `/generated/project` under `depends_on: condition: service_completed_successfully`. Both `user: root`. | Clearing the directory from the CLI (a `--clean` flag); `docker volume rm` from the script; mixing root and the image's `gradle` user. | Keeping deletion in the harness preserves DD78's non-empty refusal as a *real* safety net instead of a switch our own tool flips. A subdirectory is removed, never the mountpoint. Both services root because the generated tree is root-owned and uid-1000 `gradle` could not write `build/` into it; `docker volume rm` from the script would fight the still-attached container. |
| DD84 | The target path reaches the writer only as the CLI `--target` argument, supplied by the compose `command`. No module contains `/generated/project`. | A Django setting; a module constant; an env var read inside the writer. | The writer must stay a pure function of its arguments (DD75), and a container path baked into Python would make the app untestable outside compose and unusable for slice 3's different target. |
| DD85 | Strict TDD covers the Python half only. The compose/Gradle half is proven by one **manual gate run**, whose exact command and exit code are recorded in the verify report. | A pytest test shelling out to `docker compose`; a `jvm` marker with `addopts -m "not jvm"`. | No pytest test can start Gradle without either a Docker socket in the container (rejected) or a host-side runner (there is none), so a `jvm` marker would be dead configuration (D4). Recording the command and exit code is the strongest evidence available and keeps `pytest -q` offline and fast. |
| DD86 | `.gitignore` gains `.gradle/` only (`build/` is already ignored). | Also ignoring `generated/`; no change at all. | All generated state lives in the named volume, so this is purely defensive against someone pointing `--target` at a repo path while debugging. One line, no new directory conventions. |

## Interfaces / Contracts

```python
# domain/protocols.py — zero imports from apps.spring_generator (DD76)
class GeneratedFileLike(Protocol):
    @property
    def path(self) -> str: ...
    @property
    def contents(self) -> str: ...

class GeneratedSourcesLike(Protocol):
    @property
    def files(self) -> tuple[GeneratedFileLike, ...]: ...

# writer/filesystem.py
def write_sources(sources: GeneratedSourcesLike, target_dir: Path | str) -> tuple[Path, ...]: ...
```

### Validation algorithm (DD78, exact order — first failure wins, nothing written)

1. **Target**: resolve `target_dir`. If it exists and `any(target.iterdir())` → `NonEmptyTargetDirectoryError(target)`. A missing target is fine (created in step 5).
2. **Per file**, iterating `sources.files` in order, raising `InvalidGeneratedPathError(path, reason)`:
   a. `path` is a non-empty `str`; b. no `"\x00"`; c. no `"\\"` (covers `C:\x` and Windows separators in one check); d. not absolute — reject a leading `"/"` and a drive prefix matching `^[A-Za-z]:` (covers `C:/x`); e. no trailing `"/"`; f. split on `"/"`: every segment non-empty and neither `"."` nor `".."`.
3. **Duplicates** over the whole tuple, after every shape check has passed: exact repeat → `DuplicateGeneratedPathError`; `path.casefold()` repeat → same error, message states "differs only by case" (a case-insensitive volume would silently overwrite).
4. **Escape**, defence in depth: `candidate = (target.resolve() / path).resolve()`; require `candidate.is_relative_to(target.resolve())`, else `EscapingGeneratedPathError`. Steps 2d/2f cannot see a symlink; this can.
5. **Write**: `target.mkdir(parents=True, exist_ok=True)`, then per file `parent.mkdir(parents=True, exist_ok=True)` and `write_text(contents, encoding="utf-8", newline="\n")`. Return absolute written paths in input order.

Atomicity is *pre-write*: no validation failure can leave a partial tree. A mid-write `OSError` is **not** rolled back — accepted and documented, because the harness clears the target and step 1 refuses a dirty one.

## Data Flow

    scripts/verify-generated-project.sh  (Git Bash, host)
       │  GRADLE_IMAGE=gradle:bootstrap  compose run generate-project
       │      └─ runner_image.gradle_runner_image() ──→ emit/versions.py
       │  export GRADLE_IMAGE=gradle:9.7.1-jdk21
       ↓
    docker compose --profile jvm-verify run --rm jvm-verify
       │
       ├─ generate-project (backend image, entrypoint: [], no env_file, root)
       │     sh -c 'rm -rf /generated/project && python -m apps.generation_runner.cli
       │             --target /generated/project'
       │        build_sample_model() → map_to_relational → generate_project_sources
       │             → write_sources(...) ──→ volume generated_project:/generated
       │     exit 0 ──┐ service_completed_successfully
       ↓              ↓
    jvm-verify (${GRADLE_IMAGE:?}, root, wd /generated/project)
       gradle build --no-daemon  ──→ exit code ──→ compose ──→ script exit code

## File Changes

| File | Action | ~Lines | Description |
|---|---|---|---|
| `backend/apps/generation_runner/__init__.py` | Create | 0 | Package marker |
| `…/apps.py` | Create | 12 | `GenerationRunnerConfig` (mirrors `spring_generator/apps.py`) |
| `…/domain/__init__.py` | Create | 0 | Marker |
| `…/domain/errors.py` | Create | 35 | DD77 error hierarchy |
| `…/domain/protocols.py` | Create | 25 | DD76 Protocols |
| `…/writer/__init__.py` | Create | 5 | Re-export `write_sources` |
| `…/writer/filesystem.py` | Create | 95 | DD78 algorithm |
| `…/runner_image.py` | Create | 15 | DD80 tag function |
| `…/samples/__init__.py` | Create | 0 | Marker |
| `…/samples/sample_model.py` | Create | 150 | DD81 builder + `build_sample_relational_model()` |
| `…/cli.py` | Create | 50 | DD79 argparse + `main()` |
| `…/tests/__init__.py` | Create | 0 | Marker |
| `…/tests/test_apps.py` | Create | 12 | Registration |
| `…/tests/test_write_sources.py` | Create | 210 | Validation + write behaviour |
| `…/tests/test_writer_decoupling.py` | Create | 35 | DD75 guard |
| `…/tests/test_runner_image.py` | Create | 15 | DD80 |
| `…/tests/test_sample_model.py` | Create | 50 | DD81 |
| `…/tests/test_cli.py` | Create | 60 | DD79 subprocess contract |
| `backend/config/settings.py` | Modify | +1 | `"apps.generation_runner"` in `INSTALLED_APPS` (D7) |
| `docker-compose.yml` | Modify | +40 | DD83 two services + `generated_project` volume |
| `scripts/verify-generated-project.sh` | Create | 35 | DD82 |
| `.gitignore` | Modify | +1 | DD86 `.gradle/` |
| `openspec/changes/…/specs/generated-project-verification/spec.md` | Create | 200 | New capability |
| `docs/ai/{CURRENT_STATE,HANDOFF_LATEST,NEXT_STEPS,DECISIONS_LOG}.md` + session note | Modify | 80 | Gate docs, DD75–DD86 |

**Total ≈ 1130** — matches the proposal forecast. `400-line budget risk: High`; single PR under the already-accepted `size:exception`.

## Testing Strategy (Strict TDD — RED first, per file)

| Test file | Type | Cases |
|---|---|---|
| `test_write_sources.py` | pytest, `tmp_path` | One case per DD78 rejection (empty, NUL, backslash, `/abs`, `C:\x`, `C:/x`, trailing `/`, `.`, `..`, empty segment), exact duplicate, case-only duplicate, symlink escape, non-empty target; **no-partial-write** (a bad path late in the tuple leaves `tmp_path` empty); happy path asserts UTF-8 bytes, LF-only bytes (`b"\r" not in`), nested dirs created, returned paths |
| `test_writer_decoupling.py` | pytest | AST-walks every `.py` under `writer/` and `domain/`, asserts no `Import`/`ImportFrom` names `apps.spring_generator`; plus a subprocess importing `apps.generation_runner.writer` and asserting `"apps.spring_generator" not in sys.modules` |
| `test_runner_image.py` | pytest | Equals `f"gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}"` built from the **imported** constants, never literals |
| `test_sample_model.py` | pytest | `generate_project_sources(build_sample_relational_model())` succeeds, is deterministic across two calls, contains `build.gradle`/`settings.gradle`, exact file count 41 (spike oracle; adjust once with evidence if the first RED run disagrees) |
| `test_cli.py` | pytest, `subprocess` | `sys.executable -m apps.generation_runner.cli --target tmp_path` with `DJANGO_SETTINGS_MODULE` **removed** from the env → exit 0 and files on disk (proves DD79); exit 1 + stderr message + no traceback on a non-empty target; exit 2 on a missing `--target` |
| `test_apps.py` | pytest | `apps.get_app_config("generation_runner")` name/label |
| **Compile gate** | **Manual** (DD85) | `bash scripts/verify-generated-project.sh` → `BUILD SUCCESSFUL`, exit 0. Verify report records: exact command, resolved `GRADLE_IMAGE`, final Gradle status line, `echo $?` |

Default `pytest -q` stays Docker-free, offline and marker-free.

## Threat Matrix

| Boundary | Applicability | Design response | Planned RED test |
|---|---|---|---|
| Documentation-like paths | **N/A** — nothing classifies or executes repository files by name or extension | — | — |
| Git repository selection | **N/A** — no VCS automation in this change | — | — |
| Commit state | **N/A** — no index or worktree operation | — | — |
| Push state | **N/A** — no remote operation | — | — |
| PR commands | **N/A** — no PR automation | — | — |
| **Path traversal into a write target** (real boundary here) | **Applicable** — `write_sources` materializes attacker-shaped relative paths | DD78 steps 2d/2f/4: absolute, drive-letter, `..`, and resolved-escape all refuse with `InvalidGeneratedPathError`/`EscapingGeneratedPathError`, nothing written | `/etc/passwd`, `C:\x`, `C:/x`, `a/../../x`, and a symlinked subdirectory, each asserting the typed error **and** an empty `tmp_path` |
| **Destructive shell in the harness** | **Applicable** — `rm -rf /generated/project` runs as root | DD83: the deleted path is a fixed subdirectory *inside* the mountpoint, never `/generated`, never a host bind mount; it is a compose literal, never interpolated from a variable or an argument | Gate-run evidence only (DD85): compose `command` reviewed as a literal list; no variable appears in the `rm` argument |
| **Shell argument composition in the script** | **Applicable** — Git Bash mangles container paths | DD82: every container path stays in `docker-compose.yml`; the script passes none inline and prefixes compose calls with `MSYS_NO_PATHCONV=1`; `set -euo pipefail` plus an empty-tag guard so an unresolved tag fails loudly instead of running `gradle:` | Gate-run evidence (DD85): the script prints the resolved `GRADLE_IMAGE` before running |

## To Confirm at Apply

| Item | Verification step | Fallback if wrong |
|---|---|---|
| `docker compose run --rm jvm-verify` honours `service_completed_successfully` on its dependency | Run the gate; the log must show `generate-project` exit 0 **before** Gradle starts | Two explicit steps in the script: `run --rm generate-project`, then `run --rm jvm-verify` |
| `GRADLE_USER_HOME` under `user: root` in the `gradle` image | Run the gate; look for a `Could not create … .gradle` / permission error | Add `GRADLE_USER_HOME: /tmp/gradle-home` to the `jvm-verify` service |
| Tag-computation stdout is clean in Git Bash (no CR, no compose noise) | `echo "[$GRADLE_IMAGE]"` in the script must show no stray characters | Pipe through `tr -d '\r'` and add `-T` / `--no-deps` to the `run` |
| `generate-project` leaves a stopped container after a `run --rm jvm-verify` chain | `docker compose ps -a` after a gate run | Document it (the next run replaces it); do **not** add a `down`, which would stop `db`/`redis` |

## Migration / Rollout

No migration. Purely additive: no existing module changes behaviour, the two services are inert without `--profile jvm-verify`, and `pytest -q` / `docker compose up` are unaffected. Rollback per the proposal, plus `docker volume rm <project>_generated_project`.

## Open Questions

- [ ] None blocking. Every remaining unknown is in **To Confirm at Apply** with a concrete check and a concrete fallback.
