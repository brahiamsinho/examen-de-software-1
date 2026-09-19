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
`generate_project_sources(...)`, §37 item 13 slice 1 of 3). The relational mapper has the archived
`relational-column-ownership` prerequisite: attribute-derived columns carry
`owning_class_id`; non-attribute columns keep `None`.

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
5. **§37 item 13, generated backend compilable — slice 1 of 3 done.**
   `2026-09-19-spring-boot-project-scaffold` added the pure scaffold text
   (`generate_project_scaffold_sources`, `generate_project_sources`, versions in
   `emit/versions.py`); nothing compiles Java yet. Remaining, in order:
   - **Slice 2 `generated-project-compile-check`**: a writer
     (`write_sources(sources: GeneratedSources, target_dir)` in its own app, no
     import from `emit/`, re-validating POSIX-relative paths, `newline="\n"`)
     plus an ephemeral runner (`gradle:9.7.1-jdk21`, reading `GRADLE_VERSION`
     and the JDK from `emit/versions.py`) that runs `gradle build` on
     `generate_project_sources(...)` output. Needs new infrastructure (no JVM
     service or CI exists).
   - **Slice 3 `generated-project-boot-smoke`**: boot the compiled app against a
     fresh PostgreSQL and exercise a CRUD endpoint (the slice-0 spike already
     proved this by hand).
   - Also deferred: Gradle wrapper (binary jar, `GeneratedFile.contents` is `str`),
     `.gitignore`, Dockerfile.
6. **§37 items 14–16** — OpenAPI, Postman collection, Domain Manifest.
   Resolve first with the user: §25 says "OpenAPI nativo de Django Ninja" but
   §22 mandates springdoc-openapi in the generated stack.

## Known defect, queued as its own small change

`emit/inheritance_context.py:169` names each subclass entity with
`pascal_case(class_id)` (the UML element id) instead of the UML class name, which
is available as `discriminator_values[class_id]`. Real class ids are uuid4 hex or
UUIDs and 10 of 16 start with a digit, so `generate_model_sources` and
`generate_project_sources` raise `InvalidJavaIdentifierError` on any model whose
inheritance class ids come from `new_id()`. Every inheritance test passes readable
ids (`"vehicle"`, `"car"`, `"truck"`), which is why the suite never caught it. It
also contradicts the archived inheritance spec text. Found in the slice-0 spike
(worked around there with readable ids). It needs its own small SDD change with a
uuid-id regression test; it was deliberately **not** fixed in the scaffold change.

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
