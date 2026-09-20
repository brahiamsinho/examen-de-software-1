# Next Steps

Updated 2026-09-19. For the full picture read `HANDOFF_LATEST.md` first. Spec
section 37 (`product-04-next-django.md`) fixes the implementation order; items
1–6, 8, 9 and 11 are done and archived, item 12 is partial.

## Where we are

The Spring Boot generator (§37 item 12) has seven archived generator slices, all
text-only: `spring-boot-generator-core` (entity + repository),
`spring-boot-generator-relationships-enums` (FK relationships, enum fields,
standalone enum source), `spring-boot-generator-application-api-layer` (DTOs,
service, REST controller, shared error handling),
`2026-09-19-spring-boot-generator-inheritance` (discriminator-backed Single
Table domain classes plus one root repository only), and
`2026-09-19-spring-boot-generator-config-layer` (pure project-singleton
`src/main/resources/application.yml` only, six required no-default placeholders
including `JPA_DDL_AUTO`, no dialect/platform, no Java `config/` classes), and
`2026-09-19-spring-boot-whole-model-orchestrator` (pure in-memory
`generate_model_sources(...)` aggregation with exact duplicate-path rejection),
plus the archived `2026-09-19-spring-boot-project-scaffold` (pure
`build.gradle`/`settings.gradle`/`Application.java` scaffold and
`generate_project_sources(...)`, §37 item 13 slice 1 of 3). Slice 2
(`generated-project-compile-check`) is verified (PASS WITH WARNINGS) and archived, not yet
committed. The relational mapper has the archived
`relational-column-ownership` prerequisite: attribute-derived columns carry
`owning_class_id`; non-attribute columns keep `None`.

**Update (verified and archived):** the change
`spring-generator-inheritance-subclass-naming` is verified (PASS WITH WARNINGS, 0 CRITICAL) and
archived to `openspec/changes/archive/2026-09-19-spring-generator-inheritance-subclass-naming/`.
It fixes the former subclass-naming defect (`emit/inheritance_context.py:169` now uses
`pascal_case(table.discriminator_values[class_id])`), and the compile-check sample
model uses frozen uuid4-hex class ids. Delta spec is merged into the main
`openspec/specs/spring-boot-generation/spec.md`. Next: commit (never `.pi/`).

## Next candidates, in dependency order

1. **Design inheritance API behavior only if requested.** The archived
   inheritance slice intentionally stops at JPA Single Table domain entities
   plus the root repository. DTOs, services, controllers, subclass repositories,
   Java compilation, OpenAPI, Postman, and Domain Manifest remain future work.
2. **Broader generated backend configuration remains deferred.** The bounded
   `application.yml` singleton now exists with six required no-default
   placeholders only; Java `config/` classes, profiles, Docker/runtime
   scaffolding, and orchestration are still not started.
3. **Relationship navigation and bidirectional generation design** — the now-archived whole-model orchestrator unlocks future bidirectional `@OneToMany` and
   relation-navigation sub-endpoints, but those behaviors remain unimplemented
   and need their own SDD cycle.
4. **Filtering/search** — blocked until the relational schema carries §33
   generation metadata (`searchable`, `sortable`, `crud`, `readOnly`, …).
5. **§37 item 13, generated backend compilable — slice 2 of 3 verified and archived
   (uncommitted).** Slice 1 (`2026-09-19-spring-boot-project-scaffold`,
   archived) added the pure scaffold text. Slice 2 `generated-project-compile-check`
   is verified (PASS WITH WARNINGS) and archived: `apps/generation_runner/` (pure `write_sources`
   writer, CLI, sample model, image-tag function) plus the manual compose gate.
   To re-run the gate from the repo root in Git Bash:
   `bash scripts/verify-generated-project.sh` (expect `BUILD SUCCESSFUL`, exit 0).
   It is NOT part of `pytest` (DD85). Immediate next actions, in order:
   - **Commit slice 2** (nothing is committed yet; never commit `.pi/` or `.pi/*`).
   - W2 was fixed: CLI now catches `(GeneratedSourceWriteError, UngeneratableSourceError, ValueError, OSError)`
     with two added test cases in `tests/test_cli.py`; final counts: 822 backend tests (58 in `apps/generation_runner`).
   - **Slice 3 `generated-project-boot-smoke`**: boot the compiled app against a
     fresh PostgreSQL and exercise a CRUD endpoint (the slice-0 spike already
     proved this by hand). Not started.
   - Also deferred: Gradle wrapper (binary jar, `GeneratedFile.contents` is `str`),
     `.gitignore`, Dockerfile.
6. **§37 items 14–16** — OpenAPI, Postman collection, Domain Manifest.
   Resolve first with the user: §25 says "OpenAPI nativo de Django Ninja" but
   §22 mandates springdoc-openapi in the generated stack.

## Explicitly deferred by the user

- Generated frontend/mobile (§26). The user plans Flutter instead of the
  spec's Next.js PWA + Capacitor ("that comes later"). Do not scope it in
  until they raise it.
- The existing `mobile/` Flutter app targets Modelia's own Django API for
  limited review/consult (spec line about mobile). Real screens under
  `mobile/lib/` are still to be built.

## Loose ends (low priority, do not chase unprompted)

- §37 items 7 (Undo/Redo) and 10 (Presence) have no dedicated archived cycle
  and are not verified as implemented.
- The user has not visually confirmed, in a browser, the operations
  compartment on class boxes or the aggregation/composition rendering.
- Cypress (E2E) bootstrap was never started.
- Decisions the generator carries as accepted tech debt: irregular English
  plurals in REST paths (`person` → `persons`), unquoted SQL reserved words in
  `@Table`/`@Column` names, `Page<T>` serialized directly, enum persisted value
  is the SCREAMING_SNAKE constant rather than the model's original label.
