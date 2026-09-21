# Handoff — Latest

- **Newest work (2026-09-21, small direct change, uncommitted):** "Generate backend and leave it running", backend only. `apps.backend_deployments` (POST/GET latest/DELETE under `/api/orgs/{org_slug}/documents/{doc_id}/deployments`) + new `runner/` service (Docker socket holder, builds with Gradle, runs Postgres + JRE per deployment, reverse-proxies `/gen/<id>/...`). Requires `RUNNER_TOKEN` in the root `.env` (already appended locally, git-ignored) and `docker compose up -d --build runner`; then `docker compose up -d backend` and `migrate`. Backend 1337 passed, runner 15 passed; verified with a real deployment (details in `CURRENT_STATE.md`, decision DD168). Frontend button/polling is the next slice. Never run `docker compose down` casually: stopped runner containers are cleaned by the runner's startup sweep.

- **Previous work (2026-09-20, small direct change, uncommitted):** class/attribute names with spaces, accents, dashes or leading digits are normalized in `relational_mapping/mapping/naming.py::snake_case`, so EA-imported models (`Class A`/`Class B`) generate and `gradle build` passes (backend 1325 passed; details in `CURRENT_STATE.md`).

- **Previous work (2026-09-20, small direct change, uncommitted):** EA XMI import/export in `apps.xmi_interop` + `Importar XML` / `Exportar XML` UI (backend 1308 passed, frontend 369 passed; details in `CURRENT_STATE.md`). (The spaced-name generation failure noted here was fixed right after; see the newest entry.)

- **Previous work (2026-09-20, small direct change, uncommitted):** "Descargar backend" button + `apps.generation_export` (`GET /api/orgs/{org_slug}/documents/{doc_id}/generate` returns the deterministic Spring Boot zip of a stored document; backend 1285 passed, frontend 363 passed; details in `CURRENT_STATE.md`).

- **Previous work (2026-09-20, verified PASS WITH WARNINGS 0 critical and archived, uncommitted):** change `crud-restricts-operations` (DD160-DD167, 24/24 tasks, 9.1 closed at archive, Strict TDD, ~570 authored lines, no `size:exception`; slice 1 of 2 of the DD147 debt). The declared table `crud` / `readOnly` now restrict `operations[]` in the Domain Manifest. Files: `apps/relational_mapping/domain/profile.py` (`OPERATION_NAMES`, pure `effective_operations(profile)`), `domain/schema.py` (non-field `Table.effective_operations` property), `apps/domain_manifest/builder/entities.py` (filters `_OPERATIONS` in declared order; `resourcePath` is `null` iff the effective set is empty, computed before suppression so bad names still fail) plus tests in `test_profile.py`, `test_schema.py`, `test_manifest.py` (the old `test_declaring_crud_does_not_filter_the_operations` is inverted to `test_declaring_crud_restricts_the_operations`). `tests/test_builder_decoupling.py` and `builder/profile.py` are unchanged. Backend 1214 -> 1267 passed (`apps/relational_mapping` 170, `apps/domain_manifest` 146); mutations M1-M5 killed (M3 needed one extra direct `_operations` order test because it is equivalent through `build_entity`). **Transient divergence (DD166):** until slice 2 `spring-generator-crud-restriction` the generator still serves six endpoints while a restricted model's manifest lists fewer; no committed fixture is affected. Archived to `openspec/changes/archive/2026-09-20-crud-restricts-operations/`. Next: slice 2.

- **Previous work (2026-09-20, committed as `20bf71c`):** change `2026-09-20-generated-spring-api-filtering-search` completed the Spring generator filtering/search slice. The generator now derives searchable filters, sortable allow-lists, and default sort from `Table.profile` / `Column.profile`; emits one `application/<Entity>Specifications.java` for searchable non-inheritance tables; conditionally extends repositories with `JpaSpecificationExecutor`; adds optional Java-field-name controller query params; validates sort with HTTP 400 via generated `IllegalArgumentException` handling; applies default sort only for unsorted `Pageable`; and preserves no-profile / false-unset profile output byte-identically. Evidence: RED focused run failed on missing `build_specification_context`, then focused GREEN `68 passed`; `apps/spring_generator` `354 passed`; Docker backend `1214 passed`; frontend strict command `55 files / 351 tests` passed. Size exception accepted; no commit or push. `.pi/` remains excluded.

- **Previous work (2026-09-20, verified, archived and committed as `4b923aa`):** change `2026-09-20-uml-generation-profile-panel` completed the frontend slice for generation profile authoring. New files: `frontend/src/components/workspace/GenerationProfilePanel.tsx` and its RTL test. Modified: `frontend/src/lib/uml_documents.ts`, `frontend/src/lib/__tests__/uml_documents.test.ts`, and `frontend/src/app/(app)/documents/[docId]/page.tsx`. The panel uses existing native `Select` controls for tri-state values, reads malformed metadata defensively as unset, sends declared-only `SetGenerationProfile` payloads via `submitCommand`, clears with `profile: null`, and maps `crud` true/false to all operations/empty array. Evidence: `cd frontend && npm test` -> 55 files / 351 tests passed; focused run -> 39 tests passed; `cd frontend && npm run lint` passed. Archive composed 5 ADDED requirements into `openspec/specs/web-uml-canvas/spec.md` and moved the change to `openspec/changes/archive/2026-09-20-2026-09-20-uml-generation-profile-panel/`. No backend, persistence, canvas, WebSocket, Flutter/mobile, or `defaultSort` changes. Do not commit `.pi/`.

Updated 2026-09-20. Read this first, then `CURRENT_STATE.md` (long, per-area
detail), `NEXT_STEPS.md`, and `DECISIONS_LOG.md` (newest entry at the top,
DD1–DD167; DD160–DD167 are the archived crud-restricts-operations change; DD75–DD86 are the archived compile-check cycle, DD87–DD91 the applied
subclass-naming fix, DD103–DD107 the archived springdoc-openapi cycle, DD108–DD120 the archived
Postman-collection change, DD121–DD131 the archived Domain Manifest change, DD132–DD141 the archived relational-generation-metadata change, DD142–DD150 the archived manifest-generation-profile change, DD151–DD159 the archived uml-generation-profile-authoring change (committed 07fb611)). Older per-cycle detail lives
in `openspec/changes/archive/` (proposal, design, tasks, verify-report) and
`openspec/specs/` (25 merged capability specs, including new domain-manifest-export and generation-profile).

## Snapshot

- **Previous dependency work (2026-09-20, verified, archived and committed as `07fb611`):** change `uml-generation-profile-authoring`
  (DD151-DD159, entry of `DECISIONS_LOG.md`), 31/31 tasks, Strict TDD, backend slice 1 of 2. The generation profile is
  authorable through the command API. New command `SetGenerationProfile(element_id, profile | None)` (tenth command type;
  `commands.py`, `schemas.py` `SetGenerationProfileIn`, `dispatcher.py` last `_HANDLERS` entry) and handler
  `uml_commands/handlers/generation_profile.py` (`set_generation_profile`, `prune_generation_metadata`; owns only the `"profile"` key,
  prunes empties; `handlers/classes.py` and `handlers/attributes.py` cascade the prune, DD158 incl. a foreign root `defaultSort`).
  `uml_documents/services.py` validates inside the row lock (level inferred from the model, unknown id 422 even on clear,
  parser messages verbatim, `defaultSort` resolved per DD157). **Guard exception (DD154, the first in this codebase):**
  `uml_documents` may import exactly `apps.relational_mapping.mapping.profile_parser` (exact-match allowance in
  `test_import_boundary.py`; other `apps.relational_mapping.*` targets fail); `uml_commands` guard untouched. Spec requirements were
  rescoped (persisted-layout scenario now means codec round trip plus `map_to_relational`). Results: backend 1107 -> 1184 passed,
  `apps/uml_commands` 86, `apps/uml_documents` 134; mutants M1-M10, S1-S3 killed and reverted. ~1208 authored lines, `size:exception` accepted.
  Accepted warnings: M8 "outside the lock" is an equivalent mutant single-threaded (only "after apply" is testable); tests 2.9, 3.1, 3.2
  are characterization tests proven by mutation. The follow-up frontend panel change is now verified and archived as `2026-09-20-uml-generation-profile-panel`.

- **Previous work (2026-09-20, verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `cdae44c`):** change `manifest-generation-profile`
  (DD142-DD150), 24/24 tasks (11.4 closed at archive), Strict TDD. The Domain Manifest now emits
  the declared generation profile: entity `profile` (`auditable`, `readOnly`, `crud`, `defaultSort`) and
  attribute `profile` (`searchable`, `sortable`, `readOnly`), each present only when declared (omitted, never
  `null`). `schemaVersion` stays 1; `entity`, `aliases`, `generation_metadata` are never emitted. Supersedes DD131.
  Files: new `builder/profile.py`, `builder/errors.py` (`ManifestError` moved, re-exported), `tests/test_profile.py`;
  modified `builder/attributes.py` (`attribute_name`), `builder/entities.py` (`_resolver`, `defaultSort` resolution),
  `builder/manifest.py`; tests `test_manifest.py`, `test_attributes.py`, `test_profile_output_neutral.py` (retargeted).
  Results: `apps/domain_manifest` 88 -> 125 passed, full backend 1070 -> 1107 passed; sample tripwires and
  `test_builder_decoupling.py` unedited and green; mutation checks M1-M10 all caught except M3 (equivalent mutant).
  Tech debt (DD147): `crud` does not filter `operations[]`. Deferred: `entity`, `aliases`, authoring path.
  ~419 authored lines, no `size:exception` needed. Accepted warnings: M3 equivalent mutant (redundant `profile is None` guard); task 11.4 closed at archive;
  `EXCLUDED_KEYS` equality not asserted explicitly; the 'foreign id' scenario is covered by an id matching no column.
  Delta merged into `openspec/specs/domain-manifest-export/spec.md` (now 15 requirements; `Declared-Facts-Only Exclusion` replaced by `Declared-Facts-Only Emission`);
  archived to `openspec/changes/archive/2026-09-20-manifest-generation-profile/`.

- **Previous work (2026-09-20, verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `284881e`):** change
  `relational-generation-metadata` (DD132-DD141), 34/34 tasks.
  Files: new `relational_mapping/domain/profile.py`, `mapping/profile_parser.py`; modified
  `domain/schema.py` (`Column.profile`, `Table.profile`), `mapping/errors.py`, `mapping/mapper.py`
  (`_collect_profiles` + wiring); new tests `test_profile.py`, `test_profile_parser.py`,
  `test_map_profiles.py`, plus edits to `test_schema.py` / `test_determinism.py`, and two
  output-neutrality tests (`generation_runner/tests/`, `domain_manifest/tests/`).
  Results: `apps/relational_mapping` 138 passed, `apps/domain_manifest` 88 passed, full backend 1070 passed (was 987), 41-file
  oracle, inheritance sha256 goldens and manifest tests unchanged. Seven mutation checks each
  turned tests red and were reverted. Deferred: `required`/`unique`, `entity: false` semantics,
  `defaultSort` resolution, and the authoring path. Authored size ~960 lines accepted as `size:exception`. Accepted warnings: `Table`/`RelationalModel` already unhashable (spec amended); manifest half of the neutrality test lives in `apps/domain_manifest/tests`; `InvalidGenerationProfileError` not imported in `mapper.py` (design wiring table lists it, not needed); three tests pass by construction (protected by mutation checks). Delta specs `generation-profile` (new) and `relational-mapping` (modified) merged into main specs; archived to `openspec/changes/archive/2026-09-20-relational-generation-metadata/`. Its follow-up (manifest emission of the profile) is the `manifest-generation-profile` change above.

- **Previous work (2026-09-20, committed as `d2069a5`; archived; 31/31 tasks, verified PASS WITH WARNINGS; §37 item 16):**
  change `generated-project-domain-manifest` (DD121-DD131). Touched: new app
  `backend/apps/domain_manifest/` (pure `builder/`, `serialize.py`, `cli.py`, 87 tests),
  `backend/config/settings.py` (INSTALLED_APPS), `docker-compose.yml` (`generate-manifest`),
  `scripts/verify-generated-project.sh` (fourth step). Gate green (exit 0,
  `docs/domain-manifest.json` 12496 bytes: 6 entities, 5 resources, `vehicle` resourcePath null);
  negative check exit 1 reverted (equal sha1); default compose services unchanged. Tests: backend
  987 (900 + 87). Slice 1 is 811 authored lines: `size:exception` accepted (split-vs-exception is
  asked again at commit time). Follow-up: the mapper must carry `generation_metadata` before
  searchable/sortable/defaultSort/auditable/readOnly/aliases can exist (DD131). Delta specs
  `domain-manifest-export` (new) and `generated-project-verification` (modified) merged into main specs.
  Archived to `openspec/changes/archive/2026-09-20-generated-project-domain-manifest/`. Its follow-ups (mapper carrying `generation_metadata`, then manifest emission) are done in the two changes above.
- **Previous work (2026-09-20, committed as `8bb9fd0`; verified PASS WITH WARNINGS and archived; §37 item 15):**
  change `generated-project-postman-collection` (DD108-DD120). Touched:
  `scripts/boot-smoke.sh` (export to `docs/openapi.json`, exit 8),
  `scripts/verify-generated-project.sh` (third step), `docker-compose.yml`
  (`generate-postman`), `backend/config/settings.py` (INSTALLED_APPS) and the new app
  `backend/apps/postman_export/` (pure `converter/`, `cli.py`, tests, real fixture
  `tests/fixtures/api-docs.json`). Gate green (exit 0; both Postman files written),
  negative A exit 8 and B exit 1 reverted; evidence in the change's `gate-evidence.md`.
  Tests: backend 900 (840 + 60). Postman import into the app was not run. About 1220
  authored lines: `size:exception` recommended. Delta specs
  `postman-collection-export` (new) and `generated-project-verification` (modified)
  merged at archive.
- **Previous work (2026-09-20, committed as `a834ca2`; verified PASS WITH WARNINGS and archived at
  `openspec/changes/archive/2026-09-20-generated-project-openapi-springdoc/`; §37 item 14
  part 1 complete):** change `generated-project-openapi-springdoc` (DD103-DD107).
  Touched: `emit/versions.py`, `emit/scaffold_context.py`, `emit/renderer.py`,
  `emit/templates/build.gradle.j2`, `scripts/boot-smoke.sh`, three test files.
  Gate green (exit 0, `GET /v3/api-docs -> 200`), negative exit 7 reverted,
  evidence in the change's `gate-evidence.md`. Tests: backend 840, `apps/spring_generator` 325,
  `apps/generation_runner` 68. OpenAPI now served by the generated backend via springdoc.
  Never commit `.pi/`.
- **Earlier work (committed as `765dbd5`; verified PASS WITH WARNINGS and archived at
  `openspec/changes/archive/2026-09-19-generated-project-boot-smoke/`; §37 item 13
  complete):** change `generated-project-boot-smoke` (18/18 tasks,
  `size:exception` accepted). Adds `gen-db` and `jvm-boot-smoke` to `docker-compose.yml` (profile
  `jvm-verify`, no ports), `scripts/boot-smoke.sh`, a second step plus an EXIT
  cleanup trap in `scripts/verify-generated-project.sh`, and the Docker-free
  contract test `backend/apps/generation_runner/tests/test_boot_smoke_contract.py`
  (DD92-DD102). Gate: `bash scripts/verify-generated-project.sh` -> exit 0
  (`BUILD SUCCESSFUL`, ready in 4-5s, 201/200/204/404); negative
  `GEN_DB_PASSWORD=wrong bash ...` -> exit 4. Tests: backend 836,
  `apps/generation_runner` 67. Deferred: Gradle
  wrapper, Postman/Domain Manifest, frontend/mobile
  generation, actuator/Flyway, names-with-spaces limitation.
- Code state: the last commit is `20bf71c` (`feat(spring-generator): add filtering/search, sort validation and defaultSort`); HEAD may have moved since these docs were last edited, so run `git log --oneline -3`.
  `uml-generation-profile-authoring` (07fb611), `uml-generation-profile-panel` (4b923aa) and `generated-spring-api-filtering-search` (20bf71c) are committed and archived.
  **Uncommitted work in the tree**: the `crud-restricts-operations` change (verified PASS WITH WARNINGS, 0 critical, and archived; `apps/relational_mapping`, `apps/domain_manifest`, its openspec change folder and `docs/ai`). The untracked `.pi/`
  folder is deliberately never committed; run `git status` to check.
- Last archived OpenSpec change: `crud-restricts-operations`
  (24/24 tasks, verified PASS WITH WARNINGS, 0 CRITICAL, archived at
  `openspec/changes/archive/2026-09-20-crud-restricts-operations/`).
  34 cycles are archived; the last one is
  `2026-09-20-crud-restricts-operations`.
- Subclass-naming fix (DD87-DD91): `emit/inheritance_context.py:169` now uses
  `pascal_case(table.discriminator_values[class_id])`; fixtures use class-name
  discriminator values; `samples/sample_model.py` uses frozen uuid4-hex class ids.
  Gate evidence (re-run on the uuid sample): `bash scripts/verify-generated-project.sh`
  gave `BUILD SUCCESSFUL in 41s`, exit 0, image `gradle:9.7.1-jdk21`; the first run
  failed with a transient Maven Central TLS handshake error (exit 1) and the
  immediate rerun passed. Evidence file:
  `openspec/changes/spring-generator-inheritance-subclass-naming/gate-evidence.md`.
- Compile gate (manual, compose-based, NOT in pytest, DD85): from the repo root in
  Git Bash run `bash scripts/verify-generated-project.sh`. It generates the sample
  project into the named volume `generated_project` and runs `gradle build` in
  `gradle:9.7.1-jdk21` (tag derived from `emit/versions.py`). Recorded result:
  `BUILD SUCCESSFUL in 50s`, exit 0, 41 files; evidence file
  `openspec/changes/archive/2026-09-19-generated-project-compile-check/gate-evidence.md`. It leaves
  one stopped `generate-project` container and the named volume by design.
- Tests: backend 828 (`docker compose exec -T backend pytest -q`; 822 before the subclass-naming change), Spring generator 322 (`docker compose exec -T backend pytest apps/spring_generator -q`; 317 + 5), `apps/generation_runner` 59 (58 - 2 + 3), frontend
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
| 13 Generated backend compilable | **Done** — all 3 slices archived (scaffold text, compile check, boot-smoke; manual gate evidence `BUILD SUCCESSFUL`) |
| 14 OpenAPI | **Done (part 1)** — generated backend serves `/v3/api-docs` via springdoc 3.1.1 (verified, committed `a834ca2`) |
| 15 Postman | **Done** — `apps.postman_export` + third gate step (DD108-DD120); verified and committed `8bb9fd0` |
| 16 Domain Manifest | **Done (verified and archived; core committed as `d2069a5`)** — `apps.domain_manifest` + fourth gate step (DD121-DD131); the mapper carries the generation profile (`relational-generation-metadata`, DD132-DD141, committed as `284881e`) and the manifest emits it (`manifest-generation-profile`, DD142-DD150, verified and archived, committed as `cdae44c`) |
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
2026-09-19-spring-boot-project-scaffold,
2026-09-19-generated-project-compile-check.

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
    hierarchy order; subclass Java names use
    `pascal_case(discriminator_values[class_id])` (the UML class name), the
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
    compiled (`gradle build`, BUILD SUCCESSFUL) and booted for real.
- `backend/apps/generation_runner/` (slice 2): `writer/`
  (`write_sources(sources, target_dir)`, pure, never imports `spring_generator`,
  enforced by `tests/test_writer_decoupling.py`), `domain/` (typed errors, Protocols),
  `cli.py` (`python -m apps.generation_runner.cli --target <dir>`, no
  `django.setup()`), `runner_image.py`, `samples/sample_model.py` (frozen
  uuid4-hex class ids since the subclass-naming fix; DD81's readable-id workaround is superseded by DD90). The compile gate that
  uses it is `scripts/verify-generated-project.sh` plus the profile-gated
  `generate-project` / `jvm-verify` compose services (see Snapshot). Slice 3
  (boot smoke) is not started.
  - Rejected with typed errors (`UngeneratableSourceError` family): non-UUID
    or composite PK, composite FK, malformed/unsupported discriminator-backed
    inheritance metadata, enum column without a type name, illegal identifiers/
    resource paths.
- The generator itself stays **text only**. Compilation happens only in the
  manual compose gate (an ephemeral `gradle:9.7.1-jdk21` container); the backend
  image has no JVM and nothing compiles Java inside `pytest`.

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
- Subclass Java class names come from the UML class name (`discriminator_values`),
  never from the element id; a discriminator value that is not a legal Java
  identifier (e.g. `"Sports Car"`) is rejected with `InvalidJavaIdentifierError`
  (pinned limitation, out of scope to sanitize). Never edit
  `test_inheritance_backward_compatibility.py` (SHA-256 snapshot).
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
   subclass repositories and generation_metadata-based manifest fields remain out of scope for future cycles
   (Java compilation, OpenAPI and Postman exist at the generated-project level).
2. Filtering/search: waits for §33 generation metadata (`searchable`,
   `sortable`, …), which the schema does not have.
3. Relation-navigation sub-endpoints (`GET /parent/{id}/children`) and
   bidirectional `@OneToMany`: whole-`RelationalModel` orchestration now exists,
   but these relationship-navigation behaviors still need their own design and
   generation rules.
4. Broader generated backend config remains deferred: the YAML singleton exists, but Java `config/` classes, profiles, runtime scaffolding, and orchestration do not.
5. Item 16 (Domain Manifest) is done and archived (profile emission included); items 13, 14 and 15 are done (see the table above).
   The §25 vs §22 contradiction was resolved in favor of springdoc-openapi (see
   `DECISIONS_LOG.md`, 2026-09-19).

## How to resume

1. `docker compose up -d`, then `docker compose exec -T backend pytest -q`
   should report 987 passed (900 before the Domain Manifest change) before you change
   anything.
2. Work through SDD (hybrid store: `openspec/` + Engram, Strict TDD):
   explore → propose → spec/design → tasks → apply → verify → archive →
   commit. Ask the user the open questions before `sdd-propose`, one
   question at a time.
3. After each sub-agent phase, re-run the test suite yourself instead of
   trusting its self-report.
4. After finishing, update `CURRENT_STATE.md`, `NEXT_STEPS.md` and this
   file, and add a note under `docs/ai/sessions/`.
