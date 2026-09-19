# Design: Spring Boot Project Scaffold Generation

Two new pure entry points turn the existing 41-file model aggregate into a self-contained
Gradle project, as pure text. Nothing writes, compiles, or runs. Decision numbering continues
from DD60 (`2026-09-19-2026-09-19-spring-boot-whole-model-orchestrator`), so this cycle owns
**DD61–DD74**.

> Size note: this design exceeds the 800-word guideline because the orchestrator explicitly
> required verbatim template bodies and an exact `versions.py` shape. Prose is kept terse.

## Technical Approach

```text
generate_project_scaffold_sources(*, base_package)          generate_project_sources(model, *, base_package)
  ├─ _validate_base_package (DD20)                            ├─ generate_model_sources(model, base_package=...)   → 41 files
  ├─ build_build_script_context(base_package=...)  ──┐         ├─ generate_project_scaffold_sources(base_package=...) → 3 files
  ├─ build_application_class_context(base_package=...)│        ├─ _reject_duplicate_generated_paths(combined tuple)
  ├─ render build.gradle.j2 / settings.gradle.j2 /   │        └─ GeneratedSources(files=combined)
  │  Application.java.j2  ← emit/versions.py ────────┘
  └─ GeneratedSources(build.gradle, settings.gradle, Application.java)
```

Strictly additive. `generate_model_sources` is not touched, called, or re-ordered.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD61 | Both new public functions live in `emit/renderer.py`. | A new `emit/project_renderer.py`; a `scaffold/` sub-package. | `renderer.py` is the single public API surface and already owns `_ENVIRONMENT`, `_validate_base_package`, `_extend_generated_files`, and `_reject_duplicate_generated_paths` — all four are required here. DD51 rejected a separate module for `generate_model_sources` on the same grounds. Growth is bounded to ~55 lines because every context shape moves to DD63's module and every character of emitted text lives in DD64's templates; that split is exactly why `renderer.py` is still 291 lines after the generator grew from 2 to 44 files. If it ever must split, the seam is *entry-point family* (table vs project), never helper extraction. |
| DD62 | New `emit/versions.py` is the only place any generated-toolchain version exists. Consumers read the constants; nobody restates a literal. | Literals inside `build.gradle.j2`; a `versions` dict; deferring `GRADLE_VERSION` to slice 2. | A version restated in a template, a compose file, and a test is three places to forget on a bump — the proposal's top risk. `GRADLE_VERSION` is declared now although this slice renders nothing with it (no wrapper is emitted): slice 2's `gradle:9.7.1-jdk21` runner image must read it from here, and splitting the pin across two changes recreates the failure mode. |
| DD63 | Scaffold template contexts are frozen dataclasses in a new `emit/scaffold_context.py`, a sibling of `emit/inheritance_context.py`. | Adding them to `emit/context.py`; passing raw kwargs to `template.render()`; a dict context. | `context.py` is 660 lines of `Table`/`Column` → Java branching; the scaffold has no column, no type mapping, and no import grouping in common with it. `inheritance_context.py` already set the convention that a distinct generation concern gets its own `*_context.py`. Frozen dataclasses keep the "templates are data-driven, all branching lives in a context builder" invariant (DD2/DD9–DD12) and make the version wiring type-checked instead of stringly-typed. |
| DD64 | The three templates contain **zero** `{% %}` block tags and zero `{#`; they are pure `{{ }}` substitution over static text, LF-terminated with exactly one trailing newline. | Loops over a dependency list; conditional starters; building `build.gradle` in Python. | The DD13/DD49 whitespace lesson (`trim_blocks=True` swallows the newline after *any* `{% %}` tag, including an inline one closing a content line — this collapsed enum constants onto one line once) simply cannot bite a template with no block tags. Groovy/Java never produce `{{`, `{%`, or `{#`: Groovy braces are always `{` + newline and no GString `${…}` is used, so no delimiter escaping is needed — but the invariant is asserted by a test, not assumed. LF is doubly guaranteed: `.gitattributes` has `* text=auto eol=lf`, and Jinja's lexer normalizes `\r\n`/`\r` to `newline_sequence='\n'` regardless of checkout. `keep_trailing_newline=True` is already on `_ENVIRONMENT`. |
| DD65 | `build.gradle` reproduces the slice-0 spike oracle in substance, verbatim in form (see below): `java` + `org.springframework.boot` plugins, `SpringBootPlugin.BOM_COORDINATES` platform, `mavenCentral()` only, toolchain 21, three starters + `runtimeOnly` postgresql. | `io.spring.dependency-management`; springdoc; a Kotlin DSL `build.gradle.kts`; a Gradle wrapper; `.gitignore`. | The spike is the only empirical evidence in this cycle (`gradle build --no-daemon` → BUILD SUCCESSFUL, 49 s). Every rejected item is a settled constraint: dependency-management is redundant under the Boot 4 plugin, springdoc + Boot 4.1 + Jackson 3 is unproven, the wrapper jar is binary and `GeneratedFile.contents` is `str`, and `.gitignore` is VCS hygiene, not compilation. |
| DD66 | `settings.gradle` is one static line rendered from a variable-free template (`.render()` with no context, like `application.yml.j2`); `generated-backend` stays literal template text, not a constant. | A `ROOT_PROJECT_NAME` constant in `versions.py`; a Python string literal in `renderer.py`. | A project name is not a version, so it does not belong in DD62's module. Keeping *all* emitted characters under `emit/templates/` is a single invariant a reviewer and the LibCST guard can both rely on. |
| DD67 | `Application.java` sits in the **root** base package as `src/main/java/<package_path>/Application.java`, built with `"...{}/{}.java".format(package_path(base_package), context.class_name)`. | `config/Application.java`; `api/`; a `<E>Application` name. | `@SpringBootApplication` component-scans its own package downward, so a class in `<pkg>.config` would never scan `domain`/`api` — and `config/` is spec-forbidden anyway. The spec delta names this the single allowed Java file outside the six layer directories. Deriving the path from the same `class_name` the template renders keeps path and content from drifting. |
| DD68 | Scaffold file order is fixed: `build.gradle`, `settings.gradle`, `src/main/java/<pkg>/Application.java`. | Alphabetical; Java first. | Matches the proposal's file list and Success Criteria order. Any order works; the contract is that it is fixed and asserted, per DD53's "ordering is the product contract". |
| DD69 | `generate_project_sources` appends: all model files (unchanged, contiguous), then all scaffold files, then runs one `_reject_duplicate_generated_paths` over the **combined** tuple before constructing `GeneratedSources`. The inner check inside `generate_model_sources` is redundant here but stays (it guards the standalone entry point). | Scaffold first; interleaving; checking only the scaffold subset; dropping the inner check. | The model aggregate order is a published contract (DD53). Making it a contiguous *prefix* means a reviewer diffing the two functions sees only an appended tail, and the composition test can assert by slicing. Checking the combined tuple before construction preserves DD57 atomicity: no partial `GeneratedSources` is ever built or returned. |
| DD70 | No new error type. The only two failure modes are an invalid `base_package` (existing `ValueError`, DD20) and a path collision (existing `GeneratedSourcePathCollisionError`, DD56/DD58). | An `UngeneratableScaffoldError`; promoting `_validate_base_package` to `UngeneratableSourceError`. | The scaffold takes no `Table` and no `EnumType`, so neither `UngeneratableTableError` nor `UngeneratableEnumError` has a reachable raise site — an exception class with no raiser is dead API the archive must keep forever. Promoting the `ValueError` is a separate, cross-cutting change to five existing entry points; note it, do not smuggle it in here. |
| DD71 | Because no scaffold/model path collision is reachable today, the collision test **injects** one by monkeypatching the module-global `renderer.generate_project_scaffold_sources` to return a file at an existing model path. Therefore `generate_project_sources` MUST call its two collaborators by module-global name, never through a captured local alias or a direct import rebound at def time. | Crafting a colliding `RelationalModel` (impossible: model Java lives under six layer dirs, scaffold at the root — a UML class named `Application` yields `domain/Application.java`, not `<pkg>/Application.java`); monkeypatching `_reject_duplicate_generated_paths` (tests the mock). | The duplicate check is a structural invariant, not a reachable bug today. It must still be proven to fire, and a call-by-global-name convention is the cheapest way to keep it provable. A second, direct unit test over a hand-built tuple with `build.gradle` twice covers the helper itself without any mock. |
| DD72 | "Versions live in one place" is enforced mechanically: a test scans every `emit/**/*.py` except `versions.py` and every `emit/templates/*.j2` for `\b4\.1\.1\b` / `\b9\.7\.1\b` / a bare toolchain `21`, and fails on a hit. | Trusting review; asserting only that the rendered text contains the constant. | Containment assertions pass even when the literal is *also* hardcoded somewhere else. Only a negative source scan makes the single-source claim true. |
| DD73 | The scaffold's "no hardcoded deployable value" test list deliberately **omits** `postgres` and `port`, unlike `test_project_config_sources.py`. | Reusing the YAML forbidden list verbatim. | `runtimeOnly 'org.postgresql:postgresql'` is a Maven GAV coordinate, not a deployable value. Copying the YAML list would make the scaffold test fail for the one dependency the spike proved necessary. Host/URL/credential literals (`localhost`, `http://`, `https://`, `jdbc:`, `5432`, `8080`, `0.0.0.0`, `password`, `secret`, drive/absolute paths) are still banned. |
| DD74 | `generate_project_sources(model, *, base_package) -> GeneratedSources` is the sole input contract for the future slice-2 writer. This slice adds no writer, no path-safety re-validation, and no `spring_generator` → runner dependency. | Emitting an absolute path; a `write_to(dir)` convenience; returning a dict. | Slice 2's `write_sources(sources: GeneratedSources, target_dir)` needs only: every `path` POSIX-relative with no `..` and no drive letter, every `contents` a `str` with LF endings. Both hold by construction here, so the writer's job reduces to re-validating paths, `mkdir -p`, and writing text with `newline="\n"` — and it stays in its own app with no import from `emit/`. |

## Interfaces / Contracts

### `backend/apps/spring_generator/emit/versions.py` (new — exact shape)

```python
"""Single pinned source of every generated-project toolchain version (DD62).

No other module, template, test, compose file, or script may restate one of
these literals; `tests/test_project_scaffold_sources.py` enforces that by
source scan (DD72). Bumping a version is a deliberate, reviewable one-line
change that slices 2-3 re-verify by compiling and booting.
"""
from typing import Final

SPRING_BOOT_VERSION: Final[str] = "4.1.1"
"""Spring Boot Gradle plugin and BOM version (spike oracle: BUILD SUCCESSFUL)."""

JAVA_VERSION: Final[int] = 21
"""Java toolchain language version. `int`, not `str`, because the template
renders it into `JavaLanguageVersion.of({{ java_version }})`, which takes an
int — quoting it would be a Groovy type error."""

PROJECT_VERSION: Final[str] = "0.0.1-SNAPSHOT"
"""`version` of the generated Gradle project."""

GRADLE_VERSION: Final[str] = "9.7.1"
"""Gradle required to build the generated project. Nothing in this slice
renders it (no wrapper is emitted, DD65); slice 2's `gradle:9.7.1-jdk21`
runner image reads it from here (DD62)."""
```

### `backend/apps/spring_generator/emit/scaffold_context.py` (new)

```python
from dataclasses import dataclass

from apps.spring_generator.emit.versions import (
    JAVA_VERSION, PROJECT_VERSION, SPRING_BOOT_VERSION,
)

APPLICATION_CLASS_NAME = "Application"


@dataclass(frozen=True)
class BuildScriptContext:
    group: str                 # == base_package (settled constraint)
    version: str               # PROJECT_VERSION
    spring_boot_version: str   # SPRING_BOOT_VERSION
    java_version: int          # JAVA_VERSION


@dataclass(frozen=True)
class ApplicationClassContext:
    package: str               # == base_package (root package, DD67)
    class_name: str            # APPLICATION_CLASS_NAME


def build_build_script_context(*, base_package: str) -> BuildScriptContext: ...
def build_application_class_context(*, base_package: str) -> ApplicationClassContext: ...
```

Both builders are total, allocation-only, and contain no `+`, `.join`, `%`, or f-string
(DD14 guard applies automatically — `test_no_concat_guard.py` globs `emit/**/*.py`).

### `backend/apps/spring_generator/emit/renderer.py` (modified)

```python
def generate_project_scaffold_sources(*, base_package: str = "com.modelia.generated") -> GeneratedSources: ...
def generate_project_sources(model: RelationalModel, *, base_package: str = "com.modelia.generated") -> GeneratedSources: ...
```

## Templates (verbatim, `emit/templates/`)

`build.gradle.j2` — reproduces the spike oracle; `{{ }}` only, no `{%`, no `{#`:

```groovy
plugins {
    id 'java'
    id 'org.springframework.boot' version '{{ spring_boot_version }}'
}

group = '{{ group }}'
version = '{{ version }}'

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of({{ java_version }})
    }
}

repositories {
    mavenCentral()
}

dependencies {
    implementation platform(org.springframework.boot.gradle.plugin.SpringBootPlugin.BOM_COORDINATES)
    implementation 'org.springframework.boot:spring-boot-starter-webmvc'
    implementation 'org.springframework.boot:spring-boot-starter-data-jpa'
    implementation 'org.springframework.boot:spring-boot-starter-validation'
    runtimeOnly 'org.postgresql:postgresql'
}
```

`settings.gradle.j2` — one static line, rendered with no context (DD66):

```groovy
rootProject.name = 'generated-backend'
```

`Application.java.j2`:

```java
package {{ package }};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class {{ class_name }} {

    public static void main(String[] args) {
        SpringApplication.run({{ class_name }}.class, args);
    }
}
```

Each file ends with exactly one `\n`. No adjacent `{{`/`{%`/`{#` sequence is producible by
Groovy braces or Java generics here, so no delimiter override and no `{% raw %}` is needed.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/spring_generator/emit/versions.py` | Create | DD62 pinned constants |
| `backend/apps/spring_generator/emit/scaffold_context.py` | Create | DD63 frozen contexts + builders |
| `backend/apps/spring_generator/emit/templates/build.gradle.j2` | Create | DD64/DD65 |
| `backend/apps/spring_generator/emit/templates/settings.gradle.j2` | Create | DD66 |
| `backend/apps/spring_generator/emit/templates/Application.java.j2` | Create | DD64/DD67 |
| `backend/apps/spring_generator/emit/renderer.py` | Modify | DD61 two new functions; existing ones byte-identical |
| `backend/apps/spring_generator/tests/test_project_scaffold_sources.py` | Create | Scaffold contract |
| `backend/apps/spring_generator/tests/test_project_sources.py` | Create | Composition + collision |
| `backend/apps/spring_generator/tests/test_determinism.py` | Modify | Add both entry points |
| `backend/apps/spring_generator/tests/test_purity.py` | Modify | Add both entry points |
| `openspec/specs/spring-boot-generation/spec.md` | Modify | Via change delta |
| `docs/ai/{CURRENT_STATE,NEXT_STEPS,HANDOFF_LATEST,DECISIONS_LOG}.md`, `docs/ai/sessions/2026-09-19-*.md` | Modify / Create | See Docs |

`emit/context.py`, `emit/naming.py`, `emit/errors.py`, `emit/javatypes.py`,
`emit/inheritance_context.py`, `domain/sources.py` and all eleven existing templates are
untouched.

## Testing Strategy (Strict TDD — RED first)

| Module | Scenario | Approach |
|---|---|---|
| `test_project_scaffold_sources.py` | Entry point exists; exactly 3 files; exact paths in DD68 order for `base_package="com.example.generated"` | `[f.path for f in sources.files] == [...]` |
| ” | **Exact content** of all three files | Full-string equality against module-level oracle constants transcribed from the spike, not substring checks (the proposal's byte-level mitigation) |
| ” | Versions come from one place | Rendered text built via `.format()` from the imported constants; plus DD72 negative source scan over `emit/**/*.py` (minus `versions.py`) and `emit/templates/*.j2` |
| ” | No hardcoded host/port/URL/credential/absolute path | DD73 forbidden-literal list (explicitly not `postgres`) |
| ” | Excluded artifacts | `.gitignore`, `gradlew`, `gradle/wrapper`, `springdoc`, `io.spring.dependency-management`, `build.gradle.kts` absent from paths and contents |
| ” | LF + trailing newline | `"\r" not in contents`; `contents.endswith("\n")`; `not contents.endswith("\n\n")` |
| ” | Jinja safety | No rendered file contains `{{`, `{%`, `{#`; no `.j2` scaffold source contains `{%` (DD64 invariant) |
| ” | `base_package` validation and propagation | `"Com.Bad"`/`"1bad"`/`""` → `ValueError`; `"org.example.app"` → `group = 'org.example.app'` and `src/main/java/org/example/app/Application.java` |
| ” | Determinism | Two independent calls → equal `GeneratedSources` |
| `test_project_sources.py` | Composition order | `sources.files == generate_model_sources(...).files` tuple followed by `generate_project_scaffold_sources(...).files` (prefix/suffix slice assertions) |
| ” | `generate_model_sources` unchanged | Every model file inside the aggregate is byte-identical to the direct call; the existing inheritance SHA-256 snapshot test and the full 685-test suite stay green unmodified |
| ” | Empty model | `RelationalModel()` → 2 error files, `application.yml`, then the 3 scaffold files |
| ” | Duplicate path rejection | DD71 monkeypatched module-global scaffold generator → `GeneratedSourcePathCollisionError`, `isinstance(..., UngeneratableSourceError)`, `.path`, `.occurrences == 2`, no aggregate bound |
| ” | Helper directly | `_reject_duplicate_generated_paths` over a hand-built tuple with `build.gradle` twice |
| ” | Determinism | Two calls on the same model → equal |
| `test_purity.py` (extend) | No DB, no `validate()`, no `os.getenv`/`os.environ.get`, no `subprocess.*` | Same `patch(...)` style already used for `generate_model_sources`, applied to both new entry points |
| `test_no_concat_guard.py` | Stays green **unmodified** over `versions.py` and `scaffold_context.py` | Already globs `emit/**/*.py` |

No Java compilation, Gradle, Docker, or writer test belongs in this slice.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. The change is pure in-memory text generation; the purity tests
above assert the absence of every such boundary.

## Docs

- `docs/ai/DECISIONS_LOG.md` — new top entry recording DD61–DD74.
- `docs/ai/CURRENT_STATE.md` — `spring_generator` now has six public entry points; §37 item 13
  moves from "Not started" to "slice 1 of 3 done (pure scaffold; nothing compiles yet)".
- `docs/ai/NEXT_STEPS.md` — slice 2 `generated-project-compile-check` and slice 3
  `generated-project-boot-smoke`; plus the **known defect** from `exploration.md`
  (`emit/inheritance_context.py:169` names subclass entities with `pascal_case(class_id)`
  instead of `discriminator_values[class_id]`, so uuid-based class ids raise
  `InvalidJavaIdentifierError`) queued as its own small change.
- `docs/ai/HANDOFF_LATEST.md` — update for this cycle **and correct four stale lines already
  present**: (1) the snapshot pins `743a572`, but `main` is at `c876f79`; (2) "How to resume"
  says "about 670 passed" — it is 685 before this change; (3) the chronological archived-cycle
  list ends at `config-layer` and omits `2026-09-19-spring-boot-whole-model-orchestrator`
  (which the Snapshot section does mention, so the file contradicts itself); (4) the header
  says `DD1–DD50` — the range is `DD1–DD60`.
- `docs/ai/sessions/2026-09-19-agent-spring-boot-project-scaffold.md` — new session note.

## Migration / Rollout

No migration. Purely additive, one PR, well inside the 400-line budget (~120 authored lines of
source + templates, ~200 of tests). Rollback = revert the commit; nothing imports the new
symbols and `generate_model_sources` is untouched.

## Open Questions

- [ ] `Application.java`'s exact body is the one artifact `exploration.md` does not quote
      verbatim (it records only that a hand-written main class built and booted). The two
      load-bearing FQNs — `org.springframework.boot.SpringApplication` and
      `org.springframework.boot.autoconfigure.SpringBootApplication` — are the canonical Boot 4
      shape but are **not** oracle-pinned by the recorded spike output. Apply must transcribe
      the spike's actual file if it is still available; otherwise slice 2's compile gate is the
      first real proof. This is the only unverified claim in the change.
- [ ] `_validate_base_package` raising a bare `ValueError` rather than an
      `UngeneratableSourceError` subclass (DD20) is an inconsistency this slice inherits and
      deliberately does not fix (DD70). Worth its own change later.
