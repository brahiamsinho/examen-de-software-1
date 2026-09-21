# Current State

**Update 2026-09-20 (newest; small direct change, no SDD, uncommitted):** Enterprise Architect XMI import/export (mandatory scope, spec §16). New app `apps.xmi_interop` (`importer.py` bytes -> `ImportResult(model, layout, warnings, name)` via `defusedxml`, 5 MB cap, XXE/entity expansion rejected; `exporter.py` `ProjectDocument` -> XMI 1.1/UML 1.3 windows-1252 mirroring the real EA sample, deterministic, with `UML:Diagram` geometry from the layout; `errors.py`; `api.py`). `POST /api/orgs/{org_slug}/documents/import-xmi` (multipart, OWNER/EDITOR, creates a NEW document, returns `DocumentOut` + `warnings`) and `GET .../{doc_id}/export-xmi` (any member); errors are 422 `{detail, code: invalid_xmi|unsupported_xmi}`; the router is registered BEFORE `documents_router` because its GET `/{doc_id}` would otherwise answer 405 to the literal `/import-xmi`. `uml_documents.services.create_document_from_model` added (boundary test unchanged). Import policy: unsupported elements, unknown types (fallback String), class-typed attributes, dangling associations and canonical validation diagnostics become Spanish warnings, never failures; EA class boxes map to centre positions. Frontend: `ImportXmiControl` (dashboard), `ImportWarningsAlert` (document page, warnings handed over via sessionStorage), `Exportar XML` reusing `DownloadBackendButton` with `label` props, `lib/xmi_interop.ts`, shared `lib/save_blob.ts`. Backend 1285 -> 1308 passed; frontend 363 -> 369 passed. Verified against the real EA sample end to end (import 201, export, re-import, generate). **Verified only against ONE real EA file (XMI 1.1, classes/attributes/one association):** XMI 2.1 import is basic and tested with a hand-written fixture only; export of enumerations, generalizations, aggregation/composition and diagram connectors is untested inside real EA. Class names with spaces still fail generation (422 `generation_failed`).

**Update 2026-09-20 (previous; small direct change, no SDD, uncommitted):** the UI can now download the generated Spring Boot backend of a stored document. New offline-composing Django app `apps.generation_export` (one app per domain; `service.py` `build_project_archive(document)` = `map_to_relational` -> `generate_project_sources` -> deterministic zip: generated file order, 1980-01-01 timestamps, one top folder from a slug of the document name, fallback `modelia-backend`; `NothingToGenerateError` for a model with zero classes; `api.py` `GET /api/orgs/{org_slug}/documents/{doc_id}/generate`, any org member, `application/zip` + attachment filename `<slug>-backend.zip`, 404 like `get_document_view`, 422 `{detail, code: nothing_to_generate|generation_failed}` caught in the view (no global `ValueError` handler)). The manifest is deliberately not in the zip (`domain_manifest` import guard). Frontend: `apiFetchBlob` in `lib/api.ts`, `lib/generation_export.ts`, presentational `DownloadBackendButton` (loading state, Alert with server `detail`) at the top of the document page sidebar. Backend 1267 -> 1285 passed (`apps/generation_export` 18); frontend 351 -> 363 passed. Verified end to end against the running stack (empty doc 422, doc with class 200 zip of 12 files, two downloads byte-identical, anonymous 401). Known limitation: class names with spaces still fail with 422 `generation_failed`.

**Update 2026-09-20 (previous; change `crud-restricts-operations` verified (PASS WITH WARNINGS, 0 critical) and archived, uncommitted; the last commit is `20bf71c feat(spring-generator): add filtering/search, sort validation and defaultSort`):** slice 1 of 2 of DD147 (DD160-DD167). The declared table `crud` / `readOnly` now restrict `operations[]` in the Domain Manifest. New pure `effective_operations(profile)` and `OPERATION_NAMES` in `apps/relational_mapping/domain/profile.py`; new non-field `Table.effective_operations` property in `domain/schema.py`; `apps/domain_manifest/builder/entities.py` filters its `_OPERATIONS` rows in the controller's declared order and sets `resourcePath` to `null` exactly when the effective set is empty (an invalid table name is still rejected because the segment is computed before suppression). `builder/profile.py` and `tests/test_builder_decoupling.py` are untouched (the builder reads the property duck-typed). Tests: backend 1214 -> 1267 passed, `apps/relational_mapping` 170, `apps/domain_manifest` 146, 24/24 tasks (9.1 closed at archive), ~570 authored lines, no `size:exception`, archived to `openspec/changes/archive/2026-09-20-crud-restricts-operations/` (deltas merged: `generation-profile` 9 -> 10 requirements, `domain-manifest-export` stays at 15); mutations M1-M5 all turned the suite red. **Transient divergence (DD166):** until slice 2 `spring-generator-crud-restriction` lands, a profile-restricted model yields a manifest with fewer operations than the generator's still-six endpoints; no committed fixture uses a restricted model. DD147 is retired for the manifest and annotated in place in `DECISIONS_LOG.md`. `apps/spring_generator`, `frontend/`, `docker-compose.yml`, `scripts/` and `apps/uml_*` are untouched. HEAD may have moved since the docs were last edited: the changes `uml-generation-profile-authoring` (07fb611), `uml-generation-profile-panel` (4b923aa) and `generated-spring-api-filtering-search` (20bf71c) are committed and archived.

**Update 2026-09-20 (previous; change `2026-09-20-generated-spring-api-filtering-search` applied at the time, since verified, archived and committed as `20bf71c`):** the Spring generator now consumes generation profile metadata for filtering/search, sort validation, and default sort. Eligible searchable `VARCHAR`/`TEXT`/`INTEGER`/`BIGINT`/`NUMERIC` columns generate optional controller query parameters using Java field names, one `application/<Entity>Specifications.java` builder, conditional `JpaSpecificationExecutor` repositories, and service `Specification` composition. Eligible sortable columns generate a service allow-list; invalid sort properties throw `IllegalArgumentException` and the generated shared error handler maps it to HTTP 400. Valid `Table.profile.default_sort` applies only when the incoming `Pageable` is unsorted; invalid default-sort references raise typed `InvalidDefaultSortError` before generated sources are returned. No-profile and false/unset profile tables remain byte-identical to the previous six-file output, including the SHA snapshot. Evidence: RED focused run failed on missing `build_specification_context`; focused GREEN `68 passed`; Spring generator `354 passed`; Docker backend `1214 passed`; frontend configured command `55 files / 351 tests` passed. Size exception accepted; committed as `20bf71c`.

**Update 2026-09-20 (previous; change `2026-09-20-uml-generation-profile-panel` verified, archived and committed as `4b923aa`):** the frontend now exposes the existing generation profile authoring command in the UML document sidebar. `UmlCommandIn` includes `SetGenerationProfile(element_id, profile | null)`; the new `GenerationProfilePanel` lists class and attribute targets, pre-fills tri-state controls from guarded `generation_metadata[elementId].profile`, maps class `crud` to the backend list vocabulary, submits through the existing REST `submitCommand` path, and shows Spanish `ApiError.detail` / generic errors without unmounting. The document page mounts a Card titled `Perfil de generación` after validation. Tests: focused panel/lib run passed (39 tests), full frontend `npm test` passed (55 files / 351 tests), and `npm run lint` passed after refactoring away synchronous effect state updates. Frontend-only slice; backend, persistence, canvas, WebSocket, Flutter/mobile, and `defaultSort` untouched. Tasks 14/14 checked; archive composed 5 ADDED requirements into `openspec/specs/web-uml-canvas/spec.md` and moved the change to `openspec/changes/archive/2026-09-20-2026-09-20-uml-generation-profile-panel/`. Verification recorded 351 frontend tests, 39 focused tests, lint passing, and no backend changes. Size exception was accepted; committed as `4b923aa`.

This is the "real state document" required by `product-04-next-django.md`
section 1 — kept independent of the frozen spec, updated as work actually
lands. Be honest here even when it's unflattering: this file should never
claim more progress than actually exists.

## Where the project actually is

**Update 2026-09-20 (previous; change `uml-generation-profile-authoring` verified, archived and committed as `07fb611 feat(uml-commands): author generation profile via SetGenerationProfile command`; status corrected after HEAD moved):** the generation profile is now authorable through the API (DD151-DD159), backend slice 1 of 2. New command `SetGenerationProfile(element_id, profile | None)` (last member of the `Command` union and of `CommandIn`, ten command types now) with handler `handlers/generation_profile.py` that owns only the `"profile"` key of `generation_metadata[element_id]` and prunes emptied entries; `RemoveClass` / `RemoveAttribute` prune the profile entries of what they delete, including a foreign inheritance root's `defaultSort` pointing at a removed descendant attribute (DD158). `services.submit_command` validates inside the row lock: level inferred from the model (unknown id is 422 even on a clear, DD155), the strict `profile_parser` messages surfaced verbatim as `invalid_command_payload`, and `defaultSort.attribute` resolved against the class (plus descendants for an inheritance root, DD157). DD154 is the first named import-guard exception: `uml_documents` may import exactly `apps.relational_mapping.mapping.profile_parser`, nothing else from that app; `uml_commands` stays pure. Tests: backend 1107 -> 1184 passed, `apps/uml_commands` 86, `apps/uml_documents` 134, 31/31 tasks, ~1208 authored lines, `size:exception` accepted. `apps/uml_modeling`, `apps/relational_mapping`, `apps/spring_generator`, `apps/domain_manifest`, `docker-compose.yml` and `scripts/` untouched. The follow-up frontend UI slice is now verified and archived as `2026-09-20-uml-generation-profile-panel`; remaining profile-related work is generated Spring filtering/search and DD147 (`crud` still does not filter `operations[]`). Relationship/operation-keyed entries are not pruned (DD159); removing a `GENERALIZATION` edge can leave a root `defaultSort` on a non-descendant attribute (deferred).

**Update 2026-09-20 (previous; change `manifest-generation-profile` verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `cdae44c`; delta spec `domain-manifest-export` merged into the main spec, now 15 requirements):** the Domain Manifest now emits the declared generation profile (DD142-DD150, supersedes DD131). `entities[].profile` carries `auditable`, `readOnly`, `crud` (list of lowercase strings) and `defaultSort` (`{attribute, direction}`, `attribute` resolved to the emitted camelCase attribute name; unknown, synthetic, foreign or discriminator ids raise `ManifestError`); `attributes[].profile` carries `searchable`, `sortable`, `readOnly`. Keys are emitted only when declared (never `null`, a declared `false` is kept); `schemaVersion` stays 1; `entity`, `aliases` and `generation_metadata` are never emitted. The sample model declares no profile, so its manifest (and `docs/domain-manifest.json`, gate output) is byte-identical; no gate run needed (DD150). New `builder/profile.py`, `builder/errors.py`; `apps/relational_mapping`, `apps/spring_generator`, `docker-compose.yml` and `scripts/` untouched. Tests: `apps/domain_manifest` 88 -> 125 passed, backend 1070 -> 1107 passed, 24/24 tasks (11.4 closed at archive), ~419 authored lines, no `size:exception` needed. Accepted warnings: M3 is an equivalent mutant (redundant `profile is None` guard); task 11.4 closed at archive; `EXCLUDED_KEYS` equality not asserted explicitly; the 'foreign id' scenario is covered by an id matching no column. Known tech debt (DD147): the declared `crud` does not filter `operations[]`. Deferred: `entity`, `aliases`, the authoring path for profile data.

**Update 2026-09-20 (previous; change `relational-generation-metadata` verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `284881e`; delta specs `generation-profile` (new) and `relational-mapping` (modified) merged into main specs):** the relational mapper now carries generation profile metadata. `Column.profile` / `Table.profile` (default `None`) are filled from the reserved `"profile"` key of `generation_metadata` by a strict pure parser (`mapping/profile_parser.py`, rules 1-12, `InvalidGenerationProfileError`, DD132-DD141). No consumer reads them: the 41-file Spring oracle and the Domain Manifest are byte-identical (output-neutrality tests added in `generation_runner` and `domain_manifest`). Backend suite 987 -> 1070 passed (`apps/relational_mapping` 138, `apps/domain_manifest` 88), 34/34 tasks, ~960 authored lines accepted as `size:exception`. `apps/domain_manifest` and `apps/spring_generator` sources untouched. Accepted warnings: `Table`/`RelationalModel` already unhashable (spec amended); manifest half of the neutrality test lives in `apps/domain_manifest/tests`; `InvalidGenerationProfileError` not imported in `mapper.py` (design wiring table lists it, not needed); three tests pass by construction (protected by mutation checks).

**Update 2026-09-20 (previous; change `generated-project-domain-manifest` archived, verified PASS WITH WARNINGS; committed as `d2069a5`; delta specs `domain-manifest-export` (new) and `generated-project-verification` (modified) merged into main specs):** §37 item 16.
The new offline Django app `apps.domain_manifest` (pure `builder/`, `serialize.py`, plain `__main__`
`cli.py`, DD121-DD127) derives `domain-manifest.json` (schema v1, deterministic: 6 entities,
1 enum, 5 resource paths; `vehicle` has `resourcePath: null` and no operations, DD126) from the
sample `RelationalModel`, and a drift guard cross-checks it against the committed `api-docs.json`
(DD129). Compose service `generate-manifest` (no `depends_on`, DD128) is the fourth step of
`bash scripts/verify-generated-project.sh`. Gate green (exit 0, `docs/domain-manifest.json`
12496 bytes present); negative check exit 1, reverted with equal sha1. Only declared or generated
facts are emitted (DD131): searchable/sortable/defaultSort/auditable/readOnly/aliases wait for the
mapper to carry `generation_metadata`. Tests: backend 987 (900 + 87 new in `apps/domain_manifest`).
Slice 1 is 811 authored lines (259 non-test): `size:exception` accepted. Archived to
`openspec/changes/archive/2026-09-20-generated-project-domain-manifest/` and committed as `d2069a5`
(the Postman change is `8bb9fd0`). Evidence: `openspec/changes/archive/2026-09-20-generated-project-domain-manifest/gate-evidence.md`.

**Update 2026-09-20 (change `generated-project-postman-collection` verified PASS WITH WARNINGS and archived; committed as `8bb9fd0`; delta specs `postman-collection-export` (new) and `generated-project-verification` (modified) merged at archive):** §37 item 15.
`scripts/boot-smoke.sh` now exports the real `/v3/api-docs` body to
`docs/openapi.json` inside the generated project (last statement before `PASS`, new
exit 8, DD108). The new offline Django app `apps.postman_export` (pure stdlib
`converter/` + plain `__main__` CLI, DD109-DD112, DD115) converts it into
`postman_collection.json` + `postman_environment.json` (Postman v2.1.0, tag folders,
`{{baseUrl}}` only in the environment, one status test per request, no auth, no id
chaining), run as the third step of `bash scripts/verify-generated-project.sh` through
the new compose service `generate-postman` (no `depends_on`, DD113). Fixture-first:
the committed real capture `backend/apps/postman_export/tests/fixtures/api-docs.json`
(springdoc 3.1.1, 2026-09-20) drives the tests; the real `pageable` parameter is a
`$ref` schema (DD116). Gate green (exit 0, `BUILD SUCCESSFUL`, 201/200/204/404,
both files written); negative A exit 8 and negative B exit 1, all reverted
byte-identically. Tests: backend 900 (840 + 60 new in `apps/postman_export`).
Importing the collection into the Postman application was NOT run. Authored size is
about 1246 lines (tests dominate): `size:exception` recommended. The Domain Manifest
(item 16) is applied separately (see the update above). Evidence:
`openspec/changes/generated-project-postman-collection/gate-evidence.md`.

**Update 2026-09-20 (change verified PASS WITH WARNINGS and archived at
`openspec/changes/archive/2026-09-20-generated-project-openapi-springdoc/`; committed as `a834ca2`):** 
`generated-project-openapi-springdoc` (§37 item 14, part 1). The generated `build.gradle` now declares
`org.springdoc:springdoc-openapi-starter-webmvc-api:3.1.1` (single-sourced in
`emit/versions.py`, DD103-DD104) and `scripts/boot-smoke.sh` asserts
`GET /v3/api-docs` -> 200 with `"openapi":` and `"/api/customers"` in the body
(exit 7 on content mismatch, DD105). Gate `bash scripts/verify-generated-project.sh`
green (exit 0); negative check exit 7, reverted. springdoc 3.1.1 (built on Boot
4.1.0) boots green on Boot 4.1.1. Tests: backend 840, `apps/spring_generator`
325, `apps/generation_runner` 68. (At that time Postman and Domain Manifest, items 15-16, were
still pending; both have since been applied.) Evidence: `openspec/changes/archive/2026-09-20-generated-project-openapi-springdoc/gate-evidence.md`.

**Update 2026-09-19 (change verified PASS WITH WARNINGS and archived at
`openspec/changes/archive/2026-09-19-generated-project-boot-smoke/`; §37 item 13
is complete, 3 of 3; committed as `765dbd5`):**
`generated-project-boot-smoke` (18/18 tasks) is implemented. The
manual gate `bash scripts/verify-generated-project.sh` now compiles the sample
project and then boots the jar against a throwaway `gen-db` Postgres
(`jvm-verify` profile, tmpfs, no published ports) and runs one CRUD round-trip
on `/api/customers` (201, 200, 204, 404). The negative case
`GEN_DB_PASSWORD=wrong bash scripts/verify-generated-project.sh` exits 4. New
files: `scripts/boot-smoke.sh`, `backend/apps/generation_runner/tests/test_boot_smoke_contract.py`
(8 Docker-free tests pinning what the script hardcodes about the generated app);
modified: `docker-compose.yml`, `scripts/verify-generated-project.sh`. Tests:
backend 836, `apps/generation_runner` 67. Generator sources were not touched. The
gate is manual, not in pytest (DD85, DD101). Evidence:
`openspec/changes/archive/2026-09-19-generated-project-boot-smoke/gate-evidence.md`.

**As of 2026-09-19** (25 archived SDD cycles, the latest being
`2026-09-19-spring-boot-project-scaffold`; no open change; backend 764 tests,
685 before that change): the UML modeling core
(canonical model, validation engine, command bus, persistence, canvas with
locking), multi-tenant identity/auth, realtime collaboration, the UML →
RelationalModel mapper, and six slices of the Spring Boot generator all exist
and are archived. The mapper now preserves UML class ownership for
attribute-derived relational columns via `Column.owning_class_id`, while
synthetic/discriminator/FK/join columns keep that metadata unset. The generator
emits Java **source text only** for one table at a time (`domain/`,
`persistence/`, `application/`, `api/`, `errors/`), with discriminator-backed
Single Table inputs limited to root/subclass domain entities plus the root
repository, plus one pure project-singleton `src/main/resources/application.yml`
resource generator. The archived whole-model orchestrator slice adds the pure
`generate_model_sources(...)` aggregate API and exact duplicate generated-path
rejection; Docker verification passed for the focused Spring generator suite
and full backend regression (`238/238` spring generator tests, `685/685` backend tests).

`spring_generator` now has **seven public entry points**: `generate_table_sources`,
`generate_enum_source`, `generate_shared_error_sources`,
`generate_project_config_sources`, `generate_model_sources`, and the two new
scaffold entry points `generate_project_scaffold_sources(*, base_package)` (exactly
`build.gradle`, `settings.gradle`, root-package `Application.java`) and
`generate_project_sources(model, *, base_package)` (the model aggregate followed
by those three files). Toolchain versions live only in `emit/versions.py`
(Spring Boot 4.1.1, Java 21, project 0.0.1-SNAPSHOT, Gradle 9.7.1). This is
§37 item 13 **slice 1 of 3**: pure scaffold text, nothing writes, compiles or
runs yet (slice 2 compile-check, slice 3 boot-smoke). After this change:
`764` backend tests, `317` Spring generator tests. Separately, a manual spike
(outside the test suite, nothing committed) built the full `generate_project_sources`
output for a sample model with `gradle build` in `gradle:9.7.1-jdk21`
(BUILD SUCCESSFUL, 41 files) and booted an equivalent hand-scaffolded project
against Postgres 16; that is evidence, not an automated check, until slice 2.

**Update, same day, compile-check change verified (PASS WITH WARNINGS) and archived
(not yet committed):** §37 item 13 is now at **slice 2 of 3 archived**. New app
`backend/apps/generation_runner/` writes `GeneratedSources` to disk
(`write_sources`, path re-validation, non-empty-target refusal, pre-write
atomicity), with a CLI and a sample model (readable ids as a documented workaround
for the `emit/inheritance_context.py:169` defect). A manual, compose-based gate,
`bash scripts/verify-generated-project.sh`, generates the project into a named
volume and runs `gradle build` in `gradle:9.7.1-jdk21`; recorded result
`BUILD SUCCESSFUL in 50s`, exit 0, 41 files (evidence in
`openspec/changes/archive/2026-09-19-generated-project-compile-check/gate-evidence.md`). The gate is
NOT part of `pytest` (no Docker socket, no `jvm` marker). Verification findings:
PASS WITH WARNINGS (W1 accepted deviation: sentinel default for GRADLE_IMAGE instead of required form;
W2 fixed: CLI now catches `(GeneratedSourceWriteError, UngeneratableSourceError, ValueError, OSError)` with two added tests).
Tests: backend `822` (764 + 58 new in `apps/generation_runner`), Spring generator `317` unchanged.
Still missing: slice 3 boot smoke, the inheritance-naming bugfix. The paragraph above and the bullet below about "compilation of any
generated Java" are superseded only for the manual gate; nothing compiles Java in
the automated suite.

**Update, same day, inheritance subclass-naming fix VERIFIED and ARCHIVED (not yet committed):**
change `spring-generator-inheritance-subclass-naming` (26/26 tasks, Strict TDD, verified PASS WITH WARNINGS, 0 CRITICAL). The defect is fixed:
`emit/inheritance_context.py:169` now names each subclass Java class
`pascal_case(table.discriminator_values[class_id])` (the UML class name the mapper stores
verbatim) instead of `pascal_case(class_id)`, so uuid4-hex element ids no longer raise
`InvalidJavaIdentifierError`; output is id-independent. Fixtures now use class-name discriminator
values (`Vehicle/Car/Truck/PickupTruck`, `@DiscriminatorValue("Car")`). A discriminator value that is
not a legal Java identifier (for example `"Sports Car"`) is still rejected with
`InvalidJavaIdentifierError` (pinned limitation). `apps/generation_runner/samples/sample_model.py` now
uses frozen uuid4-hex class-id literals (vehicle/car/truck digit-leading) and lost the workaround
docstring; the manual compile gate re-run over it gave `BUILD SUCCESSFUL in 41s`, exit 0
(archived to `openspec/changes/archive/2026-09-19-spring-generator-inheritance-subclass-naming/gate-evidence.md`; the first run hit a
transient Maven Central TLS failure, exit 1, the immediate rerun passed). Tests: backend `828`
(822 + 6), Spring generator `322` (317 + 5), `apps/generation_runner` `59` (58 - 2 + 3). The SHA-256
snapshot `test_inheritance_backward_compatibility.py` is unmodified and passing. Archived to
`openspec/changes/archive/2026-09-19-spring-generator-inheritance-subclass-naming/` with delta spec
merged into main spec. The previous "Still missing: ... the inheritance-naming bugfix" no longer applies.

What does **not** exist: inheritance DTO/service/controller/API behavior, filtering/search, the generated
`config/` layer, generation_metadata-based manifest fields (the Domain Manifest exists but only with declared facts), a generated frontend/mobile,
the assistant, voice, XMI and image → UML. The generated backend now serves an OpenAPI document
at runtime via `/v3/api-docs` (springdoc 3.1.1), and the gate exports that document and a Postman
collection inside the generated project (`docs/openapi.json`, `postman_collection.json`); operationId/tag tuning, id-chained newman-runnable
collections and ProblemDetail documentation remain future work. Undo/Redo and Presence (§37 items
7 and 10) have no dedicated archived cycle and are not verified as
implemented. See `HANDOFF_LATEST.md` for the stage summary and
`NEXT_STEPS.md` for what comes next.

> The per-area sections below (Backend, Frontend, Mobile, SDD / planning,
> Domain) were appended cycle by cycle; where an older sentence in them
> contradicts this paragraph, this paragraph wins.

### Backend

- Dockerized Django project skeleton exists (`config` settings package,
  empty `apps/`).
- **In progress by a parallel workstream**: migration from Django REST
  Framework to Django Ninja, addition of Django Channels + Daphne (ASGI),
  addition of Argon2 password hashing + PyJWT, and bootstrap of
  pytest + pytest-django + hypothesis, including a health-check endpoint
  and one smoke test. This is **not confirmed complete** as of this
  reconciliation — its final result was not available to verify.
- **Postgres is now a hard test prerequisite.** With `backend/apps/users/` and
  `backend/apps/organizations/` landing the project's first migrations, `pytest-django` builds its test
  database from the `POSTGRES_*` env vars on every run — a reachable `db`
  service (`docker compose up -d db backend`) is required before
  `docker compose exec backend pytest` (or `cd backend && pytest`) will
  work. `apps/uml_modeling/` itself stays DB-free and unaffected.
- **SDD Cycle 4** (`tenant-aware-registration-login`) is **fully
  implemented**, single PR: `register_user` (`apps/users/services.py`) is
  now `@transaction.atomic` and provisions exactly one `Organization` +
  `OWNER` `Membership` per registration via three additive
  `organizations/services.py` helpers — `build_slug_base`/
  `derive_workspace_name` (pure, `hypothesis`-property-tested) and
  `generate_unique_slug` (bounded 5-attempt suffixed retry + final
  long-token fallback, raising `OrganizationError` on exhaustion, which
  rolls the whole registration transaction back). `create_organization`,
  every model, and every migration stay byte-for-byte unchanged. 185/185
  backend tests pass. `sdd-verify`/`sdd-archive` are the remaining steps.

### Frontend

- Dockerized Next.js (App Router, TypeScript) skeleton exists with a
  minimal `env.ts`/`api.ts` pair.
- **In progress by a parallel workstream**: addition of Tailwind CSS +
  shadcn/ui + Cytoscape.js + cytoscape-fcose + Jotai, and bootstrap of
  Vitest + React Testing Library, including one smoke test. This is **not
  confirmed complete** as of this reconciliation — its final result was
  not available to verify.

- **SDD Cycle 3** (`frontend-auth-integration`) is **fully implemented**
  across its 3 chained PRs (`stacked-to-main`): a credentialed, CSRF-aware
  transport seam (`lib/api.ts` — `credentials: "include"` on every request,
  automatic CSRF priming/retry, typed `ApiError`/`NetworkError`); domain
  clients `lib/auth.ts` (`register`/`login`/`logout`/`fetchMe`) and
  `lib/organizations.ts` (`listOrganizations`/`createOrganization`), one
  module per backend Django app; Jotai session/organization state
  (`state/session.ts`'s `useSession()` discriminated union
  `loading|authenticated|anonymous|error`, `state/organizations.ts`'s
  `useOrganizations()` with `localStorage`-persisted active org); a
  `SessionGuard` Client Component gating the `(app)` route group
  (`/dashboard`), with `(auth)` hosting `/login`/`/register`; the
  organization panel (`OrgSwitcher`, `OrgEmptyState`, `CreateOrgForm`,
  `AppTopbar` with the app's only logout affordance); and a session-aware
  landing navbar ("Iniciar sesión"/"Registrarse" when anonymous, "Ir al
  panel" when authenticated). 67/67 frontend tests pass, `npm run lint`
  clean, `next build` succeeds (`/`, `/login`, `/register`, `/dashboard`
  all prerender as static `○`), `backend/` byte-for-byte unchanged.
  `sdd-verify`/`sdd-archive` are the remaining steps. Deviations from
  design.md are documented inline in `tasks.md` (Phase 2, 4.1, 5.5, 6.1,
  6.5, 7.2) — most notably: `lib/auth.ts` exports `fetchMe()` (not
  `getMe()`) with object-arg signatures, matching design.md's authoritative
  "Interfaces" contract over tasks.md's looser prose; `OrgSwitcher` and
  `CreateOrgForm` were made purely presentational (props, not their own
  `useOrganizations()` call) to avoid duplicate `listOrganizations()`
  fetches between the sibling `AppTopbar`/`dashboard/page.tsx` containers
  under `(app)/layout.tsx` — a small remaining duplicate-fetch tradeoff
  (exactly 2 `useOrganizations()` instances per dashboard visit, one per
  container) is accepted as low-risk since the request is an idempotent GET
  converging on the same shared `organizationsAtom`.

- **SDD Cycle 5** (`ssr-protected-routes`) is **fully implemented**, single
  PR, frontend-only (`backend/` byte-for-byte unchanged): `(app)/layout.tsx`
  and `(gate)/layout.tsx` are now `async` Server Components that `await
  requireUser(nextPath)` (new `lib/server-session.ts`) as their first
  statement, before any protected markup can be emitted — a session cookie's
  *validity*, not merely its presence, is checked server-side on every
  direct/no-JS request, closing the gap where `SessionGuard`'s client-only
  gate let an anonymous `curl`/deep-link request receive the full RSC
  payload. `getServerUser()` (React `cache()`-wrapped) forwards the whole
  cookie jar verbatim to `GET {internalApiUrl}/api/auth/me` with
  `cache: "no-store"`; `200` → `User`, `401`/`403` → `null` (redirect to
  `/login?next=<safe(nextPath)>`), anything else (5xx, network failure) →
  throws, caught by `requireUser` and treated as "render normally, let
  `SessionGuard`'s client retry state own it" — an outage is never
  misread as a logout. New `lib/env.ts::internalApiUrl` (falls back to
  `apiUrl`) lets the frontend container reach `backend:8000` instead of
  `localhost:8000` (which is the container itself). `SessionGuard.tsx` and
  its test are byte-for-byte untouched — this is additive server-side
  defense-in-depth, not a replacement for the existing client-side skeleton/
  error/retry UX. 102/102 frontend tests pass (15 new: 13 in
  `server-session.test.ts`, 2 in `env.test.ts`), zero regressions.
  **Deployment precondition**: the browser must send the Django `sessionid`
  cookie to the Next.js origin — true for localhost and same-parent-domain
  deploys, false for a split `app.x.com`/`api.y.com` deployment (every
  authenticated user would bounce to `/login`). **Deviation found during
  manual verification, not anticipated by design.md**: `docker-compose.yml`'s
  `backend` service needed `ALLOWED_HOSTS` to additionally include `backend`
  (the Compose service name) — Django's `CommonMiddleware` otherwise rejects
  the `Host: backend:8000` header the frontend container's server-side fetch
  sends, returning `400 Bad Request` for every `/api/auth/me` call from
  inside the Docker network (misread by `getServerUser` as a 5xx-class
  failure, so it degraded silently to the client-retry fallback rather than
  the intended redirect — sd-apply added `backend.environment.ALLOWED_HOSTS`
  to `docker-compose.yml` and updated `backend/env.example` to document it).
  A second finding: design.md's Technical Approach claims the 307 response
  has nothing flushed to the body ("nothing has flushed when the gate
  throws"); verified against the real running stack (both `next dev` and a
  `next build && next start` production run) that Next.js 16.3.3 actually
  streams a small inert `<html id="__next_error__">` document shell
  alongside every `redirect()`-triggered 307 — it carries a `NEXT_REDIRECT`
  error digest and dev-mode stack trace, never dashboard/org data or
  `AppTopbar`/`SessionGuard`-authenticated markup, so the underlying spec
  requirement ("the response body contains no protected-route markup")
  still holds, but DD8's literal `rg -c "<html" body.txt` verification
  command does not — see `openspec/changes/ssr-protected-routes/tasks.md`
  Phase 6 for the full 8-step manual verification transcript.
  `sdd-verify`/`sdd-archive` are the remaining steps.

- **SDD Cycle 4** (`tenant-aware-registration-login`) is **fully
  implemented**, single PR: `LoginForm.tsx` now resolves the caller's
  organizations via `listOrganizations()` directly (never
  `useOrganizations()`, which would fire an anonymous fetch on the login
  page) and branches the post-login destination — a valid `next` wins
  unconditionally over org-count branching; otherwise 0 orgs → `/dashboard`
  unchanged, 1 org → set active + `/dashboard`, 2+ orgs → the new
  `/select-organization` picker (`app/(gate)/select-organization/page.tsx`,
  under a new `(gate)` route group with its own `SessionGuard` + centered
  card, no topbar). `RegisterForm.tsx` adopts the sole provisioned org
  (read from `GET /api/orgs` post-register, since org data is deliberately
  excluded from `UserOut`) before redirecting. New shared pieces:
  `lib/next-path.ts::isSafeNext` (the precedence-rule predicate, with
  `safe()` re-expressed through it, byte-identical), `state/organizations.ts
  ::useSetActiveOrg()` (the write half of `useOrganizations`, consumed by
  both the hook and the auth forms), `components/workspace/OrgPicker.tsx`
  (presentational, no `activeSlug`), and `components/workspace/roleLabels.ts`
  (shared with `OrgSwitcher`, preventing translation-table drift). 87/87
  frontend tests pass (17 new), `backend/` and every pre-existing
  frontend behavior unchanged. `sdd-verify`/`sdd-archive` are the
  remaining steps.

- **SDD Cycles 7–9** (`uml-canvas-ui`, `uml-command-bus`, `uml-document-persistence`,
  merged 2026-09-12, then `uml-canvas-remove-ui`, this entry) brought the
  UML canvas domain to the frontend for the first time: `lib/uml_documents.ts`
  (domain client for `apps/uml_documents`, one module per backend Django
  app), a Cytoscape.js `DiagramCanvas`, `AddClassForm`/`AddAttributeForm`/
  `AddRelationshipControl` for growing a diagram, and `state/document.ts`'s
  `useDocument` (POST command → refetch → `setDocument`). **Cycle 9
  (`uml-canvas-remove-ui`, this entry) closes the create/destroy gap** those
  cycles deliberately deferred: `RemoveClassControl` (class select + a
  mandatory confirmation step stating the exact client-derived cascade
  count), `RemoveAttributeControl` (class → attribute select, immediate
  submit), and `RemoveRelationshipControl` (relationship select labelled by
  endpoint names + kind, immediate submit) are wired into
  `documents/[docId]/page.tsx` under a new "Eliminar" heading. `UmlCommandIn`
  now covers 6 of the backend's 7 command shapes — only `RenameClass` has no
  UI. `backend/` diff is empty for this cycle: all three remove commands,
  their schemas, and cascade behavior already existed and were already
  tested. `sdd-verify`/`sdd-archive` remain.
  **Known documentation gap**: Cycles 7–8 (`uml-canvas-ui`,
  `uml-command-bus`, `uml-document-persistence`) never received their own
  `DECISIONS_LOG.md`/`CURRENT_STATE.md` sync entries when they merged; this
  paragraph is the first mention of the canvas domain existing at all in
  this file. A full backfill of those three cycles' individual design
  decisions is out of `uml-canvas-remove-ui`'s scope and remains pending.

- **SDD Cycle 10** (`uml-document-list`) is **fully implemented**, single PR,
  additive on both sides (`backend/apps/uml_documents/models.py` and its
  migrations byte-for-byte unchanged): `/dashboard` now lists an
  organization's documents instead of only redirecting to one just created.
  `GET /orgs/{slug}/documents` (`services.list_documents`, gated exactly like
  the existing single-document read — no `require_role`, so `VIEWER` reads
  too) returns a lightweight `DocumentSummaryOut` (`id`/`name`/`revision`/
  `updated_at`, `name` flat unlike `DocumentOut.metadata.name`), newest-updated
  first. `lib/uml_documents.ts::listDocuments` + `state/documents.ts`'s
  `useDocuments` (local `useState`, cloned from `useMembers`'s shape, not a
  Jotai atom) feed the new presentational `DocumentList` (real `next/link`
  rows, empty-state copy instead of `null` when there are zero documents).
  The "Nuevo Diagrama" entry point moved into a new "Mis Diagramas" header
  row, above the list, and now discloses the unmodified `CreateDocumentForm`
  behind a click instead of always rendering it. 319/319 backend tests pass
  (8 new), 251/251 frontend tests pass (23 new), zero regressions.
  `sdd-verify`/`sdd-archive` remain.

- **SDD Cycle 11** (`uml-relationship-kinds`) is **fully implemented**,
  single PR, `backend/` diff empty (`RelationshipIn.kind` was already the
  full 4-kind `Literal`; only the frontend had hardcoded `association`). The
  canvas now supports all 4 UML 2.5 relationship kinds with per-kind
  notation, not just association: `AddRelationshipControl` gained a `Tipo de
  relación` select (defaulting to `association`) that drives the submitted
  `AddRelationship.relationship.kind`; selecting `generalization` hides both
  multiplicity selects and always submits `"1"`/`"1"` (UML 2.5 has no
  multiplicity there), with the earlier multiplicity choice preserved (not
  reset) if the user switches back. `DiagramCanvas`'s `toElements` now
  copies `relationship.kind` into edge `data`, and the exported `STYLE`
  renders each kind's UML 2.5 terminator — hollow triangle
  (generalization), hollow diamond (aggregation, at the first-clicked/
  "whole" `source` end), filled diamond (composition, same end), plain line
  (association, no terminator) — while leaving the pinned `edge.self-loop`
  geometry untouched. 278/278 frontend tests pass (18 new). `sdd-verify`/
  `sdd-archive` remain.

### Mobile

- `mobile/` is a bare Flutter scaffold (default counter-app template plus
  an `AppConfig` reading `API_BASE_URL`). It does not yet implement
  anything domain-specific for the CASE tool. This is the instructor-
  mandated real Flutter client for the main tool (see `PROJECT_VISION.md`
  and `ARCHITECTURE.md`) — still to be designed and built out.

### Manual smoke checklist — Cycle 3 real cross-origin cookie flow (not automated)

Unit tests stub `fetch` at the module boundary (proposal D8); no MSW, no real HTTP.
This checklist is the deferred proof for the real browser session-cookie round trip,
per design.md's Testing Strategy and proposal Risk table. Run with the backend at
`http://localhost:8000` and the frontend at `http://localhost:3000`:

1. **Register → reload → still authenticated.** Visit `/register`, submit a unique
   email + password, land on `/dashboard` authenticated. Reload the page: `useSession()`
   re-fetches `GET /api/auth/me` and the session stays authenticated (no bounce to
   `/login`) — proves the `HttpOnly` session cookie survives a hard reload.
2. **Logout → `/`.** From the panel, click "Cerrar sesión". Confirm the request hits
   `POST /api/auth/logout`, the client session clears, and the browser lands on `/`
   (proposal Q4 — a deliberate logout is an exit, not a prelude to `/login`).
3. **Backend stopped + load `/dashboard` → retry panel, not `/login`.** Stop the
   backend container, then visit `/dashboard` directly. `GET /api/auth/me` fails as a
   network error, not a `401` — confirm the guard renders the retry panel ("No pudimos
   verificar tu sesión...") and does **not** redirect to `/login` (DD5's "an outage must
   not resolve to anonymous").

Not yet run against a real deployed cross-domain origin (`app.example.com` →
`api.example.com`) — the CSRF body-token fallback path (DD2) is unverified beyond the
cookie fast path exercised by local dev (proposal's Open Question 1 in design.md).

### End-to-end testing

- Cypress bootstrap is planned but has not been started by anyone yet.

### SDD / planning

- `openspec/` is initialized at the repo root (config + specs + changes
  directories exist). **SDD Cycle 1** (`canonical-uml-model`) has run
  through explore → propose → spec → design → tasks → apply; `sdd-verify`
  and `sdd-archive` are the remaining steps for this change.
- **SDD Cycle 2** (`multi-tenant-identity`) is **fully implemented**
  across its 3 chained PRs (`stacked-to-main`, review-budget guard), and
  was subsequently split from a single `apps/identity/` app into two
  apps per Django's one-app-per-domain convention:
  `backend/apps/users/` (`AUTH_USER_MODEL = "users.User"`, the `User`
  model, `register_user`/`authenticate_user` services, `auth_router`) and
  `backend/apps/organizations/` (`Organization`, `TenantScopedModel`/
  `Membership` models, the tenancy/membership services and
  `_assert_not_last_owner` guard, `permissions.py`
  (`resolve_membership`/`require_role`), `organizations_router`/
  `memberships_router`) — the project's **first migrations** (PR 1);
  services + permissions (PR 2); schemas, routers mounted in
  `config/api.py`, and the DD2 cross-origin session/CSRF settings block
  in `config/settings.py` plus `backend/env.example` (PR 3). 168/168
  backend tests pass. `sdd-verify`/`sdd-archive` are the remaining steps.
  Three deviations from design.md were required and are documented in
  `tasks.md`'s Phase 5 note: (1) the installed django-ninja 1.7 has no
  `NinjaAPI(csrf=True)` kwarg — CSRF is enforced equivalently via
  `django_auth`'s built-in check plus an explicit `check_csrf()` call on
  the two anonymous unsafe endpoints; (2) `org_slug` (a mount-prefix path
  segment) needed an explicit `Path[str]` annotation per operation,
  since this ninja version does not auto-detect prefix-only path params;
  (3) `email-validator` was added as a new, small dependency to support
  `EmailStr` in the schemas — the proposal's "no new dependency" line is
  now inaccurate by that one package.
- **SDD Cycle 12** (`2026-09-14-realtime-uml-collaboration`) is **implemented**
  (Phases 1–7 of `tasks.md`; Phase 8 verification below). Two members of one
  organization now see each other's edits on one UML document with no
  reload: `submit_command` (`apps/uml_documents/services.py`) is
  `@transaction.atomic` and locks the row with `_get_row(...,
  for_update=True)` chained AFTER `.for_organization(...)` (DD1 — closes a
  lost-update race between two concurrent commands that predated this
  feature), then broadcasts the resulting document via
  `transaction.on_commit` (DD2) to a sync `DocumentConsumer`
  (`apps/uml_documents/consumers.py`) joined to group `uml-doc-{doc_id}`
  (DD3). The consumer authorizes with membership only — no `require_role`
  (DD4), via the new `resolve_membership_for_user(user, org_slug)` extracted
  in `apps/organizations/permissions.py` — and re-authorizes on every
  relay, closing `4403` if membership was revoked (DD5). The wire payload is
  the existing `DocumentOut`, promoted from `api._document_out` to
  `codec.document_out(document)` (DD6/DD7), so a broadcast and a `GET
  .../documents/{docId}` stay byte-identical. `config/asgi.py`'s
  `"websocket"` route now serves `apps/uml_documents/routing.py` through
  `OriginValidator(AuthMiddlewareStack(URLRouter(...)),
  CORS_ALLOWED_ORIGINS)` (DD9) — no new env var, no CSRF equivalent (the
  socket performs no writes). `CHANNEL_LAYERS` uses
  `channels_redis.core.RedisChannelLayer` from discrete `REDIS_HOST`/
  `REDIS_PORT` env vars (DD8; a new `redis:7-alpine` Compose service with a
  healthcheck backs it). On the frontend, `useDocument`
  (`state/document.ts`) gained a second effect that opens
  `openDocumentSocket` (`lib/uml_documents.ts`, the sole place that builds a
  WS URL, derived from `lib/env.ts`'s `wsUrl`), merges every
  incoming/refetched document monotonically by revision so a duplicate or
  out-of-order delivery costs zero re-renders (DD11), and reconnects with
  capped exponential backoff (1s→2s→4s→8s→10s) on any non-terminal close —
  `4401`/`4403`/`4404` are terminal, so a revoked/unauthenticated client
  never hammers the handshake (DD13). `DiagramCanvas.tsx` gained a
  `draggingRef`/`pendingUpdateRef` guard so a remote update mid-drag defers
  its `cy.json()`/layout sync until the `free` event, instead of
  re-laying-out under the user's cursor (DD12); `pendingSourceId`/
  `pendingTargetId` needed no guard — verified unreachable from
  `useDocument`, so `app/(app)/documents/[docId]/page.tsx` has zero diff
  from this cycle. The "does `runserver` serve WebSocket in dev?" question
  is resolved as yes (DD10, `daphne` precedes `django.contrib.staticfiles`
  in `INSTALLED_APPS`) — the acceptance banner readback and the
  Redis-service healthcheck still need one `docker compose build && docker
  compose up` restart to observe, deferred to the maintainer per this
  project's docker-lifecycle convention. Full regression:
  339/339 backend (`pytest`) and 293/293 frontend (`vitest run`) pass, plus
  clean `eslint`/`tsc --noEmit`/`next build`.
- **SDD Cycle 14** (`2026-09-16-uml-class-operations`) is **implemented**
  (Phases 1–14 of `tasks.md`). **Operations are now reachable end to end** —
  the domain (`UmlOperation`/`UmlClass.operations`), codec round-trip, and
  `empty_element_name` validation all existed with zero production callers
  before this cycle; `AddOperation`/`RemoveOperation` (mirroring
  `AddAttribute`/`RemoveAttribute` verbatim) open the write path: closed
  command union 7→9, `_HANDLERS` 7→9, `CommandIn`/`UmlCommandIn` discriminated
  unions both grow by 2, `AddOperationForm`/`RemoveOperationControl` mount
  under the existing "Agregar"/"Eliminar" panels, and `DiagramCanvas` renders
  a second UML-notation compartment below attributes (`+ crearUsuario():
  Usuario`), separated by its own divider — additive-only layout math keeps
  a zero-operations class byte-identical to before this cycle. A new
  `duplicate_operation_name` rule (name-only, scoped per class) brings the
  fixed validation registry from **10 rules to 11**. **v1 scope**:
  `parameters` stays UI-unreachable — the domain/codec/persistence already
  carry a non-empty tuple losslessly, but no form collects one; the wire
  schema (`UmlOperationIn`) has no `parameters` field at all, and the mapper
  always constructs `parameters=()`. 384/384 backend tests pass (25 new),
  335/335 frontend tests pass (17 new), clean `eslint`/`next build`.
  `sdd-verify`/`sdd-archive` are the remaining steps.
- **SDD Cycle 13** (`2026-09-15-uml-node-position-sync`) is **implemented**
  (Phases 1–7 of `tasks.md`). **The document socket is now bidirectional** —
  Cycle 12 gave `DocumentConsumer` only `document_update`; this cycle adds
  its first `receive_json`, handling `node.claim`/`node.position`/
  `node.release` with a per-message `require_role(OWNER, EDITOR)` re-check.
  Dragging a class node now claims it via a new ephemeral Redis lock module
  (`apps/uml_documents/locks.py` — `SET NX PX` + owner-token compare-and-
  delete/compare-and-expire Lua scripts, TTL 10s, key
  `uml-lock:{doc_id}:{class_id}`), streams throttled (50ms) live positions
  to every other connection with **zero database write**, and on release
  persists the final position through a new `services.save_layout_position`
  — a `submit_command` sibling under the same row lock that never touches
  `dispatcher.apply()` or the `UmlCommand` union. **`ProjectDocument.layout`
  is now live**: `with_layout` (built in Cycle 1, never called in
  production before this cycle) has its first real caller, and `layout` is
  pruned of any class id absent from the current model on every persisted
  release. The two lock domains stay deliberately disjoint — a held Redis
  claim never blocks, delays, or is consulted by `RemoveClass` or any other
  `UmlCommand`, verified end-to-end in `test_consumers.py`. On the
  frontend, `toElements` (`DiagramCanvas.tsx`) now seeds each node's
  initial position from `document.layout.positions` instead of always
  running a full `fcose` layout on load; a foreign-held node is
  `ungrabify()`d with a dashed-amber affordance, and `state/document.ts`
  exposes `sendClaim`/`sendPosition`/`sendRelease` plus a `locks` state and
  a ref-based live-position listener so a remote drag moves a node with
  zero re-render. 359/359 backend tests pass (20 new, across the new
  `test_locks.py` and additions to `test_services.py`/`test_consumers.py`),
  317/317 frontend tests pass (24 new, across `DiagramCanvas.test.tsx`,
  `document.test.ts`, `uml_documents.test.ts`, `page.test.tsx`), clean
  `eslint`/`tsc --noEmit`. `sdd-verify`/`sdd-archive` are the remaining
  steps.

### Domain

- **SDD Cycle 1 is implemented** (`backend/apps/uml_modeling/`, change
  `canonical-uml-model`): `CanonicalUmlModel` (alias `UmlModel`) with
  classes, enumerations, relationships, and generation metadata;
  `ProjectDocument`/`DiagramLayout` (identity, opaque `owner_id`, pure
  revision increment via `with_model`/`with_layout`); and the single
  validation `engine.validate()` with its full 10-rule Cycle-1 registry
  (`EMPTY_ELEMENT_NAME`, `DUPLICATE_CLASS_NAME`, `DUPLICATE_ATTRIBUTE_NAME`,
  `DUPLICATE_ENUMERATION_LITERAL`, `UNKNOWN_ATTRIBUTE_TYPE`,
  `INVALID_RELATIONSHIP_ENDPOINT`, `INVALID_MULTIPLICITY`,
  `GENERALIZATION_CYCLE`, `SELF_ASSOCIATION`, `CLASS_WITHOUT_ATTRIBUTES`).
  This is a pure, DB-free, framework-agnostic domain layer: no
  `models.py`, no migrations, no urlconf, no Ninja/Pydantic schemas, no
  persistence, and no auth wiring yet — `owner_id` is a validated-opaque
  string only. 80 backend tests cover it (TDD, `pytest` + `hypothesis`),
  with zero regression to the pre-existing health-check smoke test.
- **SDD Cycle (`2026-09-17-uml-relational-mapping`) is implemented**
  (`backend/apps/relational_mapping/`, spec §21): a pure, DB-free
  `map_to_relational(CanonicalUmlModel) -> RelationalModel` — the first stage
  of the future Spring Boot generator pipeline. `domain/` (`Table`, `Column`,
  `PrimaryKey`, `ForeignKey`, `UniqueConstraint`, `Index`, `EnumType`,
  `RelationalModel`, all frozen) + `mapping/` (`errors`, `naming`, `mapper`,
  a 5-stage pipeline: hierarchy -> enumerations -> tables -> relationships ->
  freeze). Settled rules: synthetic UUID PK on every table unconditionally,
  Single Table inheritance with a verbatim-class-name `class_type`
  discriminator, native-`ENUM`-flavored enumerations, composition FKs always
  `NOT NULL CASCADE` (nullable only for the documented self-composition tree
  exception), association/aggregation FK nullability from the referenced
  end's `Multiplicity.lower`, and join tables for many-to-many. A new
  `MULTI_PARENT_GENERALIZATION` `ERROR` rule (`apps.uml_modeling`) is the
  primary defense against a multi-parent tree; the mapper's own
  `MultipleGeneralizationParentsError`/`GeneralizationCycleError`/
  `UnknownEnumerationError`/`DanglingRelationshipEndpointError` are
  defense-in-depth only — the mapper never calls `validate()`. Zero Django/DB/
  Java imports in the new module. 442/442 backend tests pass (58 new).
  `sdd-verify`/`sdd-archive` are the remaining steps.
- `UmlCommand`/Command Bus, the Cytoscape canvas, persistence (Django
  ORM), and realtime collaboration are implemented for the UML domain
  (see Backend/Frontend sections above). The Domain Manifest now exists (see the latest update above); the
  assistant pipeline, and all AI/voice/image/XMI features are **not
  started**.
- **SDD Cycle (`2026-09-18-spring-boot-generator-core`) is implemented**
  (`backend/apps/spring_generator/`, spec §22, item 12 — first slice): a
  pure, DB-free, filesystem-free `generate_table_sources(table, *,
  base_package="com.modelia.generated") -> GeneratedSources`, turning one
  `relational_mapping.domain.schema.Table` (scalar columns only, no FK,
  no discriminator, no enum) into in-memory Java source for one JPA
  `@Entity` class (`domain/`) and one Spring Data JPA repository
  interface (`persistence/`), at `src/main/java/<base_package
  path>/{domain,persistence}/...`. `domain/` (`GeneratedFile`/
  `GeneratedSources`, frozen) + `emit/` (`errors`, `naming`, `javatypes`,
  `context`, `renderer`, `templates/*.java.j2`), mirroring
  `relational_mapping`'s `domain/`+`mapping/` split one cycle later in
  the same pipeline. Settled rules: boxed Java types only (never
  primitives), `TIMESTAMPTZ -> java.time.OffsetDateTime`,
  `TEXT -> String` + `columnDefinition = "TEXT"`, the PK gets `@Id` +
  `@GeneratedValue(strategy = GenerationType.UUID)` and explicitly no
  `@NotNull`, non-PK non-nullable columns get `@NotNull` (never
  `@NotBlank`), a `VARCHAR` with a `length` gets `@Size(max=length)`, a
  typed `UngeneratableTableError` hierarchy rejects any FK/discriminator/
  `ENUM`/composite-or-non-UUID-PK table in a fixed check order before any
  render, a Java reserved-word field name gets a trailing `_` while
  `@Column(name=...)` preserves the original DB name, and every emitted
  file's field order, import grouping, and text is byte-identical across
  repeated calls on the same input. Jinja2 (`emit/templates/*.java.j2`,
  loaded from `emit/templates/` — never Django's app-root `templates/`,
  which would expose the `.java.j2` files to Django's own `APP_DIRS`
  template loader) owns all emitted Java text; a LibCST guard
  (`tests/test_no_concat_guard.py`) parses every module under `emit/`
  and fails on manual string `+`, `str.join`, `%`-formatting, or any
  f-string in the generator's own Python source (`.format()` and a
  reassignment-loop comma-join are the allowed alternatives) — it never
  parses Java and never runs at render time. 93 new backend tests
  (structural-only per proposal D2: expected paths, class/field/
  annotation lines, brace balance — no `javac`, no Java parser), full
  suite green. `sdd-verify`/`sdd-archive` are the remaining steps.
- **SDD Cycle (`2026-09-18-spring-boot-generator-application-api-layer`) is
  implemented** (`backend/apps/spring_generator/`, spec §22, item 12 —
  third slice, extends both cycles below): `generate_table_sources(table)`
  grows from 2 to **6** emitted files per call, in fixed layer order
  `domain/`, `persistence/`, `application/dto/<E>RequestDto.java`,
  `application/dto/<E>ResponseDto.java`, `application/<E>Service.java`,
  `api/<E>Controller.java` (DD50a) — a generated backend now has a callable
  REST surface for the first time. A new sibling entry point
  `generate_shared_error_sources(*, base_package) -> GeneratedSources`
  (DD42, mirroring DD30's `generate_enum_source` precedent) emits exactly
  two per-project `errors/` files once, never per-`Table`. **A real defect
  is fixed in the same slice**: the DTO layer flattens every relationship
  field to a raw FK `UUID` scalar (e.g. `categoryId`, never the related
  entity type) instead of letting JPA's EAGER-fetch `@ManyToOne`/
  `@OneToOne` serialize nested entities, which would have contradicted
  spec §27's flat-FK-id UI contract. FK resolution in the service always
  goes through `relatedRepository.findById(...).orElseThrow(...)` — never
  `EntityManager.getReference()`, which would defer the not-found check
  past the point the service can convert it into the typed 404. **DD48
  amends DD18**: the entity's no-arg constructor is now `public`, not
  `protected` — a compilation prerequisite, since DD39 puts the service in
  a different package (`application`) than the entity (`domain`), and
  `protected` would not compile across that boundary. Resource path
  segments are pluralized and kebab-cased by a new dependency-free
  `naming.resource_path_segment` (DD45; `order_line` → `/api/order-lines`).
  55 new backend tests (`spring_generator` grows from 133 to 188), full
  631-test backend suite green, single PR (`size:exception`, confirmed by
  the user over the session's 400-line budget). `sdd-verify`/`sdd-archive`
  are the remaining steps.
- **SDD Cycle (`2026-09-18-spring-boot-generator-relationships-enums`) is
  implemented** (`backend/apps/spring_generator/`, spec §22 — second
  slice, extends the core cycle above): `generate_table_sources(table)`
  now emits FK-bearing and enum-bearing tables instead of rejecting them.
  A `Column` that is part of a FK renders as `@ManyToOne`+`@JoinColumn`,
  or `@OneToOne`+`@JoinColumn(..., unique = true)` when the FK's column
  set exactly matches one of the table's own `unique_constraints`; a
  self-referencing FK (`Category.parent -> Category`) generates cleanly
  with no special-casing and no import, because the referenced
  entity/enum always lives in the same `{base_package}.domain` package
  (DD27). A `Column` with `enum_type_name` set renders as
  `@Enumerated(EnumType.STRING)` typed `pascal_case(enum_type_name)`. New
  pure `generate_enum_source(enum_type, *, base_package) -> GeneratedFile`
  (`emit/renderer.py` + new `emit/templates/Enum.java.j2`) turns a
  `relational_mapping.domain.schema.EnumType` into a standalone
  annotation-free Java `enum`, with SCREAMING_SNAKE_CASE constants
  (`in_progress`/`InProgress`/`in-progress`/`IN PROGRESS` all converge on
  `IN_PROGRESS`) and the verbatim source label preserved via a
  `getLabel()` accessor — the DD32 recovery hook for a future DDL/DTO
  slice. `reject_out_of_scope`'s check set narrowed to non-UUID/composite
  PK, discriminator, and (newly) composite FK, in that fixed order;
  `ForeignKeysUnsupportedError` was renamed to
  `CompositeForeignKeyUnsupportedError` (no back-compat alias — its only
  two consumers were inside this app) and a new
  `UngeneratableSourceError` root now sits above both
  `UngeneratableTableError` and the new `UngeneratableEnumError` branch
  (`EmptyEnumTypeError`, `DuplicateEnumConstantError`). `javatypes.py` is
  untouched — FK and enum columns bypass its scalar `ColumnType` lookup
  entirely at both call sites in `context.py` (the field builder and the
  import-collection loop), which is what makes a bare `ENUM` column
  without `enum_type_name` the only remaining path to a rejection instead
  of a `KeyError`. 40 new backend tests (`spring_generator` grows from 93
  to 133, including `test_rejections.py`'s DD35-order rewrite and
  `test_determinism.py`'s widened `hypothesis` strategies proving DD36
  needed no new ordering rule), full 576-test backend suite green,
  single PR (`size:exception`, confirmed by the user over the session's
  800-line budget). `sdd-verify`/`sdd-archive` are the remaining steps.

## Pending (status against spec section 37)

This is the spec's own recommended implementation order, kept as a reference
list. **Status as of 2026-09-19:** items 1–6, 8, 9 and 11 are done and
archived; item 12 is partial (see the paragraph after the list); items 7
(Undo/Redo) and 10 (Presence) have no dedicated archived cycle; items 13–26
are not started.

1. `CanonicalUmlModel`
2. `ProjectDocument` + `DiagramLayout`
3. Validation engine
4. `UmlCommand` + Command Bus
5. Canvas (Cytoscape.js)
6. Persistence (Django ORM)
7. Undo/Redo
8. Auth + ownership
9. Realtime (Django Channels + Daphne)
10. Presence
11. UML → RelationalModel
12. Spring Boot backend generator
13. Generated backend compilable
14. OpenAPI
15. Postman collection
16. Domain Manifest
17. Frontend generator
18. Generic CRUD (generated apps)
19. `AssistantCommand`
20. Text → command (ONNX Runtime + Optimum)
21. Executor
22. STT (Vosk, Spanish, local)
23. Voice → command
24. Android via Next.js PWA + Capacitor (generated output)
25. XMI 2.1
26. Image → UML (Moondream)

SDD Cycle 1 (`canonical-uml-model`, items 1–3) was verified and archived on
2026-09-05; the command bus (item 4) was archived on 2026-09-12. Both are in
`openspec/changes/archive/`.

Item 12 (Spring Boot backend generator) now has six archived text-only slices:
`2026-09-18-spring-boot-generator-core` (scalar-only tables,
`domain/`+`persistence/`), `2026-09-18-spring-boot-generator-relationships-enums`
(FK relationship fields, enum fields, and standalone enum source),
`2026-09-18-spring-boot-generator-application-api-layer` (DTOs, service, REST
controller, and shared error handling — `application/`, `application/dto/`,
`api/`, `errors/`), `2026-09-19-spring-boot-generator-inheritance` (archived,
committed as `1f51d6c`: discriminator-backed Single Table tables now emit root/subclass
domain entities plus exactly one root repository; no inheritance DTOs, services,
controllers, or subclass repositories), and
`2026-09-19-spring-boot-generator-config-layer` (archived, committed as `45225a4`:
`generate_project_config_sources()` emits exactly one in-memory
`src/main/resources/application.yml` with only six required no-default
environment placeholders including `JPA_DDL_AUTO`, no dialect/platform setting,
no filesystem effects, and no Java `config/` classes). Still out of scope for a future slice:
inheritance API behavior, bidirectional `@OneToMany`, `@ManyToMany`/
`@JoinTable`, filtering/search (pending a §33 generation-metadata extension),
relation-navigation sub-resource endpoints, broader `config/` layer generation,
and broader generated-project behavior beyond the now-archived orchestrating caller.
`generate_model_sources(...)` walks a whole `RelationalModel`, combines per-table/per-enum output,
calls `generate_shared_error_sources` exactly once, calls the config singleton once per generated project,
and rejects exact duplicate output paths before returning an aggregate. Item 13 (generated backend
compilable) is now **slice 1 of 3 done** via `2026-09-19-spring-boot-project-scaffold`
(pure scaffold text: `build.gradle`, `settings.gradle`, `Application.java`, plus
`generate_project_sources`). Slices 2 (`generated-project-compile-check`) and 3
(`generated-project-boot-smoke`) still need a JVM/Gradle host, which does not exist
in repo infra, so nothing compiles yet.
