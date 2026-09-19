# Proposal: Spring Boot Project Scaffold Generation

## Intent

`generate_model_sources` emits 41 Java/YAML files that no toolchain can build: there is no
`build.gradle`, no `settings.gradle` and no `@SpringBootApplication` class. §37 item 13
("generated backend compilable") cannot start until the generator emits a complete project.
The slice-0 spike confirmed the exact scaffold that builds (`gradle build`, Boot 4.1.1,
Java 21) and boots against Postgres 16. This change makes the generator emit that scaffold
as pure text. Success = the generator output is a self-contained Gradle project.

## Scope

### In Scope

- `generate_project_scaffold_sources(*, base_package)` → exactly 3 files: `build.gradle`,
  `settings.gradle`, `src/main/java/<pkg path>/Application.java`.
- `generate_project_sources(model, *, base_package)` = `generate_model_sources(...)` +
  scaffold, atomically rejecting duplicate paths via the existing
  `GeneratedSourcePathCollisionError`.
- New `emit/versions.py`: single pinned `SPRING_BOOT_VERSION` / `JAVA_VERSION` source.
- Spec delta on `spring-boot-generation`.

### Out of Scope

Disk writer; Docker/compose/CI; Gradle invocation; running or booting anything; Gradle
wrapper (binary, `GeneratedFile.contents` is `str` — generated projects require system
Gradle 8.14+/9.x); springdoc/OpenAPI (Boot 4.1 + Jackson 3 unproven); Postman; Domain
Manifest; DDL emitter; sanitizing colliding Java simple names or SQL reserved words; any
frontend/mobile generation. No `.gitignore` (VCS hygiene, not compilation; keeps the
path-layout delta to one root-package Java file). Slices 2–3 and their infrastructure
decisions are separate changes.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `spring-boot-generation`: ADD "Project Scaffold Generation"; MODIFY "Package and File
  Path Layout" (allow root-package `Application.java` + root build files), "Generator
  Purity" (cover the scaffold entry points), "Whole-Model Duplicate Path Rejection"
  (extend to `generate_project_sources`), "Existing Generator Contracts Are Preserved"
  (scope its Gradle-artifact ban to `generate_model_sources`).

## Approach

Two new pure functions in `emit/renderer.py`, following existing conventions: Jinja2
templates with `StrictUndefined`, `.format()`/`re.sub` only (LibCST no-concat guard),
reused `_validate_base_package` and `package_path`, frozen `GeneratedSources` output,
typed errors under `UngeneratableSourceError`. `generate_project_sources` composes
`generate_model_sources` + scaffold and reuses `_reject_duplicate_generated_paths`.
`generate_model_sources` stays byte-identical — the scaffold is a new entry point, never a
whole-model addition. Templates mirror the spike oracle: `java` +
`org.springframework.boot` 4.1.1 plugins, `SpringBootPlugin.BOM_COORDINATES` platform,
`mavenCentral()`, toolchain 21, starters `webmvc`/`data-jpa`/`validation`, `runtimeOnly`
postgresql. `group = base_package`, `rootProject.name = 'generated-backend'`,
`version = '0.0.1-SNAPSHOT'`. Strict TDD: RED tests first.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/spring_generator/emit/renderer.py` | Modified | Two new public functions; existing ones untouched |
| `backend/apps/spring_generator/emit/versions.py` | New | Pinned Boot/Java/Gradle constants |
| `backend/apps/spring_generator/emit/templates/build.gradle.j2` | New | Build script template |
| `backend/apps/spring_generator/emit/templates/settings.gradle.j2` | New | `rootProject.name` |
| `backend/apps/spring_generator/emit/templates/Application.java.j2` | New | `@SpringBootApplication` main class |
| `backend/apps/spring_generator/tests/test_project_scaffold_sources.py` | New | Paths, content, determinism, purity, no hardcoded host/port/URL/credentials |
| `backend/apps/spring_generator/tests/test_project_sources.py` | New | Composition order, collision rejection, `generate_model_sources` byte-identity |
| `openspec/specs/spring-boot-generation/spec.md` | Modified | Via change delta |
| `docs/ai/CURRENT_STATE.md`, `DECISIONS_LOG.md`, `HANDOFF_LATEST.md`, `NEXT_STEPS.md` | Modified | Project convention |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Boot 4.x moves fast; a version bump silently breaks generated projects | Med | Versions pinned in one module; bump is a deliberate, reviewable change re-verified by slices 2–3 |
| No wrapper → generated project needs a system Gradle | High (by design) | Documented; slice 2 supplies `gradle:9.7.1-jdk21` |
| `build.gradle` templates are untestable for compilation in this slice | High | Byte-level assertions against the spike oracle; real proof deferred to slice 2 |
| Scaffold/model path collision is not reachable today (model Java lives under six layer dirs, scaffold at the root) | Low | Keep the check as a structural invariant; test it with an injected duplicate, not a UML class |
| Simple-name and SQL-reserved-word collisions in real user models | Med | Accepted debt, unchanged by this slice |

### Follow-ups (separate changes, not fixed here)

- **KNOWN DEFECT**: `emit/inheritance_context.py:169` names subclass entities with
  `pascal_case(class_id)` (UML element id) instead of the class name. Real uuid-based ids
  raise `InvalidJavaIdentifierError`; the correct name is
  `discriminator_values[class_id]`. Every inheritance test uses readable ids, so the suite
  never caught it. Needs its own small change (it also contradicts the archived
  inheritance spec text) and is independent of the scaffold.
- Slice 2 `generated-project-compile-check`, slice 3 `generated-project-boot-smoke`.

## Rollback Plan

Purely additive. Revert the change commit: delete `emit/versions.py`, the three templates,
the two test modules and the two new functions in `renderer.py`; revert the spec delta.
Nothing else imports them and `generate_model_sources` is untouched, so every existing
caller and all 685 tests are unaffected. No data, schema or infrastructure migration.

## Dependencies

- Slice-0 spike results (recorded in `exploration.md`) as the template oracle.
- Existing `emit/renderer.py` helpers (`_validate_base_package`, `package_path`,
  `_reject_duplicate_generated_paths`) and `domain/sources.py`.
- Jinja2 (already installed). No new runtime dependency.
- Confirmed decisions: no wrapper, no springdoc, Groovy DSL, pinned Boot 4.1.1 / Gradle 9.7.1.

## Success Criteria

- [ ] `generate_project_scaffold_sources(base_package=...)` returns exactly the three
      scaffold files, byte-identical across invocations.
- [ ] `generate_project_sources(model, ...)` returns the model aggregate followed by the
      scaffold, with no duplicate path.
- [ ] `generate_model_sources` output is byte-identical to `main` for the same input.
- [ ] Generated `build.gradle`/`settings.gradle`/`Application.java` contain no hardcoded
      host, port, URL, credential or absolute path.
- [ ] Boot/Java/Gradle versions appear in `emit/versions.py` only.
- [ ] Duplicate scaffold/model path raises `GeneratedSourcePathCollisionError` with no
      partial `GeneratedSources`.
- [ ] Purity test passes: no filesystem, env, subprocess, network, Gradle or Docker access.
- [ ] Full backend suite green; new tests written RED-first (strict TDD).
- [ ] Diff stays under the 800-line review budget (single PR).
