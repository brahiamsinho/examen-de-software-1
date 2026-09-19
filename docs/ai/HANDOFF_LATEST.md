# Handoff — Latest

Updated 2026-09-19. Read this first, then `CURRENT_STATE.md` (long, per-area
detail), `NEXT_STEPS.md`, and `DECISIONS_LOG.md` (newest entry at the top,
DD1–DD50 for the last three generator cycles). Older per-cycle detail lives
in `openspec/changes/archive/` (proposal, design, tasks, verify-report) and
`openspec/specs/` (21 merged capability specs).

## Snapshot

- Code state: branch `main` == `origin/main` at `0aa211a`. The only changes
  possibly not yet committed are this handoff refresh (`docs/ai/*` and the
  new note under `docs/ai/sessions/`); run `git status` to check.
- No active OpenSpec change. 20 archived cycles.
- Tests: backend 631 (`docker compose exec -T backend pytest -q`), frontend
  335 (vitest, last run during the `spring-boot-generator-core` verify; the
  frontend has not changed since).
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
| 12 Spring Boot backend generator | **Partial** — `domain/`, `persistence/`, `application/`, `api/`, `errors/` for one table at a time; see below |
| 13 Generated backend compilable | Not started (nothing compiles Java yet) |
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
spring-boot-generator-application-api-layer.

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
  N:M = join table. Validation rule `MULTI_PARENT_GENERALIZATION` rejects
  multi-parent generalization (Single Table needs a tree).
- `backend/apps/spring_generator/` (pure, filesystem-free, deterministic):
  - `generate_table_sources(table, *, base_package)` → 6 files under
    `src/main/java/<pkg>/`: `domain/<E>.java` (JPA entity),
    `persistence/<E>Repository.java`, `application/dto/<E>RequestDto.java`,
    `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`,
    `api/<E>Controller.java`. FK columns become `@ManyToOne`/`@OneToOne` +
    `@JoinColumn` on the entity but flat `UUID` fields on the DTOs.
  - `generate_enum_source(enum_type, *, base_package)` → standalone Java enum.
  - `generate_shared_error_sources(*, base_package)` → `errors/
    ResourceNotFoundException.java` + `errors/GlobalExceptionHandler.java`
    (one set per generated project, deliberately not per table).
  - Rejected with typed errors (`UngeneratableSourceError` family): non-UUID
    or composite PK, composite FK, discriminator column (inheritance), enum
    column without a type name, illegal identifiers/resource paths.
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

1. **Inheritance generation (needs a user decision).** `Column` in
   `relational_mapping/domain/schema.py` has no owning-UML-class field, so
   which fields belong to which subclass cannot be rebuilt for 2+ sibling
   subclasses. Options: (a) add `owning_class_id` to `Column` (reopens an
   archived cycle), (b) limit to single-subclass trees, (c) defer.
2. Filtering/search: waits for §33 generation metadata (`searchable`,
   `sortable`, …), which the schema does not have.
3. Relation-navigation sub-endpoints (`GET /parent/{id}/children`) and
   bidirectional `@OneToMany`: need whole-`RelationalModel` awareness, and a
   caller that walks the whole model does not exist yet.
4. `config/` layer of the generated backend: not started.
5. Item 13 (compile), 14 (OpenAPI), 15 (Postman), 16 (Domain Manifest).
   Spec contradiction to resolve with the user before item 14: §25 says
   "OpenAPI nativo de Django Ninja" but §22 mandates springdoc-openapi for
   the generated backend.

## How to resume

1. `docker compose up -d`, then `docker compose exec -T backend pytest -q`
   must report 631 passed before you change anything.
2. Work through SDD (hybrid store: `openspec/` + Engram, Strict TDD):
   explore → propose → spec/design → tasks → apply → verify → archive →
   commit. Ask the user the open questions before `sdd-propose`, one
   question at a time.
3. After each sub-agent phase, re-run the test suite yourself instead of
   trusting its self-report.
4. After finishing, update `CURRENT_STATE.md`, `NEXT_STEPS.md` and this
   file, and add a note under `docs/ai/sessions/`.
