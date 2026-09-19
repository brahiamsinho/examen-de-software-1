# Session Note: Spring Boot project scaffold (apply, verify, archive)

Date: 2026-09-19
Change: `2026-09-19-spring-boot-project-scaffold` (§37 item 13, slice 1 of 3)

## Summary

`sdd-apply` implemented all 20 tasks with Strict TDD, single PR (`size:exception`). Two new pure entry points in `backend/apps/spring_generator/emit/renderer.py` turn the 41-file model aggregate into a self-contained Gradle project as text:

- `generate_project_scaffold_sources(*, base_package)` returns `build.gradle`, `settings.gradle` and `src/main/java/<pkg>/Application.java`.
- `generate_project_sources(model, *, base_package)` returns `generate_model_sources(...)` followed by those three files, after one duplicate-path check over the combined tuple.

New files: `emit/versions.py` (the only home of Spring Boot 4.1.1, Java 21, project 0.0.1-SNAPSHOT, Gradle 9.7.1), `emit/scaffold_context.py` (frozen contexts), and three zero-block-tag templates `build.gradle.j2`, `settings.gradle.j2`, `Application.java.j2`. The template bodies equal the slice-0 spike files that compiled and booted for real. Nothing writes, compiles or runs.

## What to know

- Tests: `test_scaffold_context.py` (8), `test_project_scaffold_sources.py` (41), `test_project_sources.py` (18), plus additions to `test_purity.py` (+8) and `test_determinism.py` (+2). After verify, one missing discriminator-table case and two forbidden literals (`127.0.0.1`, `username`) were added. Backend 685 -> 764; Spring generator 238 -> 317.
- Purity is proven with `patch` guards for env, subprocess and sockets plus a write-only filesystem guard (`open` in `w/a/x/+`, `Path.write_text/write_bytes/mkdir`, `os.makedirs/mkdir`). A read guard is impossible because Jinja lazily reads the `.j2` files. A non-vacuity test proves the guard fires.
- The path-collision check is proven by monkeypatching the module-global `renderer.generate_project_scaffold_sources` (DD71), because no real scaffold/model collision is reachable.
- `test_no_concat_guard.py` and the inheritance SHA-256 snapshot pass unmodified, so `generate_model_sources` is byte-identical.

## Deviations from design.md

1. `Application.java.j2` follows the verbatim spike oracle in `exploration.md` (no blank line between the class declaration and `main`). The design's template showed a blank line; the oracle is the file that actually built and booted, so it wins. This also resolves the design's only open question about the exact body.
2. The DD72 negative scan found one real leak the design expected not to exist: a comment `# Java 21 reserved words` in `emit/naming.py`. It was reworded to `# Java reserved words` (comment only, no behavior change).

## Follow-up

- Verified (PASS WITH WARNINGS, no critical) and archived at `openspec/changes/archive/2026-09-19-spring-boot-project-scaffold/`. Also proven outside the suite: the full `generate_project_sources` output for a sample model builds with `gradle build` in `gradle:9.7.1-jdk21` (BUILD SUCCESSFUL, 41 files).
- Next slices: `generated-project-compile-check` (writer + `gradle:9.7.1-jdk21` runner), then `generated-project-boot-smoke`.
- Separate known defect, queued in `NEXT_STEPS.md`: `emit/inheritance_context.py:169` uses `pascal_case(class_id)` for subclass names instead of `discriminator_values[class_id]`, so uuid-based ids raise `InvalidJavaIdentifierError`. Not fixed here.
