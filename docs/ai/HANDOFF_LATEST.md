# Handoff — Latest

Updated 2026-09-19. Read this first, then `CURRENT_STATE.md` (long, per-area
detail), `NEXT_STEPS.md`, and `DECISIONS_LOG.md` (newest entry at the top,
DD1–DD74 for the last four generator cycles). Older per-cycle detail lives
in `openspec/changes/archive/` (proposal, design, tasks, verify-report) and
`openspec/specs/` (21 merged capability specs).

## Snapshot

- Code state: everything up to `c876f79` is committed. The
  `2026-09-19-spring-boot-project-scaffold` change is verified and archived, and
  its commit is the one that follows `c876f79` on `main` (check `git log`). The
  untracked `.pi/` folder is deliberately never committed; run `git status` to
  check.
- Active OpenSpec change: none. 25 cycles are archived; the last one is
  `2026-09-19-spring-boot-project-scaffold`.
- Tests: backend 764 (`docker compose exec -T backend pytest -q`; it was 685 before the scaffold change), Spring generator 317 (`docker compose exec -T backend pytest apps/spring_generator/tests -q`; it was 238 before), frontend
  335 (`cd frontend && npm test`, last run during the config-layer verify; the
  orchestrator and scaffold slices changed no frontend code).
- If Docker is down on Windows: start Docker Desktop and poll `docker info`
  until it answers, then `docker compose up -d`.

## What stage the project is in

The exam spec is `product-04-next-django.md`; section 37 gives the
implementation order. Status against it:

| §37 item | Status |
|---|---|
| 1–3 CanonicalUmlModel, ProjectDocument/DiagramLayout, validation engine | Done |
| 4 UmlCommand + Command Bus | Done |
| 5 Canvas (Cytoscape) | Done (incl. remove UI, relationship kinds, operations compartment) |
| 6 Persistence (Django ORM) | Done |
| 7 Undo/Redo | No dedicated archived cycle; not verified as implemented |
| 8 Auth + ownership (multi-tenant) | Done |
| 9 Realtime (Channels/Daphne) | Done (WebSocket sync + per-node claim locking) |
| 10 Presence | No dedicated archived cycle; not verified as implemented |
| 11 UML → RelationalModel | Done |
| 12 Spring Boot backend generator | **Partial** — `domain/`, `persistence/`, `application/`, `api/`, `errors/` for non-inheritance tables and domain + root repository for discriminator-backed Single Table tables; see below |
| 13 Generated backend compilable | **Slice 1 of 3 done** (pure scaffold text: `build.gradle`, `settings.gradle`, `Application.java`); slice 2 compile-check and slice 3 boot-smoke not started, nothing compiles Java yet |
| 14 OpenAPI, 15 Postman, 16 Domain Manifest | Not started |
| 17–26 frontend generator, assistant, voice, Android, XMI, image→UML | Not started |

## Archived cycles (chronological)

2026-09-05 canonical-uml-model · 09-06 multi-tenant-identity,
tenant-aware-registration-login, frontend-auth-integration,
ssr-protected-routes · 09-10 organization-member-management · 09-11
email-verification-password-reset · 09-12 uml-command-bus,
uml-document-persistence, uml-canvas-ui · 09-13 uml-canvas-remove-ui,
uml-document-list · 09-14 realtime-uml-collaboration,
uml-relationship-kinds · 09-15 uml-node-position-sync · 09-16
uml-class-operations · 09-18 uml-relational-mapping,
spring-boot-generator-core, spring-boot-generator-relationships-enums,
spring-boot-generator-application-api-layer, relational-column-ownership,
2026-09-19-spring-boot-generator-inheritance,
2026-09-19-spring-boot-generator-config-layer,
2026-09-19-spring-boot-whole-model-orchestrator,
2026-09-19-spring-boot-project-scaffold.

Fixes done outside an SDD cycle (each logged in `DECISIONS_LOG.md`):
- `f605592` client-side lock self-expiry (a lock whose release message was
  lost stayed "locked" forever because Redis TTL expiry broadcasts nothing).
- `b00141e` `broadcast_document` now pre-serializes through `DocumentOut`
  before `group_send`: channels_redis uses msgpack, which cannot encode
  `UUID`/`datetime`. The in-memory test channel layer hides this class of
  bug; only the real Redis layer exposes it.
- Git history was rewritten and force-pushed once to strip
  `Co-Authored-By`/`Claude-Session` trailers (the user does not want AI
  attribution on the repo).

## The generation pipeline (what exists today)

```
CanonicalUmlModel --map_to_relational()--> RelationalModel --spring_generator--> Java source text
 (uml_modeling)     (relational_mapping)    Table/Column/FK/    (spring_generator)   (in memory only)
                                            EnumType
```

- `backend/apps/relational_mapping/`: pure, DB-free mapper. Single Table
  inheritance with a `class_type` discriminator, synthetic UUID PK on every
  table, native PG ENUM, composition = `NOT NULL` + `ON DELETE CASCADE`,
  N:M = join table. Attribute-derived `Column` values now carry both
  `source_element_id` (the UML attribute) and `owning_class_id` (the UML class
  that owns that attribute); synthetic id, discriminator, FK and join-table
  columns keep `owning_class_id = None`. Validation rule
  `MULTI_PARENT_GENERALIZATION` rejects multi-parent generalization (Single
  Table needs a tree).
- `backend/apps/spring_generator/` (pure, filesystem-free, deterministic):
  - `generate_table_sources(table, *, base_package)` → for non-discriminator
    tables, 6 files under `src/main/java/<pkg>/`: `domain/<E>.java` (JPA
    entity), `persistence/<E>Repository.java`,
    `application/dto/<E>RequestDto.java`,
    `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`,
    `api/<E>Controller.java`. FK columns become `@ManyToOne`/`@OneToOne` +
    `@JoinColumn` on the entity but flat `UUID` fields on the DTOs. For
    supported discriminator-backed Single Table tables, the same entry point
    emits only root/subclass domain entities plus the root repository in
    hierarchy order; subclass Java names use `pascal_case(class_id)`, the
    root remains concrete, and the discriminator is metadata only.
  - `generate_enum_source(enum_type, *, base_package)` → standalone Java enum.
  - `generate_shared_error_sources(*, base_package)` → `errors/
    ResourceNotFoundException.java` + `errors/GlobalExceptionHandler.java`
    (one set per generated project, deliberately not per table).
  - `generate_project_config_sources()` → exactly one in-memory resource at
    `src/main/resources/application.yml`, with only the six required no-default
    placeholders (`SPRING_APPLICATION_NAME`, `SPRING_DATASOURCE_URL`,
    `SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, `JPA_DDL_AUTO`,
    `SERVER_PORT`). It has no table/model inputs, no filesystem effects, no
    environment reads, no dialect/platform setting, and no Java `config/` layer.
  - `generate_model_sources(model, *, base_package)` is now archived: it
    aggregates table files, enum files, shared errors, and project config in
    order, and raises `GeneratedSourcePathCollisionError` on duplicate exact
    output paths before returning any aggregate. Docker verification passed:
    `238/238` Spring generator tests and `685/685` backend tests.
  - `generate_project_scaffold_sources(*, base_package)` (archived) → exactly three files in fixed order: `build.gradle`,
    `settings.gradle`, `src/main/java/<pkg>/Application.java` (root package, not
    `config/`). Rendered from three `emit/templates/*.j2` files that contain no
    `{% %}` blocks; every version comes from `emit/versions.py` (Spring Boot
    4.1.1, Java 21, project 0.0.1-SNAPSHOT, Gradle 9.7.1 declared for slice 2).
    `generate_project_sources(model, *, base_package)` = the
    `generate_model_sources` output followed by those three files, with one
    duplicate-path check over the combined tuple. Both are pure and take the same
    validated `base_package`. The scaffold reproduces a slice-0 spike that
    compiled (`gradle build`, BUILD SUCCESSFUL) and booted for real, but nothing
    in the repo compiles it yet (slices 2-3).
  - Rejected with typed errors (`UngeneratableSourceError` family): non-UUID
    or composite PK, composite FK, malformed/unsupported discriminator-backed
    inheritance metadata, enum column without a type name, illegal identifiers/
    resource paths.
- Everything is validated as **text only**. No JVM, no Gradle, no
  compilation anywhere in the repo.

## Conventions you must not break

- `emit/*.py` may not build source text by string concatenation. The LibCST
  guard `tests/test_no_concat_guard.py` bans `+`, `.join`, `%` and
  source-bearing f-strings. Use `.format()` or `re.sub`.
- Jinja `trim_blocks` swallows the newline after any `{% %}` tag, even an
  inline one ending a content line inside a loop. Use inline expressions
  `{{ a if cond else b }}` there (this collapsed enum constants onto one
  line once).
- Frozen dataclasses, deterministic order (`Table.columns` order),
  byte-identical output across calls, typed exceptions.
- Java package boundaries matter: the entity's no-arg constructor is
  `public` because the service lives in another package than the entity.
- `validation/` and `config/` output is still forbidden by the spec.
- Pinned toolchain versions live only in `emit/versions.py`; a test scans
  `emit/**/*.py` and `emit/templates/*.j2` for restated `4.1.1`, `9.7.1` or a
  bare `21`. Do not write them anywhere else.
- Known defect, own small change (see `NEXT_STEPS.md`):
  `emit/inheritance_context.py:169` uses `pascal_case(class_id)` for subclass
  names instead of `discriminator_values[class_id]`, so uuid-based class ids
  raise `InvalidJavaIdentifierError`.
- Triple closed-union touch point for any new UML command: `UmlCommand`
  (Python), `CommandIn` (Pydantic), `UmlCommandIn` (TypeScript).
- The validation registry (`uml_modeling/validation/engine.py` `RULES`,
  now 12 rules) is guarded by a hard-coded count test, and growing it also
  breaks closed-set assertions in `test_diagnostics.py` and
  `test_validation_integration.py`.

## Decisions already made with the user (do not re-ask)

- Generated backends must be externally configurable: no hardcoded
  host/port/URL in templates (they will be deployed to the cloud).
- Generated frontend/mobile (§26) is deferred. The user intends Flutter
  instead of the spec's Next.js PWA + Capacitor (a deliberate deviation),
  but said "that comes later". Note `mobile/` already holds a real Flutter
  app; it is Modelia's own review/consult client against the Django API, not
  a client for generated backends.
- Future direction for item 13: an ephemeral container with JVM/Gradle plus
  a fresh PostgreSQL to compile/run generated code. Nothing built yet.
- UML operations (e.g. `crearUsuario`) do not generate endpoints: per §23 the
  API is derived from structural metadata, not operation names.
- Delivery: for every oversized cycle the user chose "size:exception, single
  PR". Commit and push to `main` after each archived cycle (confirm before
  pushing if unsure).
- No `Co-Authored-By`/AI attribution in commits; conventional commits only.

## Blocked / open

1. **Inheritance API behavior remains deferred.** The domain + root repository
   Single Table slice is applied, but inheritance DTOs, services, controllers,
   subclass repositories, generated Java compilation, OpenAPI, Postman, and
   Domain Manifest behavior remain out of scope for future cycles.
2. Filtering/search: waits for §33 generation metadata (`searchable`,
   `sortable`, …), which the schema does not have.
3. Relation-navigation sub-endpoints (`GET /parent/{id}/children`) and
   bidirectional `@OneToMany`: whole-`RelationalModel` orchestration now exists,
   but these relationship-navigation behaviors still need their own design and
   generation rules.
4. Broader generated backend config remains deferred: the YAML singleton exists, but Java `config/` classes, profiles, runtime scaffolding, and orchestration do not.
5. Item 13 (compile), 14 (OpenAPI), 15 (Postman), 16 (Domain Manifest).
   Spec contradiction to resolve with the user before item 14: §25 says
   "OpenAPI nativo de Django Ninja" but §22 mandates springdoc-openapi for
   the generated backend.

## How to resume

1. `docker compose up -d`, then `docker compose exec -T backend pytest -q`
   should report 764 passed (685 before the scaffold change) before you change
   anything.
2. Work through SDD (hybrid store: `openspec/` + Engram, Strict TDD):
   explore → propose → spec/design → tasks → apply → verify → archive →
   commit. Ask the user the open questions before `sdd-propose`, one
   question at a time.
3. After each sub-agent phase, re-run the test suite yourself instead of
   trusting its self-report.
4. After finishing, update `CURRENT_STATE.md`, `NEXT_STEPS.md` and this
   file, and add a note under `docs/ai/sessions/`.
