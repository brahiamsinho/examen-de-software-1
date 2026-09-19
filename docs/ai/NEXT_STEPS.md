# Next Steps

Updated 2026-09-19. For the full picture read `HANDOFF_LATEST.md` first. Spec
section 37 (`product-04-next-django.md`) fixes the implementation order; items
1–6, 8, 9 and 11 are done and archived, item 12 is partial.

## Where we are

The Spring Boot generator (§37 item 12) has five archived generator slices, all
text-only: `spring-boot-generator-core` (entity + repository),
`spring-boot-generator-relationships-enums` (FK relationships, enum fields,
standalone enum source), `spring-boot-generator-application-api-layer` (DTOs,
service, REST controller, shared error handling),
`2026-09-19-spring-boot-generator-inheritance` (discriminator-backed Single
Table domain classes plus one root repository only), and
`2026-09-19-spring-boot-generator-config-layer` (pure project-singleton
`src/main/resources/application.yml` only, six required no-default placeholders
including `JPA_DDL_AUTO`, no dialect/platform, no Java `config/` classes and no
whole-model orchestrator). The relational mapper has the archived
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
3. **Whole-model orchestrator** — a function that walks a `RelationalModel`,
   calls the per-table/per-enum generators, calls the shared-error generator
   exactly once, and detects cross-artifact Java class-name collisions (e.g. a
   table `order` and an enum `order`). It also unlocks bidirectional
   `@OneToMany` and relation-navigation sub-endpoints, which need the whole
   model.
4. **Filtering/search** — blocked until the relational schema carries §33
   generation metadata (`searchable`, `sortable`, `crud`, `readOnly`, …).
5. **§37 item 13, generated backend compilable** — nothing compiles Java today.
   Agreed direction: an ephemeral container with a JVM/Gradle image plus a fresh
   PostgreSQL. It needs new infrastructure (no JVM service or CI exists) and is
   its own cycle.
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
