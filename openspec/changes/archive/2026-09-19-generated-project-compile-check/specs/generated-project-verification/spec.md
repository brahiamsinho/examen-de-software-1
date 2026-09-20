# Generated Project Verification Specification

## Purpose

Defines how the in-memory Gradle project returned by `generate_project_sources` is materialized to disk and proven to compile with `gradle build --no-daemon`. Covers the source writer, the sample model, the CLI, the runner-image tag, the compose chain and the manual gate evidence. A green build proves compilation and packaging only; boot, schema, reserved words and name collisions are out of scope.

Verification key: **[pytest]** = automated in the default suite (Docker-free, offline); **[manual]** = verified by a recorded gate run.

## Requirements

### Requirement: Writer Path Validation

`write_sources(sources, target_dir)` MUST validate every file path before writing anything. It MUST reject, each with a typed error: empty paths; absolute paths (`/x`, `C:\x`, `C:/x`); `.`, `..` or empty segments; backslashes; NUL characters; trailing slashes; exact duplicates; case-insensitive duplicates; and any path whose resolved location escapes `target_dir`. **[pytest]**

#### Scenario: Unsafe path is rejected

- GIVEN sources containing one path from any reject class above
- WHEN `write_sources` is called
- THEN a typed error is raised and `target_dir` contains no files

#### Scenario: Case-insensitive duplicate is rejected

- GIVEN sources with `A/Foo.java` and `a/foo.java`
- WHEN `write_sources` is called
- THEN a typed duplicate-path error is raised and nothing is written

### Requirement: Validate-Before-Write Atomicity

The writer MUST complete validation of all files before creating any file or directory. A late-position invalid path MUST NOT leave earlier valid files on disk. **[pytest]**

#### Scenario: Invalid last file writes nothing

- GIVEN nine valid files followed by one path containing `..`
- WHEN `write_sources` is called
- THEN the error is raised and `target_dir` is still empty

### Requirement: Encoding and Output

The writer MUST write each file as UTF-8 with LF line endings (`newline="\n"`), creating parent directories as needed, and MUST return the tuple of written paths. **[pytest]**

#### Scenario: Non-ASCII content with LF endings

- GIVEN a file whose contents include `é` and `\n`
- WHEN it is written
- THEN the bytes on disk are UTF-8, contain no `\r`, and the returned tuple contains that file's path

### Requirement: Non-Empty Target Refusal

The writer MUST refuse a `target_dir` that already contains any entry, with a typed error, to prevent a stale-file false green. A missing or empty `target_dir` MUST be accepted. **[pytest]**

#### Scenario: Stale target refused

- GIVEN `target_dir` containing a stale `Old.java`
- WHEN `write_sources` is called
- THEN a typed non-empty-target error is raised and `Old.java` is untouched

### Requirement: Writer Decoupling

The writer package MUST accept its input through a `typing.Protocol` (`.files`, `.path`, `.contents`) and MUST NOT import from `apps.spring_generator`. **[pytest]**

#### Scenario: Import guard

- GIVEN every module in the writer package
- WHEN a guard test scans their imports
- THEN none references `apps.spring_generator`, and a plain stub object satisfying the Protocol is accepted

### Requirement: Sample Model

The runner app MUST provide a sample-model builder using `CanonicalUmlModel` and `map_to_relational`, with readable inheritance class ids, covering scalar types, an enum, a many-to-one, a Single Table hierarchy and an N:M join table. Feeding it to `generate_project_sources` MUST succeed deterministically. **[pytest]**

#### Scenario: Deterministic generation

- GIVEN `build_sample_model()` called twice
- WHEN `generate_project_sources(..., base_package=...)` runs on each
- THEN both results are identical, include `build.gradle`, and contain the expected file count (about 41)

### Requirement: CLI Behavior

`python -m apps.generation_runner.cli` MUST generate the sample project into a target directory via `write_sources` without calling `django.setup()`. It MUST exit 0 on success and non-zero, with a message on stderr, when the writer raises a typed error. **[pytest]** for exit codes and no Django setup; **[manual]** inside the container.

#### Scenario: Refused target yields non-zero exit

- GIVEN a non-empty target directory
- WHEN the CLI runs
- THEN the exit code is non-zero and nothing in the target is modified

#### Scenario: No Django bootstrap

- GIVEN the CLI module is imported and run
- WHEN it completes
- THEN `django.setup` was never called and no `POSTGRES_*` variables were required

### Requirement: Image Tag Derivation

The runner image tag `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}` MUST be computed by a function reading only `emit/versions.py`. The host script MUST obtain it from that function and export `GRADLE_IMAGE`. No version literal MAY appear in compose, env files or the script. Compose MUST consume it as `${GRADLE_IMAGE:?}`. **[pytest]** for the function; **[manual]** for script and compose.

#### Scenario: Tag follows versions.py

- GIVEN `GRADLE_VERSION` and `JAVA_VERSION` values in `versions.py`
- WHEN the function is called
- THEN it returns `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}` exactly

#### Scenario: Unset image fails loudly

- GIVEN `GRADLE_IMAGE` is unset
- WHEN compose resolves `jvm-verify`
- THEN compose aborts with an error naming `GRADLE_IMAGE` before any container starts **[manual]**

### Requirement: Compose Chain Contract

Compose MUST define profile `jvm-verify` with a one-shot `generate-project` service (backend image, `entrypoint: []`, no `env_file`) and a `jvm-verify` service running `gradle build --no-daemon`, both on named volume `generated_project`. `jvm-verify` MUST depend on `generate-project` with `service_completed_successfully`, and the harness MUST clear the target subdirectory before generation. The gate exit code MUST propagate to the host script. No Docker socket MAY be mounted into the backend container, and no Gradle cache volume is defined. **[manual]**

#### Scenario: Default up unaffected

- GIVEN the compose file with the new profile
- WHEN `docker compose up` runs without `--profile`
- THEN neither new service starts

#### Scenario: Failure propagates

- GIVEN a generated project that fails to compile, or a failing `generate-project`
- WHEN the entry script runs the chain
- THEN the script exits non-zero and Gradle does not run after a failed generation

### Requirement: Default Suite Isolation

The default `pytest -q` MUST NOT require Docker, network or a JVM, and no `jvm` marker MAY be registered. **[pytest]**

#### Scenario: Offline default suite

- GIVEN a host without Docker daemon access or network
- WHEN `pytest -q` runs
- THEN all runner-app tests pass

### Requirement: Manual Gate Evidence

The verify report MUST record the exact gate command, its exit code, and the `BUILD SUCCESSFUL` line from a run over the sample project. **[manual]**

#### Scenario: Evidence recorded

- GIVEN a completed gate run
- WHEN the verify report is written
- THEN it contains the command, exit code 0 and `BUILD SUCCESSFUL`
