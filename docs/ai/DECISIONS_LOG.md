# Decisions Log

## 2026-09-21 — Delete a diagram / XML into a blank diagram (DD170, small direct change, no SDD)

- **DD170** Deleting is a hard delete of the `UmlDocument` row (deployments cascade); the runner stop is orchestrated in the HTTP view, not in `uml_documents.services`, so that app keeps its import boundary and never depends on `backend_deployments`. The stop is best-effort (runner TTL reaper and startup sweep are the backstop): a runner outage must not make a diagram undeletable. Importing XML into an existing diagram is allowed only while it is blank (no classes and no relationships, checked under the same row lock as commands, 409 `document_not_empty` otherwise) so an import can never silently destroy work; it keeps the user's diagram name and bumps the revision once instead of creating a new document.

## 2026-09-21 — Cloud deployment, stage 2 (DD169, small direct change, no SDD)

- **DD169** Single-VM deploy is a standalone `docker-compose.prod.yml` (no override of the dev file, so dev is untouched) with Caddy as the only published service (80/443; `/gen/*` -> runner, `/api/*` and `/ws/*` -> backend, rest -> frontend; admin and the runner management API are not routed). The runner reaches Docker only through `tecnativa/docker-socket-proxy:0.3.0` on an `internal` network (`DOCKER_HOST=tcp://socket-proxy:2375`; `docker.from_env()` already honours it, so no runner code changed). Permissions actually needed, verified by a full build/run/stop plus image pull: `CONTAINERS=1 IMAGES=1 NETWORKS=1 VOLUMES=1 POST=1` (0.3.0 has no separate DELETE switch; `POST=1` covers POST/PUT/DELETE); `/info`, `/build`, `/swarm`, `/secrets`, `/system/df` answer 403. The proxy restricts API sections only, not request bodies, so the runner's own `_create` guard stays the control for image/mount/privilege. The runner's startup sweep removes every `modelia.managed` resource on the shared daemon, so do not run two runners on one Docker host. The site and API share one origin (`NEXT_PUBLIC_API_URL=https://$APP_DOMAIN`), so cookies are `Lax`+`Secure` and CORS only serves the websocket origin check.


## 2026-09-21 — Running generated backends: runner service (DD168, small direct change, no SDD)

- **DD168** Generated backends run through a separate `runner` service, never through Django: Django stores `Deployment` rows and calls the runner over HTTP with a bearer token; only the runner mounts the Docker socket (stage 2: restricted docker-socket-proxy). Deviations from the first design, all to stay simple and safe: (a) no Django background thread, because the runner builds asynchronously (202) and `GET .../deployments/latest` pulls its state into the row; (b) the zip is sent as the raw `PUT` body (`application/zip`, id in the URL, org slug in the query) and repacked in memory to a tar streamed into a per-deployment named volume with `put_archive`, so no host path is ever bind-mounted; (c) the build image is runner env (`RUNNER_BUILD_IMAGE`, default equal to `gradle_runner_image()`), never sent by Django, because the runner cannot import `versions.py`; (d) per-deployment network is `internal` (the app and its Postgres have no internet route); (e) the runner keeps deployment state in memory and sweeps every labelled resource at startup, so a restart cannot orphan anything (Django maps a runner 404 to `stopped`). The runner is also the reverse proxy (`/gen/{id}/...`), so the cloud reverse proxy only needs to route `/gen/*` to it.

## 2026-09-20 — XMI interop dialect (small direct change, no DD number)

- Export dialect is XMI 1.1 / UML 1.3 exactly as Enterprise Architect exports it (mirrored from a real sample), windows-1252, deterministic. Import reads that dialect (verified) plus a basic XMI 2.1 (hand-written fixture only, unverified against real EA).
- Canonical direction: the whole (diamond) end of aggregation/composition is `source`; UML 1.x marks the whole end, UML 2 marks the part end (the 2.x reader flips it). EA class boxes map to canonical centre positions.
- Import never fails on recoverable content: everything skipped or assumed is a warning; only non-XML, forbidden constructs (defusedxml), > 5 MB, non-XMI or zero classes fail (422 `invalid_xmi` / `unsupported_xmi`).
- `import-xmi` router is registered before `documents_router` (route shadowing by `/{doc_id}`).

## 2026-09-20 — Change archived: CRUD restricts operations, manifest slice (DD160-DD167) (`crud-restricts-operations`)

Status: verified (PASS WITH WARNINGS, 0 critical) and archived, uncommitted (24/24 tasks, task 9.1 closed at archive; Strict TDD; backend 1214 -> 1267 passed, `apps/relational_mapping` 170, `apps/domain_manifest` 146, ~570 authored lines, no `size:exception`; archived to `openspec/changes/archive/2026-09-20-crud-restricts-operations/`; deltas merged: `generation-profile` 9 -> 10 requirements, `domain-manifest-export` stays at 15 with 1 renamed and 3 modified; accepted warnings: M3 equivalent mutant covered by a direct test, no safety-net column in apply-progress, private `_OPERATIONS` / `_operations` imported by tests; the last commit is `20bf71c feat(spring-generator): add filtering/search, sort validation and defaultSort`). Slice 1 of 2: the declared table `crud` / `readOnly` now restrict `operations[]` in the Domain Manifest. Slice 2 `spring-generator-crud-restriction` (generator consumes the same function) is a separate later change. Same text as `openspec/changes/crud-restricts-operations/design.md` (parity).

- **DD160** `OPERATION_NAMES` (`("create","findById","update","delete","list","count")`, the controller's declaration order) and the pure `effective_operations(profile: TableProfile | None) -> tuple[str, ...]` live in `backend/apps/relational_mapping/domain/profile.py` (zero new imports, so the module-purity scenario still covers it). Rejected: a new `domain/operations.py`; returning list/set or `CrudOperation` members.
- **DD161** Truth table. `profile is None` and `TableProfile()` are identical. `crud=None` gives all six; a declared `crud` maps CREATE -> `create`, READ -> `findById, list, count`, UPDATE -> `update`, DELETE -> `delete`; `read_only=True` intersects with the read operations (never adds); `crud=()` gives `()`. Output is always a tuple in `OPERATION_NAMES` order regardless of the declared `crud` order. An empty result is reachable only by a declared empty `crud` or `read_only=True` with a `crud` lacking READ. No parse-time rejection of `readOnly` + write `crud` (DD133 "never invent").
- **DD162** Decoupling: `Table.effective_operations` is a non-field `@property` on `apps.relational_mapping.domain.schema.Table`, read duck-typed by `builder/entities.py`. Rejected: (a) importing the function in the builder (breaks the import guard), (b) a guard amendment in the DD154 style, (c) caller injection (`cli.py` cannot import the app either and it changes a public signature). `tests/test_builder_decoupling.py` stays unedited; a property (not a field) leaves `__eq__`, `__hash__` and `repr` of the frozen `Table` unaffected. Direct attribute access, no silent all-six fallback.
- **DD163** `entities._operations(resource_path, names)` filters the `_OPERATIONS` rows while iterating `_OPERATIONS` in its declared order (never `names` order). In `build_entity` the path segment is computed BEFORE suppression, then `resource_path` becomes `None` when the effective set is empty, so an invalid table name still raises and no inheritance table is newly validated. `builder/profile.py` is untouched: `crud` / `readOnly` are still emitted verbatim under `entity["profile"]`.
- **DD164** The single owner of "`resourcePath` is `null` iff `operations[]` is empty" is the `CRUD Operations` requirement of `domain-manifest-export` (generalizes the inheritance coupling). `Entity Content` and `Manifest Derivation and Purity` stay unmodified.
- **DD165** `Endpoint Drift Guard` and `test_computed_paths_equal_the_paths_springdoc_served` are unchanged (the sample declares no profile). Latent constraint: `resources <= computed` holds only while every entity with a resource path keeps a suffix-`""` operation (`create` or `list`); a future sample declaring e.g. `crud: ["delete"]` would break it.
- **DD166** Transient manifest/generator divergence until slice 2: between the two slices a profile-restricted model yields a manifest with fewer operations than the generator's still-six endpoints. Accepted (single release, no committed fixture uses a restricted model, so no golden, `docker-compose.yml` or `scripts/` change). Slice 2 removes it by consuming the same function.
- **DD167** DD147 is retired for the manifest by DD160-DD163 and fully retired once slice 2 lands. The DD147 line above is annotated in place, never deleted.

Evidence: RED-first per phase (import error, then missing property, then 8 red manifest tests); at apply time backend `1214 -> 1261 passed`, `apps/domain_manifest` 140 (final after the verify fix: backend 1267 passed, `apps/domain_manifest` 146), `apps/relational_mapping` 170; mutations M1-M5 each turned the suite red and were reverted byte-identical. Deviation noted for verify: mutation M3 (iterate `names` instead of `_OPERATIONS`) is behaviourally equivalent through `build_entity` because `effective_operations` already returns canonical order, so a direct `_operations(path, out_of_order_names)` test was added to kill it. `builder/profile.py`, `tests/test_builder_decoupling.py`, `apps/spring_generator`, `frontend/`, `docker-compose.yml` and `scripts/` are untouched. No commit or push was performed.

## 2026-09-20 — Change applied: Generated Spring API filtering/search (`2026-09-20-generated-spring-api-filtering-search`)

Status: verified, archived and committed as `20bf71c feat(spring-generator): add filtering/search, sort validation and defaultSort` (status line corrected on 2026-09-20 after HEAD moved). The Spring generator now consumes the generation profile carried by relational mapping: searchable column filters, sortable allow-lists, and table `defaultSort`. Searchable non-inheritance tables emit one `application/<Entity>Specifications.java`; repositories extend `JpaSpecificationExecutor` only when searchable filters exist; controllers bind optional Java-field-name query parameters; services compose `Specification` objects, validate every sort property, apply default sort only to unsorted `Pageable`, and preserve no-profile / false-unset output byte-identically.

Decision: invalid sort requests use generated service-side `IllegalArgumentException`, and the generated shared `GlobalExceptionHandler` maps `IllegalArgumentException` to `400 Bad Request`. This was the smallest bounded handler change needed to satisfy the 400 contract without adding a new generated error class.

Decision: the previous generation-runner assertion that declared true profiles were Spring-output neutral is superseded. True `searchable` / `sortable` metadata intentionally changes generated Spring output; false or unset profile values remain output-neutral and are now the pinned compatibility case.

Evidence: focused RED failed before implementation on missing `build_specification_context`; focused GREEN passed (`68 passed`); full Spring generator passed (`354 passed`); Docker backend passed (`1214 passed`); frontend configured strict command passed (`55 files / 351 tests`). Size exception was accepted for the cohesive generator/test slice; no commit or push was performed.

## 2026-09-20 — Change archived: UML generation profile panel (frontend slice) (`2026-09-20-uml-generation-profile-panel`)

Status: verified, archived and committed as `4b923aa feat(uml-panel): add generation profile sidebar panel with tri-state controls`. Archive composed five ADDED requirements into `openspec/specs/web-uml-canvas/spec.md` and moved the active change to `openspec/changes/archive/2026-09-20-2026-09-20-uml-generation-profile-panel/`. Tasks were 14/14 complete with no unchecked implementation markers at the final archive gate. Verification recorded PASS_WITH_WARNINGS with 0 blockers and 0 critical findings; `cd frontend && npm test` passed 55 files / 351 tests, the focused lib + panel run passed 39 tests, `cd frontend && npm run lint` passed, and no backend changes were made. The optional `npx tsc --noEmit` warning about a broad test-helper mock type remains recorded as a non-blocking quality warning. No commit or push was performed, and `.pi/` remains excluded.

Decision: archive accepted the warning because native status admitted archive and verification recorded no blockers or critical findings. The canonical merge was non-destructive because the delta contained ADDED requirements only; no REMOVED or MODIFIED requirement blocks were applied.

## 2026-09-20 — Change applied: UML generation profile panel (frontend slice) (`2026-09-20-uml-generation-profile-panel`)

Status: applied at the time of writing; since verified, archived and committed as `4b923aa` (see the archived entry above). This frontend-only slice exposes the existing backend `SetGenerationProfile` command through the UML document sidebar. `UmlCommandIn` gained the exact `{ type: "SetGenerationProfile"; element_id: string; profile: Record<string, unknown> | null }` variant while `submitCommand` stayed unchanged. `GenerationProfilePanel` is presentational: targets are derived from current `classes`, metadata is guarded as untrusted, tri-state controls distinguish unset from false, `crud` maps to `["create", "read", "update", "delete"]` or `[]`, all-unset submits `profile: null`, and `ApiError.detail` is displayed in Spanish UI flow. The sidebar Card title is `Perfil de generación`.

Decision: keep all helpers local to the panel for now (target derivation, record guard, prefill, payload building). No new dependency or custom UI primitive was added; the existing native `Select` component was enough and remains accessible through `Label htmlFor`. A lint finding against synchronous setState in an effect led to a derived-base-values plus local-edits state model instead of an effect-driven prefill reset.

Evidence: focused RED/GREEN runs over lib + panel tests; final `cd frontend && npm test` passed (55 files / 351 tests), and `cd frontend && npm run lint` passed. Scope boundaries held: no backend, persistence, canvas, WebSocket, Flutter/mobile, generated-code, or `defaultSort` changes. Size exception was accepted by the user.

## 2026-09-20 — Change applied: UML generation profile authoring (DD151-DD159) (`uml-generation-profile-authoring`)

Status: verified, archived (`archive/2026-09-20-uml-generation-profile-authoring`) and committed as `07fb611 feat(uml-commands): author generation profile via SetGenerationProfile command` (31/31 tasks, Strict TDD; status line corrected on 2026-09-20 after HEAD moved). Backend slice 1 of 2: a generation profile can now be authored through the command API (`POST` command `SetGenerationProfile`); the frontend panel is slice 2 (`uml-generation-profile-panel`). Numbers: backend 1107 -> 1184 passed, `apps/uml_commands` 86, `apps/uml_documents` 134, `relational_mapping` + `domain_manifest` + `spring_generator` 588. Authored size ~1208 lines (source ~221, tests ~987, plus docs): **`size:exception` accepted** (standing user choice; tests were not trimmed, design estimated ~525 and the budget 800). Untouched (git diff empty): `frontend/`, `apps/uml_modeling`, `apps/relational_mapping`, `apps/spring_generator`, `apps/domain_manifest`, `docker-compose.yml`, `scripts/`.

- **DD151** one command `SetGenerationProfile(element_id, profile | None)`; the server infers table-level vs column-level from the model (mirrors `_collect_profiles`), the client sends no `level`.
- **DD152** the command carries the raw validated `Mapping`, stored verbatim under `generation_metadata[element_id]["profile"]`; `apps/uml_commands` keeps its pure import guard (no `apps.relational_mapping`).
- **DD153** semantic validation lives in `services.submit_command` inside the `select_for_update()` row lock, after `_to_project_document(row)` and before `apply(...)`; the handler never raises (DD6). Parser errors become `InvalidCommandPayloadError` with the message verbatim (422, `invalid_command_payload`).
- **DD154 (first named import-guard exception in this codebase)** `apps.relational_mapping.mapping.profile_parser` is the only `apps.relational_mapping` module `uml_documents` may import (exact-match `_ALLOWED_EXACT_MODULES`; every other `apps.relational_mapping.*` target joins `_DISALLOWED_PREFIXES`). Rejected: copying the 12 rules (write/generation drift), moving the parser, widening to a prefix (would admit `mapper`, `schema`). Pinned by `test_relational_mapping_exception_is_exactly_one_module` and synthetic `mapping.mapper` / `apps.users` targets that still fail. `services.py` imports `InvalidGenerationProfileError` from `profile_parser` too (R1), never from `mapping.errors`.
- **DD155** level inference always runs, so an unknown id is a 422 even on a clear (`None`/`{}`); parsing runs only when a body is present.
- **DD156** the handler owns exactly the `"profile"` key: sibling keys are preserved, an emptied entry is pruned, an unknown id returns the model unchanged.
- **DD157** `defaultSort.attribute` is resolved at write time against the class's own attributes plus, for an inheritance root, its transitive descendants' attributes (the mapper attaches `Table.profile` to the STI root).
- **DD158 (correction of the naive rule)** `RemoveClass` (and `RemoveAttribute`) share one pruning primitive `prune_generation_metadata` that also clears a *foreign* root's `defaultSort` pointing at a removed descendant attribute; the same-class-only rule was wrong under DD157 and would make generation fail on a dangling id.
- **DD159** relationship- and operation-keyed entries are not pruned (inert in `_collect_profiles`); removing a `GENERALIZATION` edge can leave a root `defaultSort` on a non-descendant attribute, accepted and deferred to the slice that resolves `defaultSort` to a column.

Persisted-scenario rescoping (R2): the spec scenario about persisted layout was rescoped to what this change actually delivers (the profile survives the document codec round trip and reaches `map_to_relational`), not a layout guarantee. Two pinned counts (`nine` command types) were found by the R2 sweep and updated to ten (`test_commands`, `test_dispatcher`, `uml_documents/test_schemas`).

Accepted warnings: (1) design mutation 8 half "outside the lock" is an equivalent mutant single-threaded; only the "after apply" half is testable and is killed by a spy on `apply` (`transaction.atomic` would roll the row back either way). (2) Tests 2.9, 3.1 and 3.2 are characterization tests that pass at once (R5); they are proven by mutation (S1 a `def remove_class` in `schemas.py`, S3 the gate removed from `submit_command`, M5 DD158 narrowed), not by a prior RED. (3) The cascade tests of 1.6 shared the collection-error RED with the prune tests and are proven by M5. (4) `size:exception` as above. Mutants M1-M10 and S1-S3 were each reverted and the affected apps re-run green.

## 2026-09-20 — Change archived: Manifest generation profile (DD142-DD150) (`manifest-generation-profile`)

Status: verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `cdae44c`; archived to `openspec/changes/archive/2026-09-20-manifest-generation-profile/`. `sdd-apply` implemented 23 of 24 tasks in Strict TDD; task 11.4 (the main-spec heading rename `Declared-Facts-Only Exclusion` -> `Declared-Facts-Only Emission` plus the Purpose fix) was closed at archive, so 24/24. The delta merged into `domain-manifest-export` (now 15 requirements: 1 renamed, 2 modified, 5 added). Authored size ~419 lines, no `size:exception` needed. Accepted warnings: the M3 mutant is equivalent (the `profile is None` guard is redundant); task 11.4 was closed at archive; `EXCLUDED_KEYS` equality is not asserted explicitly; the 'foreign id' scenario is covered by an id matching no column. The Domain Manifest (schema v1, `schemaVersion` unchanged) now emits the declared generation profile carried by the mapper (`Table.profile` / `Column.profile`): entity `profile` (`auditable`, `readOnly`, `crud`, `defaultSort`) and attribute `profile` (`searchable`, `sortable`, `readOnly`), each key present only when declared. Numbers: `apps/domain_manifest` 88 -> 125 passed, backend 1070 -> 1107 passed.

**DD131 is superseded** by this change: it said the manifest emits none of `searchable`, `sortable`, `defaultSort`, `auditable`, `readOnly` and never `generation_metadata`. Those five keys are now emitted iff declared (DD145, DD148); `aliases`, `entity` and `generation_metadata` are still never emitted.

- **DD142** new pure module `builder/profile.py` with `build_column_profile(profile)` and `build_table_profile(profile, resolve_attribute)`; profile objects are read duck-typed with `getattr(profile, "<snake_name>", None)`, with no `apps.relational_mapping` import (the decoupling guard scans it automatically).
- **DD143** `ManifestError(ValueError)` moves to `builder/errors.py`, imported by `manifest.py` and `entities.py`, still re-exported from `apps.domain_manifest.builder`; breaks the `entities` <-> `manifest` import cycle.
- **DD144** `defaultSort.attribute` is resolved in `entities.py` by `_resolver(table)` through the shared `attributes.attribute_name(column)`, so it equals the emitted `attributes[].name` by construction. Discriminator excluded; synthetic, foreign and unknown ids raise `ManifestError("table 'vehicle' declares defaultSort on unknown attribute id 'attr-x'")`. Key is `attribute`, never `attributeId` (`test_determinism` forbids `id` keys).
- **DD145** omission rule: a key whose value is `None` is omitted; zero keys or an absent profile emit no `profile` key. A declared `false` is kept (test is `is not None`, not truthiness). `null` is not used for these keys (DD125's fixed-key rule stays for the pre-existing keys).
- **DD146** enum members are read through `_text(value) = getattr(value, "value", value)`: `crud` is a `list[str]` in the mapper's canonical order, `direction` a plain `"asc"`/`"desc"`.
- **DD147 (tech debt)** the declared `crud` does NOT filter `operations[]`, which keeps describing what the generated controller actually serves (all six operations); the generator ignores `crud` today. Revisit when the generator consumes `crud`. **[Retired by DD167 (manifest, change `crud-restricts-operations`) / slice 2 `spring-generator-crud-restriction` (generator); text kept as history.]**
- **DD148** the test guard `EXCLUDED_KEYS` narrows to `["aliases", "entity", "generation_metadata"]` (the proposal text is stale on this); the five newly legal keys get positive emission tests.
- **DD149** `test_profile_output_neutral.py` is retargeted, not deleted: a profile-carrying model changes the manifest and contains `profile`; empty `generation_metadata` and the sample model still produce the same manifest.
- **DD150** no `docker-compose.yml`, `scripts/` or gate change and no new golden: the sample model declares no profile, so `docs/domain-manifest.json` is byte-identical by construction, pinned by the unedited tripwires `test_sample_entity_header`, `test_sample_attribute` and `test_determinism`.

Apply notes: mutation checks M1-M10 were run and reverted (tree green after). M3 (dropping the `profile is None` guard) survives: it is an equivalent mutant, because `getattr(None, field, None)` already yields `None`; the guard is kept as pinned in the design. Tests for tasks 6.1, 7.1 and 8.1 pass by construction and are protected by the mutation checks (M9/M10, M1-M2). Archive-time still pending: rename `Declared-Facts-Only Exclusion` to `Declared-Facts-Only Emission` in the main spec and fix its Purpose text (task 11.4).

## 2026-09-20 — Change archived: Relational generation metadata (DD132-DD141) (`relational-generation-metadata`)

Status: verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `284881e`; archived to `openspec/changes/archive/2026-09-20-relational-generation-metadata/`. Delta specs `generation-profile` (new, 9 requirements) and `relational-mapping` (4 modified, 3 added; now 17 requirements) are merged into main specs. Final numbers: backend suite 1070 passed (987 before), `apps/relational_mapping` 138 passed, `apps/domain_manifest` 88 passed, 34/34 tasks; authored size ~960 lines accepted as `size:exception`. Accepted warnings: `Table`/`RelationalModel` are already unhashable (spec amended); the manifest half of the neutrality test lives in `apps/domain_manifest/tests`; `InvalidGenerationProfileError` is not imported in `mapper.py` (the design wiring table lists it, it is not needed); three tests pass by construction (protected by mutation checks).

`sdd-apply` implemented all 34 tasks in Strict TDD. `apps.relational_mapping` now parses the reserved `"profile"` key of `CanonicalUmlModel.generation_metadata` and carries it on `Table.profile` / `Column.profile`. No consumer reads it (Domain Manifest and Spring output byte-identical). Unblocks the DD131 emission slice.

- **DD132** profile value objects live in their own module `domain/profile.py` (`SortDirection`, `CrudOperation`, `DefaultSort`, `ColumnProfile`, `TableProfile`), not in `schema.py`.
- **DD133** every profile field is tri-state (`X | None`, `None` = undeclared); a `"profile"` yielding zero declared keys canonicalizes to `None`.
- **DD134** hashable by construction; `crud` is a `tuple` in canonical order `create, read, update, delete`, never a set/list.
- **DD135** `mapping/profile_parser.py` is a pure, model-free parser (`parse_table_profile` / `parse_column_profile`, one raw entry each), pinned by an AST import-guard test.
- **DD136** `InvalidGenerationProfileError` subclasses `UnmappableModelError` in `mapping/errors.py` (one catch for every mapper failure).
- **DD137** table-level keys `entity, auditable, readOnly, crud, defaultSort`; column-level `searchable, sortable, readOnly`; levels disjoint except `readOnly`, a misplaced key raises.
- **DD138** `aliases`, `required`, `unique`, `source`, `confidence` and every key outside `"profile"` are out: ignored, never validated.
- **DD139** `entity` is parsed and carried, no mapper behaviour branches on it.
- **DD140** `defaultSort.attribute` is stored as an unresolved `ElementId`; resolution to a column is deferred.
- **DD141** profiles are collected up front by `_collect_profiles` (in `generation_metadata` order) before any table work, so the first malformed entry aborts deterministically. STI: only the root class's profile becomes the `Table.profile`; synthetic columns (`id`, `class_type`, FK, join table) never carry one.

Apply notes: within one entry, rules are applied in numeric order 1..12 (first failing rule raises; pinned by a two-fault test). `Table` is not hashable (pre-existing `MappingProxyType` field), so hash assertions target `Table.profile` and `Column`. The manifest half of the output-neutrality test lives in `domain_manifest/tests/` because a guard forbids any other app importing `apps.domain_manifest`.

## 2026-09-20 — Change archived: Generated project Domain Manifest (`generated-project-domain-manifest`)

`sdd-apply` implemented all 31 tasks in Strict TDD (slice 1: pure builder, serializer, CLI, 87 tests) plus a proven gate step (slice 2). §37 item 16: a deterministic `docs/domain-manifest.json` (schema v1) describing the generated backend (entities, attributes, relationships, enums, CRUD operations, subtypes), derived offline from the `RelationalModel`. Status: archived (PASS WITH WARNINGS, 0 CRITICAL), committed as `d2069a5`. Evidence: `openspec/changes/archive/2026-09-20-generated-project-domain-manifest/gate-evidence.md` and archive-report.md.

- **DD121** new app `apps.domain_manifest` (no models, no migrations): `builder/` (attributes, relationships, entities, manifest), `serialize.py`, `cli.py`, `apps.py`; registered right after `apps.postman_export`. It is not folded into `postman_export` (that would mix OpenAPI conversion with model derivation).
- **DD122** source of truth is the `RelationalModel` (`sample_model`), not the captured `docs/openapi.json` and not the generated tree. Endpoints are computed, then cross-checked by the drift guard (DD129).
- **DD123** `builder/` imports `apps.spring_generator.emit.naming` directly; the decoupling guard allowlists exactly that module and rejects any other `apps.spring_generator.*`, Django, `generation_runner` and `postman_export`. The `oneToOne` rule (FK column set equals a unique constraint) is restated locally, not imported from `emit/context`.
- **DD124** `serialize.py` is duplicated from `postman_export` instead of shared. `cli.py` is glue: it may import only `apps.generation_runner.samples.sample_model`, never calls `django.setup()`.
- **DD125** schema v1: fixed key set per object (`null`, never an omitted key), neutral type names from a closed `ColumnType` map, entities/enums/subtypes/unique constraints sorted by name, relationships by `field`, attributes in table-column order, six CRUD operations in the controller order. FK attributes keep the `Id` suffix; the discriminator column is excluded.
- **DD126** `resourcePath` is `null` iff `operations` is `[]`; this holds exactly for inheritance tables (`vehicle`), which the generator emits as entities + repository only. Real sample: 6 entities, 5 resources, no `/api/vehicles`.
- **DD127** determinism: `json.dumps(indent=2, sort_keys=True, ensure_ascii=False) + "\n"`, written with `newline="\n"`; no ids, timestamps or set iteration; fixed filename `domain-manifest.json`.
- **DD128** compose service `generate-manifest` mirrors `generate-postman`: profile `jvm-verify`, `entrypoint: []`, `user: root`, `./backend:/app:ro` + `generated_project:/generated`, no `depends_on`, no `rm -rf`, literal command array; gate step 4 after `generate-postman`, no new exit code (forwards the CLI 1 or 2 under `set -euo pipefail`).
- **DD129** drift guard: the resource paths and `operations[].path` of the manifest must equal the `paths` keys of the committed `postman_export/tests/fixtures/api-docs.json` in both directions (read-only). Mutation-checked (`/count` renamed: 6 failures, reverted).
- **DD130** pytest proves builder + CLI only (never reads `scripts/` or `docker-compose.yml`, DD101/DD120); the compose/script half is proven by the gate (exit 0, `domain-manifest.json` 12496 bytes) and one negative check (`--out-dir` under `docs/openapi.json`: CLI `error: [Errno 20]`, exit 1, gate exit 1; reverted with equal sha1).
- **DD131** only declared or generated facts are emitted: no `searchable`, `sortable`, `defaultSort`, `auditable`, `readOnly`, `aliases`, no `generation_metadata`. Section 33 split note: the UML metamodel (§33 UML side) carries classes/attributes/relationships, whereas those flags belong to the project's own profile (`generation_metadata`), which the mapper does not carry yet. Follow-up: the mapper must carry `generation_metadata` before these fields can exist; emitting them with defaults would be indistinguishable from real intent.

Deviations found during apply (no DD132+ was needed; task 1.2 found no contradiction: the read operation is `findById` in the design and the spec was aligned):

- Naming errors (`InvalidJavaIdentifierError`, `InvalidResourcePathError`) extend `Exception`, not `ValueError`; `builder/manifest.py` imports them through `emit.naming` (allowlisted path) and wraps them in `ManifestError(ValueError)`. The CLI catches `(ValueError, OSError)` and builds the manifest before `mkdir`, so nothing is written on rejection.
- The type map is keyed on the `ColumnType` member name (string), so the builder imports no `relational_mapping` module.
- Guard scope rule: the AST guard covers `builder/**` and `serialize.py`; `cli.py` is checked separately (only the sample-model import allowed).
- Entities are sorted by `name` (so `Customer` first), not by table order.

Totals: backend 987 (900 + 87 in `apps/domain_manifest`). Authored size 811 lines in slice 1 (259 non-test, 552 tests) plus slice 2 (compose 17, script 4, docs, evidence): `size:exception` accepted by the orchestrator decision; split-vs-exception is asked again at commit time.

## 2026-09-20 — Change archived: Generated project Postman collection (`generated-project-postman-collection`)

`sdd-apply` implemented all 31 tasks in Strict TDD (converter + CLI); the compose/script half is proven by recorded gate runs (DD101). §37 item 15: the smoke exports the real `/v3/api-docs` body and a new offline app `apps.postman_export` turns it into a Postman Collection v2.1.0 plus an environment file, as a third gate step. Status: verified (PASS WITH WARNINGS, 0 critical) and archived, committed as `8bb9fd0`

- **DD108** `scripts/boot-smoke.sh` copies `$BODY` to the relative `docs/openapi.json` as the LAST statement before `PASS` (`mkdir -p docs || die 8`, `cp ... || die 8`; new exit 8). Any later `_http` call would overwrite `$BODY`; `generate-project` wipes the volume so the export cannot go stale.
- **DD109** new app `apps.postman_export` (no models, no migrations): pure `converter/` plus plain `__main__` `cli.py`; registered after `apps.generation_runner`; a decoupling guard forbids Django/generator imports and any importer of the app.
- **DD110** the converter is pure stdlib Python; no `openapi-to-postmanv2` Node container.
- **DD111** fixed output names `postman_collection.json` / `postman_environment.json`; `info.name` = OpenAPI `info.title`.
- **DD112** determinism: items sorted by (path, method), folders by tag; no `_postman_id`/ids/timestamps; `json.dumps(indent=2, sort_keys=True, ensure_ascii=False)` + `"\n"`, written with `newline="\n"`.
- **DD113** compose service `generate-postman`: profile `jvm-verify`, no `depends_on` (it would re-run the generator and wipe the export), no `rm -rf`, literal command array; third sequential gate step.
- **DD114** fixture first: the real body was captured by the gate and committed as `tests/fixtures/api-docs.json` (14408 B, springdoc 3.1.1, 2026-09-20, all five controllers) before any fixture-dependent test.
- **DD115** exactly one status test per request on the lowest documented 2xx code; no id chaining, no `auth` block; `baseUrl` exists only in the environment file (`--base-url`, default empty).
- **DD116** the real `pageable` query param is `required: true` with a `$ref` to the `Pageable` schema (page int min 0, size int min 1, sort array), not an inline object: it is resolved and expanded into `page=0`, `size=20` (one named constant, Spring Data default) and a disabled empty `sort`.
- **DD117** `Page<T>` responses are flat named schemas (`PageCustomerResponseDto`); the converter never reads response bodies.
- **DD118** the fixture was kept whole rather than trimmed to Customer (not oversized).
- **DD119** an operation with no numeric 2xx documented gets no test event.
- **DD120** pytest cannot see `scripts/` or compose (DD101): proven by `gate-evidence.md`, gate exit 0 (three steps), negative A exit 8 and negative B exit 1, all reverted byte-identically.

Totals: backend 900 (840 + 60 in `apps/postman_export`). Authored size is about 1246 lines (source 363, tests 845, scripts/compose/settings 38), over the 800-line budget because of tests: `size:exception` recommended. Verified PASS WITH WARNINGS and archived; committed as `8bb9fd0`.

## 2026-09-20 — Change archived: Generated project OpenAPI via springdoc (`generated-project-openapi-springdoc`)

`sdd-apply` implemented all 22 tasks (Strict TDD for the Docker-free half; the bash half is proven by recorded gate runs). §37 item 14, part 1: the generated `build.gradle` now declares springdoc and the boot smoke asserts `GET /v3/api-docs`. Status: verified PASS WITH WARNINGS (0 CRITICAL) and archived; the commit is what remains. Evidence: `openspec/changes/archive/2026-09-20-generated-project-openapi-springdoc/gate-evidence.md`.

- **DD103** `SPRINGDOC_VERSION = "3.1.1"` lives only in `emit/versions.py`; it is the last field of `BuildScriptContext` and `renderer.generate_project_scaffold_sources` forwards it (without that kwarg Jinja raises `UndefinedError` due to `StrictUndefined`).
- **DD104** template line `implementation 'org.springdoc:springdoc-openapi-starter-webmvc-api:{{ springdoc_version }}'` after the Boot starters, before the postgres driver; no `-ui`, no actuator.
- **DD105** `scripts/boot-smoke.sh` asserts the document after the CRUD proof: `assert_status 200 GET /v3/api-docs` (exit 6 on non-200), then two pure-bash `case` needles `"openapi":` and `"/api/customers"` (new exit 7).
- **DD106** pytest pins the generated side only (oracle line, positive springdoc test, DD72 scan `\b3\.1\.1\b`, coordinate pin in `test_boot_smoke_contract.py`); the `/v3/api-docs` literal is unreachable from pytest (DD101).
- **DD107** gate recorded: first run green (exit 0, `GET /v3/api-docs -> 200`); negative check with a bogus needle exited 7 and was reverted. springdoc 3.1.1 (built on Boot 4.1.0) booted green on Boot 4.1.1, and `@RestControllerAdvice` did not break the endpoint; no fix-forward was needed.

Totals: backend 840 (836 + 4), `apps/spring_generator` 325, `apps/generation_runner` 68. Committed as `a834ca2`.

## 2026-09-19 — Decision: generated backend documents its API with springdoc-openapi (§25 vs §22)

Product decision resolved with the user before §37 items 14–16. `product-04-next-django.md` §25 says "OpenAPI nativo de Django Ninja", while §22 fixes the generated stack to Spring Boot with springdoc-openapi and states that the main application's stack and the generated stack are independent (§22, "no deberá sustituir Spring Boot por el framework utilizado internamente por la herramienta principal"). Django Ninja can only describe the Django API of Modelia itself, never the generated Spring backend, so §25 read literally is unimplementable. Decision: §22 wins. The OpenAPI document of the **generated** backend comes from springdoc-openapi (Postman collection and Domain Manifest derive from it); Django Ninja's native OpenAPI stays as the spec for **Modelia's own** API (`TECH_STACK.md`). Consequence for the next change: adding springdoc to `build.gradle.j2` needs its version single-sourced in `emit/versions.py` and a check that the springdoc release supports Spring Boot 4.1.1 (to confirm at explore).

## 2026-09-19 — Change applied: Generated project boot smoke (`generated-project-boot-smoke`)

`sdd-apply` implemented all 18 tasks (Strict TDD for the one pytest-reachable piece; the compose/bash half is proven by recorded gate runs). Slice 3 of 3 of spec §37 item 13. Verified (PASS WITH WARNINGS) and archived at `openspec/changes/archive/2026-09-19-generated-project-boot-smoke/`. The gate `bash scripts/verify-generated-project.sh` now also boots the compiled jar against a throwaway Postgres and runs one CRUD round-trip (201/200/204/404). Evidence: `openspec/changes/generated-project-boot-smoke/gate-evidence.md`.

Decisions (DD92-DD102, full rationale in the change `design.md`):

- **DD92** two services under the existing `jvm-verify` profile (`gen-db`, `jvm-boot-smoke`), no published ports; the JVM is reached over its own container loopback.
- **DD93** throwaway credentials come from `${GEN_DB_*:-default}` in compose only; `JPA_DDL_AUTO=create-drop`; Postgres data on `tmpfs`. **Amended at apply:** `gen-db` reads `GEN_DB_SERVER_PASSWORD` while the app reads `GEN_DB_PASSWORD`; with one shared variable the negative run changed both sides and passed with exit 0.
- **DD94** two sequential `run --rm` steps (`jvm-verify`, then `jvm-boot-smoke`), no `depends_on: jvm-verify`, so a Gradle failure keeps its own output.
- **DD95** cleanup is an `EXIT` trap running `docker compose --profile jvm-verify rm -sfv gen-db`, never `down`.
- **DD96** `scripts/boot-smoke.sh` is mounted `:ro` and run as `bash /scripts/boot-smoke.sh` (no dependence on the executable bit).
- **DD97** jar selection globs `build/libs/*.jar`, skips `-plain`, requires exactly one; no version literal in the script.
- **DD98** readiness polls `GET /api/customers/count` with `kill -0` fail-fast (exit 4) and a timeout (exit 5). **Refined at apply:** the failure dump lists `FATAL`/`Caused by` lines before the tail, because a stack trace hid the root cause.
- **DD99** one `_http` curl seam plus `assert_status`; typed exit codes 0/2/3/4/5/6. `curl 8.18.0` is present in `gradle:9.7.1-jdk21`, so no fallback was needed.
- **DD100** the created id is parsed in pure bash and checked against `^[0-9a-fA-F-]{36}$` before reaching any URL.
- **DD101** the only pytest addition is `apps/generation_runner/tests/test_boot_smoke_contract.py` (8 tests pinning generated literals); `docker-compose.yml` and `scripts/` are unreachable from the test process.
- **DD102** the negative case is `GEN_DB_PASSWORD=wrong bash scripts/verify-generated-project.sh`; observed exit 4 with `password authentication failed`, no `gen-db` left, no `wrong` in the dump.

Evidence: contract test characterization (passes immediately; two mutations made 2 of 8 tests red, then reverted); gate green three times, `BUILD SUCCESSFUL in 40s`, ready in 4-5s; negative exit 4. Totals: backend 836 (828 + 8), `apps/generation_runner` 67 (59 + 8). No generator source changed; no Maven Central flake occurred this time.

## 2026-09-19 — Cycle archived: Inheritance subclass Java class naming (`spring-generator-inheritance-subclass-naming`)

`sdd-archive` composed the delta spec into `openspec/specs/spring-boot-generation/spec.md` (2 MODIFIED requirements + 3 new scenarios, total requirements now 26), moved the change to `openspec/changes/archive/2026-09-19-spring-generator-inheritance-subclass-naming/`, and persisted the archive report to Engram. The verified-state archive confirms all 26 tasks complete, PASS WITH WARNINGS (W1 intentional root-only fixtures, W2 transient TLS flake), 0 CRITICAL, 828 backend tests (6 new), 322 spring_generator tests (5 new), compile gate `BUILD SUCCESSFUL`, inheritance-naming defect fixed, uuid-id sample deterministic. The change is archived but not yet committed.

## 2026-09-19 — Change applied: Inheritance subclass Java class naming (`spring-generator-inheritance-subclass-naming`)

`sdd-apply` implemented all 26 tasks with Strict TDD. The change was later verified and archived (see the entry above); it is not yet committed. It fixes the defect recorded in the compile-check cycle: `emit/inheritance_context.py:169` named every hierarchy subclass `pascal_case(class_id)` (the UML element id), so uuid4-hex ids (10 of 16 start with a digit) raised `InvalidJavaIdentifierError`.

Decisions (DD87-DD91, full rationale in the change `design.md`):

- **DD87** subclass class name is `pascal_case(table.discriminator_values[class_id])`, inline at `:169`; subscript (not `.get`) so a missing value stays a loud `KeyError`; no helper, no schema change. Root naming (`pascal_case(table.name)`) is untouched.
- **DD88** fixtures adopt verbatim UML class names as discriminator values (`Vehicle/Car/Truck/PickupTruck`), because `mapper.py:275` stores `class_by_id[class_id].name`; screaming-snake values were unreachable fixtures. Emitted file names are unchanged; only `@DiscriminatorValue("CAR")` assertions became `("Car")`.
- **DD89** discriminating coverage lives in new tests (uuid digit-leading ids, id-independence, `"Sports Car"` rejection pinned), not in the old fixtures, which keep readable ids (with readable ids and class-name values, `pascal_case("car") == pascal_case("Car")`).
- **DD90** `samples/sample_model.py` uses frozen uuid4-hex class-id literals (vehicle/car/truck digit-leading), not live `new_id()`, to stay deterministic across processes. This supersedes DD81 (readable-id workaround). Only class ids changed.
- **DD91** the manual compile gate (`bash scripts/verify-generated-project.sh`) is the end-to-end regression evidence over the uuid-id sample.

Evidence: RED (5 new tests failing: 4x `InvalidJavaIdentifierError`, 1x `DID NOT RAISE` for the `"Sports Car"` test) then GREEN after the one-line fix; `test_inheritance_backward_compatibility.py` unmodified and passing. Gate: run 1 exit 1 (transient Maven Central TLS handshake failure), immediate rerun exit 0, `BUILD SUCCESSFUL in 41s`, image `gradle:9.7.1-jdk21`. Totals: backend 828 (822 + 6), `apps/spring_generator` 322 (317 + 5), `apps/generation_runner` 59 (58 - 2 + 3).

Apply-time deviation: `test_rejections.py:59` fixture also needed realigning (found by the tasks phase, listed in task 3.3). Its other root-only `"VEHICLE"` fixtures (lines 146-179) were left as is: they never name a subclass.

## 2026-09-19 — Cycle archived: Generated project compile check, slice 2 of 3 (`2026-09-19-generated-project-compile-check`)

`sdd-apply` implemented all 42 tasks with Strict TDD for the Python half; the compose/Gradle half is proven by a recorded manual gate run (DD85). `sdd-verify` passed with warnings (0 critical); W2 was fixed in a later commit (CLI now catches `UngeneratableSourceError` and `OSError`; two tests added; final count 822 backend tests, 58 in `apps/generation_runner`). This is §37 item 13 slice 2 of 3: for the first time the generated project is written to disk and compiled. The change is verified and archived but not yet committed. Slice 3 (`generated-project-boot-smoke`) and the `inheritance_context.py:169` bugfix are still queued.

Decisions (DD75-DD86, full rationale in the change `design.md`):

- **DD75** new app `apps/generation_runner/` splits into a pure part (`domain/`, `writer/`, guarded so it never imports `apps.spring_generator`) and glue (`cli.py`, `runner_image.py`, `samples/`) that may import the generator.
- **DD76** the writer types its input with `typing.Protocol` (`GeneratedSourcesLike`, `GeneratedFileLike`), not `runtime_checkable`, so there is zero import edge to the generator.
- **DD77** typed errors: base `GeneratedSourceWriteError` with `InvalidGeneratedPathError`, `DuplicateGeneratedPathError`, `EscapingGeneratedPathError`, `NonEmptyTargetDirectoryError`.
- **DD78** `write_sources(sources, target_dir)` validates everything before writing, in fixed order: non-empty target, per-file shape, duplicates (exact and case-only), resolved-escape, then write (`newline="\n"`, UTF-8). Atomic pre-write; a mid-write `OSError` is not rolled back (documented).
- **DD79** CLI `python -m apps.generation_runner.cli --target <dir> [--base-package ...]`, no `django.setup()`, exit 0/1/2, so the one-shot service needs no `backend/.env` or database.
- **DD80** `runner_image.gradle_runner_image()` builds `gradle:{GRADLE_VERSION}-jdk{JAVA_VERSION}` from `emit/versions.py`; no version literal anywhere else.
- **DD81** `samples/sample_model.py` uses readable element ids and documents the `inheritance_context.py:169` workaround.
- **DD82** host script `scripts/verify-generated-project.sh` computes the tag through a one-shot `generate-project` run, exports `GRADLE_IMAGE`, then runs `jvm-verify`.
- **DD83** two profile-gated compose services (`generate-project`, `jvm-verify`) over named volume `generated_project`; the harness (not the CLI) does `rm -rf /generated/project`, so the writer's non-empty refusal stays a real safety net. Both run as root.
- **DD84** the container target path lives only in the compose `command`, never in Python.
- **DD85** Strict TDD covers Python only; the gate is a manual command whose exit code and output are recorded in `openspec/changes/generated-project-compile-check/gate-evidence.md`. No `jvm` pytest marker, no Docker socket.
- **DD86** `.gitignore` gains `.gradle/` only.

Apply-time deviations from `design.md` (empirical, found by the gate):

1. `${GRADLE_IMAGE:?}` broke every ordinary compose command (`config`, `exec`, `ps`) while the variable was unset, because compose interpolates the whole file. Fallback applied: `image: ${GRADLE_IMAGE:-gradle.invalid/unset:GRADLE_IMAGE-not-set-run-scripts-verify-generated-project.sh}`, which fails at pull time naming `GRADLE_IMAGE`. Negative check 7.2 changed accordingly (pull failure, not an interpolation abort; `generate-project` starts first).
2. The backend `dev` image ships no source, so `generate-project` failed with `ModuleNotFoundError: No module named 'apps'`. Fix: `generate-project` mounts `./backend:/app:ro`.
3. Symlink-escape gap: DD78 step 1 refuses any non-empty target, so a pre-existing symlink is unreachable through `write_sources`. Step 4 is tested through the helper directly and an end-to-end test that monkeypatches the `_resolve` seam.

Evidence: gate `bash scripts/verify-generated-project.sh` gave `BUILD SUCCESSFUL in 50s`, exit 0 (orchestrator re-run after archive), image `gradle:9.7.1-jdk21`, 41 files. `docker compose exec -T backend pytest -q` reported 822 passed (764 before + 58 new in `apps/generation_runner`); `apps/spring_generator` still 317 passed. W1 (accepted deviation): compose image uses sentinel default instead of required form (pull-time failure naming GRADLE_IMAGE). W2 (fixed before archive): CLI now catches `(GeneratedSourceWriteError, UngeneratableSourceError, ValueError, OSError)` with two new test cases in `test_cli.py`. No commit or push was performed by verify/archive.

## 2026-09-19 — Cycle archived: Spring Boot project scaffold, slice 1 of 3 (`2026-09-19-spring-boot-project-scaffold`)

`sdd-apply` implemented all 20 tasks with Strict TDD, single PR (`size:exception`, the user's standing choice; it was applied by the orchestrator from that standing choice, not asked again). `sdd-verify` passed with warnings (no critical); the two code warnings were fixed before archive, so the suite ended at 764 backend tests (685 before the change). This is slice 1 of §37 item 13 ("generated backend compilable"): pure scaffold text only. Nothing writes, compiles or runs; slice 2 (`generated-project-compile-check`) will compile it and slice 3 (`generated-project-boot-smoke`) will boot it against a fresh PostgreSQL. The slice-0 spike proved the shape for real: `gradle build --no-daemon` gave BUILD SUCCESSFUL in 49 s, and the app booted against PostgreSQL 16.

Decisions (DD61-DD74, full rationale in the change `design.md`):

- **DD61** both new entry points live in `emit/renderer.py` (`generate_project_scaffold_sources`, `generate_project_sources`); if it must ever split, the seam is entry-point family, not helper extraction.
- **DD62** new `emit/versions.py` is the only place a generated-toolchain version exists: `SPRING_BOOT_VERSION="4.1.1"`, `JAVA_VERSION=21` (an `int`), `PROJECT_VERSION="0.0.1-SNAPSHOT"`, `GRADLE_VERSION="9.7.1"`. `GRADLE_VERSION` renders nothing yet; slice 2's `gradle:9.7.1-jdk21` runner image reads it.
- **DD63** frozen contexts and builders in `emit/scaffold_context.py`, a sibling of `inheritance_context.py`.
- **DD64** the three templates contain zero `{% %}` and zero `{#`: pure `{{ }}` substitution, which makes the `trim_blocks` trap impossible by construction.
- **DD65** `build.gradle` reproduces the spike oracle: `java` + `org.springframework.boot` plugins, `SpringBootPlugin.BOM_COORDINATES` platform, `mavenCentral()` only, toolchain 21, three starters (`webmvc`, `data-jpa`, `validation`) + `runtimeOnly postgresql`. No `io.spring.dependency-management`, springdoc, Kotlin DSL, wrapper or `.gitignore`.
- **DD66** `settings.gradle` is one static line rendered with no context; `generated-backend` is literal template text.
- **DD67** `Application.java` sits in the root base package (`@SpringBootApplication` scans downward; `config/` is spec-forbidden); path built with `.format()` from the same `class_name` the template renders.
- **DD68** fixed scaffold order: `build.gradle`, `settings.gradle`, `src/main/java/<pkg>/Application.java`.
- **DD69** `generate_project_sources` = model aggregate (contiguous prefix, untouched), then scaffold, then one duplicate-path check over the combined tuple before building `GeneratedSources` (atomic).
- **DD70** no new error type: invalid `base_package` keeps the bare `ValueError` (DD20); collisions reuse `GeneratedSourcePathCollisionError`. Promoting the `ValueError` is a separate cross-cutting change.
- **DD71** no scaffold/model collision is reachable today, so the test injects one by monkeypatching the module-global `renderer.generate_project_scaffold_sources`; `generate_project_sources` therefore calls its collaborators by module-global name.
- **DD72** "versions live in one place" is enforced by a negative source scan over `emit/**/*.py` (minus `versions.py`) and `emit/templates/*.j2` for `4.1.1`, `9.7.1` and a bare `21`.
- **DD73** the hardcoded-value test deliberately omits `postgres` and `port` (the GAV `org.postgresql:postgresql` is a coordinate, not a deployable value).
- **DD74** `generate_project_sources(model, *, base_package) -> GeneratedSources` is the sole input contract for the future slice-2 writer; no writer, path re-validation or runner dependency was added here.

Apply-time deviations from `design.md` (see the session note): the `Application.java` template follows the verbatim spike oracle from `exploration.md` (no blank line between the class declaration and `main`; the design's template had one), which closes the design's only open question about the exact body; and the DD72 scan found one real leak, a comment `# Java 21 reserved words` in `emit/naming.py`, reworded to `# Java reserved words` (comment only, no behavior change).

Evidence: `docker compose exec -T backend pytest -q` reported 762 passed (685 before + 77 new); `pytest apps/spring_generator/tests -q` reported 315 passed (238 before + 77 new). The existing inheritance SHA-256 snapshot and `test_no_concat_guard.py` pass unmodified, so `generate_model_sources` is byte-identical. No commit or push was performed by apply.

Known separate defect, not fixed here: `emit/inheritance_context.py:169` names subclass entities with `pascal_case(class_id)` instead of using the UML class name from `discriminator_values[class_id]`, so real uuid-based class ids raise `InvalidJavaIdentifierError` (10 of 16 uuid4 hex ids start with a digit). Every inheritance test passes readable ids, so the suite never caught it. Queued in `NEXT_STEPS.md` as its own small change.

## 2026-09-19 — Cycle archive: Spring Boot whole-model source orchestrator (`2026-09-19-spring-boot-whole-model-orchestrator`)

`sdd-archive` composed the whole-model orchestrator delta into `openspec/specs/spring-boot-generation/spec.md` and moved the change to `openspec/changes/archive/2026-09-19-2026-09-19-spring-boot-whole-model-orchestrator/`. The archived canonical spec now includes requirements for deterministic whole-model aggregation, singleton shared errors and application YAML, typed duplicate-path rejection, whole-model determinism/purity, and preservation of lower-level generator contracts.

Archive evidence records 13/13 tasks complete and verification green: `238/238` Spring generator tests and `685/685` backend tests. No commit or push was performed at archive time (committed later as `c876f79`), and `.pi` remains excluded from intended commits.

## 2026-09-19 — Cycle apply partial: Spring Boot whole-model source orchestrator (`2026-09-19-spring-boot-whole-model-orchestrator`)

`sdd-apply` added the pure whole-model orchestration API in `backend/apps/spring_generator/emit/renderer.py`: `generate_model_sources(model, *, base_package="com.modelia.generated")` walks `RelationalModel.tables`, then `RelationalModel.enum_types`, then appends shared errors and the project `application.yml` singleton. It delegates to the existing table, enum, shared-error, and project-config generators and does not add materialization, compilation, Docker, Gradle, OpenAPI, Postman, frontend, mobile, mapper, validation, or Java template behavior.

A new `GeneratedSourcePathCollisionError(UngeneratableSourceError)` in `emit/errors.py` rejects exact duplicate generated paths with deterministic `path` and `occurrences` payloads before returning any `GeneratedSources`. Tests were added for aggregate order, empty/global singleton output, package propagation, lower-level byte identity, inheritance table boundaries, duplicate path collisions, determinism, and purity. Docker verification now passes: focused model/determinism/purity checks `31 passed`, preexisting API regression `37 passed`, full Spring generator suite `238 passed`, and full backend regression `685 passed`.

## 2026-09-19 — Cycle apply: Spring Boot generator config singleton (`2026-09-19-spring-boot-generator-config-layer`)

`sdd-apply` implemented the approved strict-TDD bounded slice for project
configuration generation. `generate_project_config_sources()` is a
parameter-free, project-singleton public entry point in
`backend/apps/spring_generator/emit/renderer.py`; it returns exactly one
in-memory `GeneratedFile` at `src/main/resources/application.yml` rendered from
`emit/templates/application.yml.j2`.

The YAML contains only six required no-default environment placeholders:
`SPRING_APPLICATION_NAME`, `SPRING_DATASOURCE_URL`,
`SPRING_DATASOURCE_USERNAME`, `SPRING_DATASOURCE_PASSWORD`, `JPA_DDL_AUTO`, and
`SERVER_PORT`. It deliberately emits no Hibernate dialect/platform setting, no
hardcoded deployable value, no dynamic environment read, no filesystem effect,
no whole-model orchestrator, and no Java `config/` layer. Existing table, enum,
inheritance, and shared-error generation boundaries remain unchanged; table
generators still emit no `src/main/resources/` paths.

## 2026-09-19 — Cycle apply: Spring Boot generator Single Table inheritance (`2026-09-19-spring-boot-generator-inheritance`)

`sdd-apply` implemented the approved single-PR `size:exception` slice with Strict TDD. A discriminator-backed `Table` now passes typed validation when it has a UUID PK, a discriminator column present in `columns`, non-empty ordered `source_class_ids`, discriminator values for every hierarchy id, and assignable owned fields. Malformed shapes raise `MalformedInheritanceTableError` with stable reasons such as `source_class_ids_required`, `discriminator_value_required`, `unknown_column_owner`, `unowned_column_unsupported`, and `subclass_relationship_unsupported`.

The renderer now branches only after the existing base-package, table-shape, and resource-path checks. Supported inheritance tables emit `domain/<Root>.java`, each subclass domain class in `Table.source_class_ids[1:]` order using `pascal_case(class_id)`, and exactly one root `persistence/<Root>Repository.java`. The root entity is concrete and carries `@Inheritance(SINGLE_TABLE)`, `@DiscriminatorColumn`, and `@DiscriminatorValue`; subclasses extend the root and carry only their own discriminator value. The discriminator column is metadata only, and field partitioning is driven by `Column.owning_class_id`; subclass-owned relationship fields are rejected.

The non-discriminator path remains byte-identical: existing six-file generation still uses the old templates and order, protected by a SHA-256 snapshot test for a scalar + enum + FK `Product` table. This slice deliberately adds no inheritance DTOs, services, controllers, subclass repositories, Java compilation, config, OpenAPI, Postman, Domain Manifest, frontend, mobile, or infrastructure work. Evidence: `docker compose exec -T backend pytest apps/spring_generator/tests -q` reported 208 passed, and `docker compose exec -T backend pytest -q` reported 655 passed. No commit has been created yet.

## 2026-09-19 — Cycle apply: Relational column ownership metadata (`relational-column-ownership`)

`sdd-apply` implemented the archived `relational-column-ownership` cycle with
Strict TDD. `Column` in `backend/apps/relational_mapping/domain/schema.py` now
has `owning_class_id: ElementId | None = None`, distinct from
`source_element_id`: `source_element_id` identifies the UML attribute, while
`owning_class_id` identifies the UML class that owns that attribute. The mapper
threads ownership only through `_map_attribute_column(...)`; root and subclass
attributes flattened into a Single Table preserve their original UML class id.
Synthetic `id`, `class_type` discriminator, relationship FK columns, and
many-to-many join-table columns deliberately keep `owning_class_id is None`.

The Spring generator boundary remains unchanged: discriminator-backed tables
still raise the existing inheritance unsupported error, even when owned
attribute metadata is present. This cycle is a prerequisite for future Spring
inheritance generation, not the inheritance generator itself. Verification found
one weak assertion (`all(...)` over join-table columns); it was fixed by
asserting the exact join-table column names before checking each column. Final
evidence: focused suite 44 passed, full backend suite 636 passed, and
`python manage.py check` reported no issues. No commit had been created at that time (committed later as `30c1c3e`).

## 2026-09-18 — Cycle apply: Spring Boot generator `application/`+`api/` layers (`2026-09-18-spring-boot-generator-application-api-layer`)

`sdd-apply` implemented all 23 tasks (Phases 1–8) from
`openspec/changes/2026-09-18-spring-boot-generator-application-api-layer/tasks.md`
with strict TDD, single PR (`size:exception`, confirmed by the user over the
400-line review budget; this session's apply resumed after a rate-limit
interruption mid-Phase-4, picking up from the persisted `tasks.md` checkpoints
with no rework). Extends both archived cycles (DD1–DD36): `generate_table_sources`
grows from 2 to 6 emitted files, and a new sibling `generate_shared_error_sources`
emits the two per-project `errors/` files.

**Design decisions DD37–DD50** (`design.md`) landed as specified: DTOs live in
`application/dto/` as two classes, `<E>RequestDto`/`<E>ResponseDto` — a
sub-package of `application/`, never a new top-level `dto/` (which §22's
literal directory list never names) and never `api/` (which would invert
`application/ → api/` layering) (DD37); DTO field rules — one field per
`table.columns`, request omits the PK, a FK column becomes `UUID
<camelCase(column.name)>` (never the related entity type, keeping the `Id`
suffix unlike DD26's JPA field name, so two FKs to the same table stay
distinct), an enum column keeps its enum type, request fields carry forwarded
`@NotNull`/`@Size`, response fields carry none, and neither DTO ever gets a
JPA annotation (DD38); `<E>Service` in `application`, `@Service`, constructor
injection, `private final` fields, class-level `@Transactional(readOnly =
true)` + method-level on the three mutators, exactly six public methods —
`create`/`findById`/`update`/`delete`/`list(Pageable)`/`count()`, a single
`Pageable` parameter covering both pagination and sorting since it already
carries a `Sort` (DD39); FK resolution always via
`relatedRepository.findById(...).orElseThrow(...)`, never
`EntityManager.getReference()` (which defers the not-found check past where
the service can convert it into the typed 404) — one repository per distinct
`fk.referenced_table`, deduplicated and ordered by first appearance, a
self-reference dedups against the entity's own repository adding no extra
constructor parameter, and a nullable FK whose DTO value is `null` skips the
lookup (DD40); one generic `ResourceNotFoundException(String resourceName,
UUID id) extends RuntimeException` in `<base_package>.errors`, not a
per-entity hierarchy — the advice is a singleton generated with no knowledge
of how many tables exist, so a per-entity type would be structurally
impossible under the one-`Table` signature (DD41); a new
`generate_shared_error_sources(*, base_package) -> GeneratedSources` entry
point, taking no `Table`, reusing `_ENVIRONMENT`/`_validate_base_package`/
`package_path`, emitting the two `errors/` files exactly once — never from
`generate_table_sources`, which would produce N byte-identical copies at the
same path (DD42); `GlobalExceptionHandler` is `@RestControllerAdvice` (not
bare `@ControllerAdvice`, which resolves a returned object as a view name
without `@ResponseBody`), two handlers returning `ProblemDetail` (RFC 7807,
zero extra generated classes) for 404/400, the validation handler building its
`field -> message` map via a plain `for` loop over
`ex.getBindingResult().getFieldErrors()` (DD43); DTO ↔ entity conversion lives
in two `private` methods on the service, `toResponseDto`/`applyRequestDto` —
no mapper class, no MapStruct (would add an annotation processor to every
generated `build.gradle`, the same argument DD18 used against Lombok), no
`BeanUtils.copyProperties` (cannot bridge `UUID categoryId` ↔ `Category
category`); the individual statement lines are precomputed in `context.py` as
an ordered `tuple[str, ...]` via `.format()`, the template only loops and
indents (DD44); resource path segment = `naming.resource_path_segment(table.
name)` — pluralize the last `_`-separated word via a fixed 3-rule `re.sub`
chain, then lowercase and replace `_` with `-`, validated against
`^[a-z0-9]+(-[a-z0-9]+)*$` and raising the new `InvalidResourcePathError`
(`UngeneratableTableError` subclass) as DD35's fifth check (DD45); the
endpoint table — `POST ""` → 201, `GET "/{id}"` → 200, `PUT "/{id}"` → 200
(not `PATCH`, since the request DTO carries every non-PK field), `DELETE
"/{id}"` → 204, `GET ""` → paginated 200, `GET "/count"` → 200 — Spring's
pattern comparator deterministically ranks the literal `/count` segment above
`/{id}`'s variable, so the two never collide (DD46); the controller binds
`Pageable` directly with zero custom `@RequestParam` parsing — Spring Boot
auto-configures the resolver whenever spring-data and spring-web are both on
the classpath (DD47); **DD48 amends DD18, the only backwards-incompatible
change this cycle**: the entity's no-arg constructor becomes `public`, not
`protected` — a compilation prerequisite, since DD39 puts the service in
`<base_package>.application` while the entity lives in `<base_package>.
domain`, and `protected` grants access only within the same package (DD48);
six new templates, all data-driven, every loop body obeying the DD13
whitespace lesson (a content line never ends with a `{% %}` block tag), with
comma-separated lists precomputed via `_comma_join` (DD49); determinism rules
for the new artifacts — `GeneratedSources.files` order is fixed layer order
(Entity, Repository, RequestDto, ResponseDto, Service, Controller), DTO field
order is `table.columns` order with the PK simply omitted from the request,
service constructor parameter order is own repository first then each
distinct FK-referenced-table repository in first-appearance order, and DD27's
same-package import suppression does **not** extend to `application.dto` —
the service and controller must import the DTOs explicitly, since
`<pkg>.application.dto.*` is a different package from `<pkg>.application`
(DD50).

**Verification.** 55 new backend tests: `test_resource_path.py` (new, DD45),
`test_dto_generation.py` (new, DD37/DD38), `test_service_generation.py` (new,
14 tests, DD39/DD40/DD44), `test_error_sources.py` (new, 7 tests, DD41–DD43),
`test_controller_generation.py` (new, 7 tests, DD45–DD47), plus modifications
to `test_entity_structure.py` (DD48 ctor flip), `test_paths_and_package.py`
(6-file expectations), `test_determinism.py` (widened to all six files: fixed
layer order, DTO field order, `org.springframework.*` import group), and
`test_purity.py` (extended to `generate_shared_error_sources`).
`test_no_concat_guard.py` stayed green unmodified over every modified `emit/`
module. Full backend suite: 631/631 passed, zero regressions. No deviations
from `design.md` were required — every DD landed exactly as specified,
including DD48's scope delta (flagged in `design.md`'s Open Questions as a
proposal-unanticipated change to a file the proposal listed as untouched, and
accepted as-is).

## 2026-09-18 — Cycle apply: Spring Boot generator relationships (FK) + enum types (`2026-09-18-spring-boot-generator-relationships-enums`)

`sdd-apply` implemented all 27 tasks (Phases 1–5) from
`openspec/changes/2026-09-18-spring-boot-generator-relationships-enums/tasks.md`
with strict TDD, single PR (`size:exception`, confirmed by the user over the
400-line/session-800-line budget). Extends the archived
`2026-09-18-spring-boot-generator-core` cycle (DD1–DD22): `generate_table_sources`
now emits FK-bearing and enum-bearing tables instead of rejecting them, and a
new sibling `generate_enum_source` renders standalone Java enums.

**Design decisions DD23–DD36** (`design.md`) landed as specified: one field
per `Column` always, `_field_context` picks the first matching branch
PK → FK-member → `enum_type_name` → scalar, so a FK column yields the
relationship field instead of, never in addition to, a scalar field (DD23);
`@OneToOne` iff `set(fk.column_names)` equals a `unique_constraints` set on
the same table, `@ManyToOne` otherwise, derivable from one `Table` with zero
cross-table lookup (DD24); `@JoinColumn(name, nullable[, unique = true])`
replaces `@Column` on a relationship field, never both, and
`referencedColumnName` is never emitted since every referenced entity's `@Id`
is unconditionally named `id` (DD25); relationship field name =
`camel_case(base)` where `base` strips one trailing `_id` from the FK column
name (`category_id` → `category`), via new `naming.py::relationship_base_name`
— the referenced-table name breaks on self-reference and on two FKs to the
same table, so the column name (which carries the role) is used instead
(DD26); no import is emitted for the referenced entity or enum type, since
both are generated into `{base_package}.domain`, the same package as the
entity being rendered — this is what makes a self-referencing FK need no
special-casing anywhere (DD27); the enum branch keys on
`column.enum_type_name is not None` and short-circuits before any
`java_type_for()` call — `javatypes.py` gains no `ColumnType.ENUM` row, and
**both** call sites inside `context.py` (the field builder and
`build_entity_context`'s import-collection loop) must skip FK/enum columns
identically, since the second call site is an easy miss the design's Risks
section flagged explicitly (DD28); enum-field annotation order extends DD11
to `@Id, @GeneratedValue, @ManyToOne|@OneToOne, @JoinColumn, @Enumerated,
@Column, @NotNull, @Size` — always `EnumType.STRING`, never `ORDINAL` (which
would silently corrupt stored rows if a UML enumeration's literals are ever
reordered), never `@Size` (DD29); `generate_enum_source` lives in
`emit/renderer.py` alongside `generate_table_sources`, reusing the same
module-level Jinja `_ENVIRONMENT`/`_validate_base_package`/`package_path`;
its context builder `build_enum_context` lives in `context.py` next to the
other builders, preserving the invariant that all branching lives there and
templates stay data-driven (DD30); enum constants are SCREAMING_SNAKE_CASE
via a fixed 3-step regex (camel/Pascal boundary split → non-alnum run
collapse to `_` → `.upper()`), validated through the existing
`naming._validate` so an illegal result still raises
`InvalidJavaIdentifierError` (DD31); the verbatim source label is preserved
as a plain `private final String label` + constructor arg + `getLabel()` on
the generated enum — zero annotations, DD19 (no Jackson) still holds — since
JPA's `@Enumerated(STRING)` persists `name()` (`IN_PROGRESS`), not the
original label (`in_progress`); a future DDL/DTO slice must read `getLabel()`
or reapply DD31 (DD32, **known recorded divergence**); a new
`UngeneratableSourceError(Exception)` root sits above both the existing
`UngeneratableTableError` (re-parented, name and every subclass unchanged)
and a new `UngeneratableEnumError` branch (`EmptyEnumTypeError`,
`DuplicateEnumConstantError`) (DD33); `ForeignKeysUnsupportedError` is
**renamed** to `CompositeForeignKeyUnsupportedError` with **no**
backwards-compatible alias — its blast radius is two files inside this one
app, and the old name asserted a promise ("this generator does not support
foreign keys") that is now false (DD34); the new fixed rejection order in
`reject_out_of_scope` is PK shape → composite FK (any FK with
`len(column_names) > 1`, first offender in `foreign_keys` order) →
discriminator → a `ColumnType.ENUM` column with `enum_type_name is None`
(first offender in `columns` order) — single-column FKs and named enum
columns now raise nothing (DD35); determinism needed no new rule: field
order stays `Table.columns` declaration order because DD23 guarantees
exactly one field per column, and the new `jakarta.persistence.{ManyToOne,
OneToOne, JoinColumn, Enumerated, EnumType}` imports join the existing
`jakarta.*` group, added only when actually used, confirmed by widening the
existing `hypothesis` property-test strategies rather than adding new
ordering logic (DD36).

**Verification.** 40 new backend tests across `test_relationship_fields.py`
(15, new), `test_enum_fields.py` (7, new), `test_enum_source.py` (14, new),
`test_rejections.py` (rewritten to the new DD35 order, net +3), and
`test_determinism.py` (widened strategies + 1 new enum-determinism property).
`test_no_concat_guard.py` stayed green unmodified (the two new `naming.py`
helpers use only `re.sub`/`.upper()`). Full backend suite: 576/576 passed,
zero regressions. No deviations from `design.md` were required.

`sdd-apply` implemented all 31 tasks (Phases 1–8) from
`openspec/changes/2026-09-18-spring-boot-generator-core/tasks.md` with strict
TDD, single PR (`size:exception`, confirmed by the user over the 400-line/
session-800-line budget). New Django app `backend/apps/spring_generator/`
(`domain/` + `emit/` split, no `models.py`) adds a pure, in-memory
`generate_table_sources(table, *, base_package="com.modelia.generated") ->
GeneratedSources` — spec §22, item 12's first slice (one
`relational_mapping.domain.schema.Table` -> one JPA `@Entity` + one Spring
Data JPA repository interface, `domain/`+`persistence/` only).

**Design decisions DD1–DD22** (`design.md`) landed as specified: app-per-domain
registration shell, no `models.py`/`migrations/` (DD1); templates at
`emit/templates/*.java.j2`, never app-root `templates/` (Django's `APP_DIRS`
loader would otherwise scan the `.java.j2` files as Django templates) (DD2);
public API is a pure function returning in-memory sources, never touching the
filesystem (DD3); frozen `GeneratedFile`/`GeneratedSources` with a derived
`as_mapping()`, POSIX-relative paths (DD4); boxed Java types only, never
primitives (DD5); `TIMESTAMPTZ -> java.time.OffsetDateTime`, round-tripping
the source column's timezone offset instead of Hibernate 6's silent-offset-
drop with `LocalDateTime` (DD6); `TEXT -> String` + `columnDefinition =
"TEXT"`, avoiding the `@Lob` OID-large-object trap on PostgreSQL (DD7); the
PK gets `@Id` + `@GeneratedValue(strategy = GenerationType.UUID)` +
`updatable = false` and explicitly **no** `@NotNull` — Bean Validation would
otherwise fire before the provider generates the id on `persist()` (DD8);
`@NotNull` on every non-PK `nullable=False` column, `@Size(max=length)` on a
`VARCHAR` with a `length`, never `@NotBlank` (DD9); `@Column` always emits an
explicit `name`, then only present attributes in the fixed order `name,
nullable, length, precision, scale, columnDefinition, updatable` (DD10);
fixed per-field annotation order `@Id, @GeneratedValue, @Column, @NotNull,
@Size` (DD11); determinism — field order is `Table.columns` declaration
order unchanged, imports deduped and grouped `java.*` / `jakarta.*` /
`org.*` / `<base_package>.*`, lexicographic within group (DD12); a
module-level Jinja2 `Environment` with `StrictUndefined`, `autoescape=False`,
`trim_blocks`/`lstrip_blocks`, constructed once at import (DD13); LibCST's
concrete, executed role is a guard (`tests/test_no_concat_guard.py`) that
parses every module under `emit/` and fails on manual string `+`,
`str.join`, `%`-formatting, or any f-string — it never parses the emitted
Java and never runs at render time (DD14); a Java-identifier whitelist
(`[A-Za-z_][A-Za-z0-9_]*`) rejects an illegal table/column name, and a Java
reserved word gets a trailing `_` while `@Column(name=...)` preserves the
original DB name (DD16); the repository is `interface <E>Repository extends
JpaRepository<<E>, UUID>`, empty body, no `@Repository` annotation — Spring
Data's own scanning registers the proxy regardless (DD17); `protected`
no-arg constructor + explicit getters/setters, no Lombok, no `equals`/
`hashCode` this slice (DD18); no Jackson annotations this slice — that
belongs to the future `api/` DTO layer (DD19); a validated `base_package`
keyword parameter (default `com.modelia.generated`), no `application.yml`,
host, port, URL, or credential in any template (DD20); `jinja2` ->
`backend/requirements/base.txt` (runtime), `libcst` ->
`backend/requirements/test.txt` (guard-only) (DD21); a dedicated
`tests/factories.py` imports only `apps.relational_mapping.domain`, never
`relational_mapping`'s own test factories (DD22).

**Typed rejection hierarchy (DD15).** `emit/errors.py`'s
`UngeneratableTableError` base plus `UnsupportedPrimaryKeyError`,
`ForeignKeysUnsupportedError`, `InheritanceUnsupportedError`,
`UnsupportedColumnTypeError`, `InvalidJavaIdentifierError` mirror
`relational_mapping.mapping.errors`'s shape (base + attribute-carrying
subclasses). `reject_out_of_scope(table)` checks in the fixed order PK shape
-> FK -> discriminator -> enum column before any render; a table violating
several rules at once always raises the first one, deterministically.

**Deviations from design.md, found during implementation:**
1. **Guard filename**: `test_no_concat_guard.py`, not the literal
   `no_concat_guard.py` DD14 names — pytest's own `python_files = ["test_*.py",
   "*_test.py"]` (`backend/pyproject.toml`) does not auto-collect a file
   named `no_concat_guard.py` during the full-suite run, which would have
   silently dropped the guard from every future `pytest -q`. Renamed to keep
   it collected and enforced on every run.
2. **DD14's guard is a blanket syntactic ban, not a dataflow-sensitive one.**
   A LibCST-only guard cannot mechanically distinguish "a string that flows
   into emitted Java" from any other string in the same module without full
   dataflow analysis, which contradicts DD14's own framing of a simple,
   "never called at render time" structural check. The guard therefore flags
   `+`/`str.join`/`%`/f-strings anywhere in `emit/*.py`, including exception
   messages (`errors.py`) and identifier-conversion helpers (`naming.py`),
   not only literal Java-annotation assembly (`context.py`). `naming.py`
   converts `snake_case` to Pascal/camelCase via a single declarative
   `re.sub` instead of word-splitting + `.join()`; `errors.py`/`context.py`/
   `renderer.py` use `str.format()` (not one of DD14's four checked
   patterns) plus a small reassignment-loop comma-join helper in place of
   `", ".join(...)`.

Full regression: 536/536 backend tests pass (93 new, zero regressions), no
new frontend or mobile diff.

## 2026-09-18 — Bug fix: `document.update` broadcast crashed any command while a WebSocket client was connected

Real-browser testing (adding an operation to a class) surfaced a 500 on
`POST .../commands` whenever at least one client held a live WebSocket
connection to the document. Root cause (confirmed via `docker compose logs
backend` and a direct call to `broadcast_document` against the real
Redis-backed channel layer): `services.broadcast_document` passed
`codec.document_out(document)` — which returns raw `uuid.UUID`/`datetime`
values — straight into `channel_layer.group_send`. That call crosses
channels_redis' msgpack transport, a serialization boundary the Cycle-13
design (DD6) never accounted for; msgpack raises `TypeError: can not
serialize 'UUID' object` immediately, before the consumer's own
`DocumentOut`-based re-serialization (`consumers.py::document_update`) ever
runs. The DB write had already committed (the crash happens inside
`transaction.on_commit`), so the command silently succeeded while the HTTP
response came back as a non-JSON 500 — which the frontend's `ApiError`
parser then rendered as the literal string `"null"` (its fallback for a
response body with no `detail` field).

Test coverage never caught this because `test_consumers.py`/`test_services.py`
exercise Django Channels' in-memory test channel layer, which never invokes
channels_redis' msgpack serializer — the crash is invisible without a real
Redis-backed channel layer in the loop.

**Fix**: `broadcast_document` now serializes the payload through
`schemas.DocumentOut.model_validate(...).model_dump(mode="json")` itself,
before calling `group_send` — not only on the consumer's receiving side.
Added `test_broadcast_document_sends_a_json_safe_payload_to_the_channel_layer`
in `test_services.py`, asserting `id`/`created_at`/`updated_at` are plain
`str` in the message handed to `group_send`. Verified against the real
Redis channel layer via a direct `broadcast_document` call in
`manage.py shell` (no msgpack error), plus the full suite (443/443 green).

## 2026-09-18 — Cycle apply: UML → RelationalModel deterministic mapping (`2026-09-17-uml-relational-mapping`)

`sdd-apply` implemented all 33 tasks (Phases 1–7) from
`openspec/changes/2026-09-17-uml-relational-mapping/tasks.md` with strict TDD,
single PR (`size:exception`, confirmed by the user over the 400-line budget).
New Django app `backend/apps/relational_mapping/` (`domain/` + `mapping/`
split, no `models.py`) adds a pure, DB-free `map_to_relational(model) ->
RelationalModel` — the first stage of spec §21's Spring Boot pipeline — plus
one new `uml_modeling` validation rule.

**Design decisions DD1–DD20** (`design.md`) landed as specified: app-per-domain
shell (DD1); every output dataclass frozen (DD2); mutable `_TableDraft`
builders frozen at the end (DD3); `snake_case` singular table names, no
pluralization (DD4); unconditional synthetic `id UUID` PK, `pk_<table>` (DD5);
Single Table inheritance with a verbatim-class-name `class_type` discriminator,
emitted only for a >=2-class tree (DD6); root attribute columns `NOT NULL`,
descendant-contributed columns `nullable=True` (DD7); one `unique_name` helper
absorbing every column-name collision (attribute named `id`, sibling-subclass
clash, `class_type` clash) via plain name -> owner-class-prefixed -> `_2`/`_3`
suffix (DD8); deterministic construction order throughout, driven by
`model.classes`/`model.relationships` declaration order (DD9); all
enumerations emitted as native-`ENUM`-flavored `EnumType`s regardless of
reference (DD10); "many" = `upper is None or upper > 1`, "optional" =
`lower <= 0` (DD11); FK placement keyed off which end is "many", falling back
to "FK on target + `UniqueConstraint`" for 1:1 (DD12); composition FKs are
always `NOT NULL` + `CASCADE` except the DD14 self-composition exception
(DD13); self-referencing relationships use the generic rule unchanged (DD14);
role-based FK column naming, `naming.unique_name` as the DD8 fallback (DD15);
join tables get their own synthetic PK, both FKs `CASCADE` (DD16); every FK
gets a non-unique index unless it already carries a `UniqueConstraint` (DD17);
the mapper never calls `validate()` — `UnmappableModelError` subclasses
(`MultipleGeneralizationParentsError`, `GeneralizationCycleError`,
`UnknownEnumerationError`, `DanglingRelationshipEndpointError`) are
defense-in-depth only (DD18); `GENERALIZATION` relationships contribute no
column/FK/table, fully consumed by the Stage-3 collapse (DD19); a dedicated
`tests/factories.py` imports only `apps.uml_modeling.domain`, never the
`uml_modeling` test factories (DD20).

**New `uml-validation` rule — `MULTI_PARENT_GENERALIZATION`.** Lives beside
`generalization_cycle` in `validation/rules/relationships.py`: ERROR when a
class is the source (child) of more than one *distinct* `GENERALIZATION`
target; a duplicate edge to the same parent is silent. Grows the fixed
registry from **11 rules to 12**.

**Deviation (not itemized in the original task list, same shape as Cycle 14's
DD6-adjacent addendum)**: growing `RULES` 11→12 and `DiagnosticCode` by one
member broke two pre-existing closed-set regression tests `design.md`/
`tasks.md` didn't call out — `test_diagnostics.py`'s
`test_diagnostic_code_has_exactly_the_eleven_cycle_one_codes` (renamed to
"twelve", set literal grown) and `test_validation_integration.py`'s
full-registry fixture (`produced_codes == set(DiagnosticCode)` plus an exact
`len(result.diagnostics)` count) — both updated in the same change (a `Child`
class with two distinct `GENERALIZATION` parents added to the fixture, given
one attribute so it does not also trip a second, unwanted
`CLASS_WITHOUT_ATTRIBUTES` diagnostic) rather than left red.

Full regression: 442/442 backend (`pytest`) pass (54 new for
`relational_mapping`, 4 new for the validation rule; baseline was 384), zero
regressions. `sdd-verify`/`sdd-archive` are the remaining steps.

## 2026-09-16 — Cycle 14 apply: UML class operations (`2026-09-16-uml-class-operations`)

`sdd-apply` implemented all 27 tasks (Phases 1–14) from
`openspec/changes/2026-09-16-uml-class-operations/tasks.md` with strict TDD,
single PR (`size:exception`, ~950-1150 estimated lines, accepted by the user
over the 800-line budget). This cycle opens the operation write path end to
end: `AddOperation`/`RemoveOperation` clone the attribute vertical slice
(command → handler → dispatcher → schema → form → canvas compartment) at
every layer, so `+ crearUsuario(): Usuario` is now declarable and renders
live.

**DD4 — nullable `return_type`, wire form.** `UmlOperationIn.return_type:
str | dict | None = None` accepts JSON `null` and omission identically
(both map to `None`); the empty-string sentinel `""` was rejected as a wire
option (`AttributeType` has no empty member, so `codec._decode_attribute_type("")`
raises) and instead stays a genuine 422 error via the existing
`InvalidCommandPayloadError` path — `""` is never a synonym for "no return
type". `services.py` also needed two `isinstance` branches in
`_command_from_payload` plus a new `_operation_from_schema` helper, which
`proposal.md`'s Affected Areas table omitted entirely; `design.md` flagged
this explicitly and it landed as designed.

**DD9 — zero-operations parity math.** `classBoxSvgDataUri`'s new
`operationLines` parameter is additive-only: `opAreaHeight` is exactly `0`
when `operationLines` is empty, the second divider and operation `<text>`
lines are emitted only when `operationLines.length > 0`, and `width`'s
`Math.max(...)` spread contributes nothing from an empty array. A dedicated
test pins the zero-ops SVG string/width/height against the pre-cycle
attribute-only shape — the spec's explicit backward-compatibility guarantee
holds by construction, not by accident.

**DD10 — visibility symbol, deliberate asymmetry.** `toElements` had no
existing symbol convention (the attribute line hardcodes `- ${a.name}: ...`
and ignores `a.visibility` entirely). A new `VISIBILITY_SYMBOL` map
(`public → +`, `private → -`, `protected → #`, `package → ~`) is used for
operation lines only; retrofitting it onto the attribute line was
deliberately left untouched (would change `DiagramCanvas.test.tsx`'s
existing pinned expectations, out of scope) and is flagged as a follow-up
in `design.md`'s Open Questions.

**Deviation (not in the original task list)**: growing `RULES` 10→11 and
`DiagnosticCode` by one member broke two pre-existing regression tests
`design.md`/`tasks.md` didn't call out the way they called out
`services.py` — `test_diagnostics.py::test_diagnostic_code_has_exactly_the_ten_cycle_one_codes`
and `test_validation_integration.py`'s full-registry fixture (which asserted
`produced_codes == set(DiagnosticCode)` and an exact diagnostic count).
Both were updated in the same change (renamed to "eleven", fixture gained a
duplicate-operation-name case) rather than left red — recorded here as a
DD6-adjacent addendum.

Full regression: 384/384 backend (`pytest`) and 335/335 frontend
(`vitest run`) pass, plus clean `eslint`/`next build` (TypeScript checked
inline by Turbopack's build step). `sdd-verify`/`sdd-archive` remain.

## 2026-09-16 — Post-cycle-13 fix: client-side lock self-expiry (silent TTL-expiry gap)

Real usage surfaced a gap Cycle 13's tests never exercised end-to-end: a
node lock's Redis key correctly self-expires via TTL (`locks.py`,
`LOCK_TTL_MS = 10_000`) whenever an explicit `node.release`/disconnect
never happens — a dropped WS frame, a backgrounded tab, a `free` that
never fires for any reason — but **nothing broadcasts `node.unlocked` for
a passive TTL expiry**, only `_handle_release` and `disconnect()` do. Every
already-connected client's `locks` entry for that node stayed
"locked by X" forever, even though the server would already let a fresh
claim through. Confirmed with a throwaway diagnostic test before touching
any code (systematic-debugging discipline): claimed a node, let it sit
past a monkeypatched short TTL with no release/disconnect, and observed a
fresh `locks.claim()` succeed server-side while both the holder's and an
observer's sockets received nothing at all.

**Fix, deliberately client-side, no new backend infra**: `state/document.ts`
now gives every `locks` entry its own `setTimeout` deadline
(`_LOCK_STALE_MS = 12_000`, the server's 10s TTL plus a 2s latency margin),
armed on `node.locked` and on each `node.locks` join-snapshot entry, and
**refreshed by every `node.position` frame for that class** — the same
signal that refreshes the server's own TTL, so an actively-dragged node
never flickers. An explicit `node.unlocked` cancels the pending timer
outright. Rejected alternatives: Redis keyspace-notification-driven active
broadcast (needs `notify-keyspace-events` config plus a new subscriber
process — real new infra for a purely cosmetic staleness signal) and a
periodic per-consumer sweep (fragile inside a sync Channels consumer with
no existing polling primitive). The client-side timer is a pure rendering
decision: the server's Redis TTL remains the sole source of truth for who
may actually claim a node, so a client that gets this wrong by a few
seconds self-corrects on the next `node.locked`/`node.locks` signal either
way.

## 2026-09-15 — Cycle 13 apply: implementation complete (uml-node-position-sync)

`sdd-apply` implemented all 21 tasks (Phases 1–7) from
`openspec/changes/2026-09-15-uml-node-position-sync/tasks.md` with strict
TDD, single PR (`size:exception`, ~1150-1250 estimated lines, accepted by
the user over the 800-line budget). Cycle 12 made `DocumentConsumer`
read-only fan-out; this cycle gives it its first `receive_json` so a class
node can be dragged live, with an ephemeral Redis lock arbitrating who
holds it and a durable Postgres write firing once per release.

**DD1/DD2/DD3 — `backend/apps/uml_documents/locks.py`: a lazy module-level
sync `redis.Redis` (reusing `settings.REDIS_HOST`/`REDIS_PORT`, no new env
var), key `uml-lock:{doc_id}:{class_id}`, value `f"{token}|{label}"`,
`claim` = `SET NX PX`, `release`/`refresh` as registered Lua scripts.**
`redis` is promoted to a direct `requirements/base.txt` line since it's now
a real import, not only `channels-redis`'s transitive pull-in. One
implementation correction versus the design sketch: the Lua scripts must
extract the token substring via `string.match(current, '^([^|]*)|')` before
comparing to `ARGV[1]`, since the stored value is `"token|label"`, not the
bare token — a literal `GET == ARGV[1]` (as design.md's pseudocode shows)
never matches. `refresh` doubles as the per-frame authorization check: a
live-position frame only broadcasts when it returns `1`.

**DD4/DD10 — TTL 10s, client throttle 50ms (20Hz); `connect()` sends one
`node.locks` snapshot via `SCAN` (never `KEYS`) right after `accept()`.**
20Hz reads as continuous motion and cuts a 60Hz `mousemove` stream to a
third of the `group_send` publishes; the TTL is 200× the refresh cadence so
a GC pause can't drop a live lock, with `disconnect()` (DD7) as the fast
path and TTL only the backstop.

**DD5/DD6 — Two lock domains stay disjoint: Redis claims never consult the
Postgres row lock or vice versa. `receive_json` re-resolves membership AND
`require_role(OWNER, EDITOR)` on every inbound message; a `VIEWER` is
silently refused, never closed, and keeps receiving broadcasts.** Prior
cycle's DD4 (membership-only at `connect()`) is unchanged and correct for a
read subscription; it would under-authorize now that the socket writes.

**DD7/DD9 — `disconnect()` iterates `self.held`, releases each via the Lua
script, and `group_send`s one `node.unlocked` per id — no durable write.
Group handlers (`node_locked`/`node_unlocked`/`node_position`) re-derive
`mine` per connection and never forward `owner_token`.** `node.locked` with
`mine: true` doubles as the claim-accepted ack, so no separate ack frame is
needed and no token ever reaches a browser.

**DD8 — `services.save_layout_position`, a `submit_command` sibling under
the same `@transaction.atomic` + `_get_row(for_update=True)` lock, calling
the already-built `ProjectDocument.with_layout`. Never routes through
`dispatcher.apply()`; the `UmlCommand` union has zero diff.** Prunes any
layout entry whose class id is absent from the live model on every
successful persist (self-healing, no migration) and returns the document
UNCHANGED — no write, no revision bump — when the target class itself is
gone (the `RemoveClass`-mid-drag case). Verified end-to-end in
`test_consumers.py`: a lock survives its class being removed by another
client without erroring or stranding, and the same class id remains freely
claimable afterward.

**DD11/DD12/DD13 — Frontend: `locks` stays `useState` (low-frequency,
belongs in render); live positions bypass React entirely via a stable
`positionListenerRef` `DiagramCanvas` writes its imperative apply-handler
into on mount. A foreign-held node is `ungrabify()`d (prevention, not
cancellation) plus a dashed-amber `.locked-remote` style; the owner label
renders as a "{label} está moviendo {class}" line under the canvas in
`page.tsx`. Claim is optimistic — the drag starts locally and
`node.claim_rejected` (relayed through a `claimRejectedListenerRef`
mirroring `positionListenerRef`'s exact idiom, since design.md's prop
sketch didn't enumerate it but task 6.1's RED requirement needs an
imperative snap-back channel) restores the position stashed in
`grabStartPosRef` at `grab` time. `toElements(model, layout)` seeds
`position` from `layout.positions`; the `layout` parameter defaults to
`{positions: {}}` rather than being required, so the ~10 pre-existing
`toElements(model)` call sites in `DiagramCanvas.test.tsx` needed no
mechanical rewrite — behavior is identical to design.md's literal
non-optional signature either way.

359/359 backend tests pass, 317/317 frontend tests pass, `npm run lint` and
`npx tsc --noEmit` both clean. `sdd-verify`/`sdd-archive` are the remaining
steps.

## 2026-09-14 — Cycle 12 design: real-time UML collaboration over Channels (realtime-uml-collaboration)

`sdd-design` produced
`openspec/changes/2026-09-14-realtime-uml-collaboration/design.md` for the
first realtime cycle: two members of one organization editing the same UML
document currently cannot see each other's work, because `useDocument` fetches
once on mount and refetches only after its *own* `submitCommand()`. The chosen
shape is result-broadcast — `dispatcher.apply()` stays untouched, HTTP POST
remains the only write transport, and the WebSocket is read-only fan-out.
This entry is the `config.yaml` `rules.design` dual documentation of DD1–DD13;
nothing is implemented yet.

**DD1 — `submit_command` becomes `@transaction.atomic`, and `_get_row` gains a
`for_update: bool = False` flag that chains `.select_for_update()` *after*
`.for_organization(...)`.** The flag exists because `_get_row` is shared with
`get_document`, whose GET view runs outside any transaction — an unconditional
lock would raise `TransactionManagementError` on the read path. The decorator
(not a `with` block) matches `users/services.py:40` and
`organizations/services.py:68/118/134`. Tenant scoping is preserved because
`for_organization` applies `WHERE organization_id = …` before
`select_for_update()` appends `FOR UPDATE`; `select_for_update()` never widens
a queryset, and `TenantScopedManager.get_queryset()` raises
`TenantScopeViolation` on any unscoped access anyway.

**DD2 — The broadcast is emitted via `transaction.on_commit(...)` after
`_save`, closing over the in-memory `result.document`.** Copies
`users/services.py:73` in style. Broadcasting inline would publish a revision
that readers cannot yet `SELECT`; closing over the dataclass rather than the
ORM row means the post-commit callback issues zero queries. A `post_save`
signal was rejected because it would also fire for `create_document`, which
has no group to address.

**DD3 — A sync `DocumentConsumer(JsonWebsocketConsumer)` in
`uml_documents/consumers.py`, routed at
`ws/orgs/<org_slug>/documents/<doc_id>/`, joins group `uml-doc-{doc_id}`.**
Every line of this codebase is sync ORM, so a sync consumer running in
Channels' thread pool calls the membership/document queries directly with no
`database_sync_to_async` wrapper and no async fork of `resolve_membership`.
The group key is the document UUID alone because authorization — not the group
name — enforces tenancy; embedding the slug would falsely imply the name is a
security boundary.

**DD4 — `connect()` authorizes with membership only, deliberately WITHOUT
`require_role`, via a new `resolve_membership_for_user(user, org_slug)`
extracted from `resolve_membership`.** This is a documented correction to the
proposal's wording: the WS is a read subscription, and the read endpoint it
mirrors (`get_document_view`) has no role gate — `api.py:54` carries an
explicit `# no require_role — DD3, any member reads`. Requiring OWNER/EDITOR
would lock a `VIEWER` out of live updates for a document it can already `GET`.
Extracting the user-level function keeps `permissions.py`'s stated invariant
("Nothing else in the app decides authorization") true, and its 20 HTTP
callers stay byte-identical. Unauthenticated closes `4401`; unknown-org,
non-member, and unknown-doc all close `4404`, preserving
`resolve_membership`'s "indistinguishable by design" contract over WS.

**DD5 — Authorization is re-run in the group-message handler before each
relay; failure closes `4403`. Document deletion needs no separate handling.**
A revoked member must stop receiving data at the exact moment data would leak,
and that moment is the outbound message — one indexed `Membership` lookup per
delivered broadcast. A timer would add machinery and still leak for up to one
interval. Deletion is covered for free: broadcasts originate only from
`submit_command`, which cannot run against a deleted row, so the client's next
`getDocument()` 404s through `useDocument`'s existing `notFound` branch.

**DD6/DD7 — The payload is the EXISTING `DocumentOut`.** `api._document_out`
is promoted to `codec.document_out(document)` and the consumer sends
`DocumentOut.model_validate(codec.document_out(doc)).model_dump(mode="json")`,
wrapped as `{"type": "document.update", "document": {…}}`. `codec` is the
natural home because the function is `_encode_model` + `_encode_layout`
composed, and it removes `api.py`'s reach into two underscore-private codec
functions; importing `api` into `services` would invert the layering.
`model_dump(mode="json")` is load-bearing — the raw dict holds `UUID`/
`datetime` objects `json.dumps` rejects, and routing it through the same
Pydantic schema is what guarantees byte-identity with the GET response, so the
client merge needs zero new decoding.

**DD8 — `CHANNEL_LAYERS` → `RedisChannelLayer` from discrete
`REDIS_HOST`/`REDIS_PORT` env vars defaulting to `("redis", 6379)`, plus a
`redis:7-alpine` Compose service with a `redis-cli ping` healthcheck.**
Discrete host/port defaulting to the Compose service name is exactly the
`DATABASES` pattern and `settings.py`'s stated "never a `localhost` fallback"
rule; a single `REDIS_URL` would introduce a second connection-string
convention. In-memory was rejected in exploration because prod runs `daphne`,
which scales to multiple processes, where an in-memory layer fails silently.

**DD9 — `OriginValidator(AuthMiddlewareStack(URLRouter(...)),
settings.CORS_ALLOWED_ORIGINS)`, `OriginValidator` outermost, no new env
var.** `CORS_ALLOWED_ORIGINS` already holds exactly the `scheme://host[:port]`
strings `OriginValidator` expects, so reusing it makes HTTP and WS origin
policy structurally incapable of drifting. CSRF genuinely does not apply: a
browser `new WebSocket()` cannot set the `X-CSRFToken` header `lib/api.ts`
echoes, and it need not, because the socket performs no writes. A
query-string token was rejected for putting a credential in server logs.

**DD10 — RESOLVED, not deferred: `manage.py runserver` already serves
WebSocket in dev; `backend/Dockerfile` and `entrypoint.sh` get a zero diff.**
Django's `get_commands()` iterates `reversed(apps.get_app_configs())` and
`update`s, so an earlier `INSTALLED_APPS` entry overrides a later app's
same-named command. `daphne` sits at index 5 and `django.contrib.staticfiles`
at index 6 (`settings.py:41-42`), so Daphne's ASGI `runserver` wins — which is
precisely what the pre-existing `# daphne must be listed before
django.contrib.staticfiles` comment at `settings.py:40` was protecting.
`ASGI_APPLICATION` is already set. Acceptance readback is the startup banner
reading `Starting ASGI/Daphne version … development server`. This unblocks
task sequencing: Redis + `CHANNEL_LAYERS` + routing land before the consumer,
and no Dockerfile task is scheduled.

**DD11/DD13 — The WS client lives inside `useDocument`, not in a separate
hook, and merges monotonically by revision.** `useDocument` already owns
`document`, already resets on its `${orgSlug}:${docId}` tracked key, and is
the sole producer of the `revision` prop `DiagramCanvas` is keyed on. The
guard `incoming.revision <= prev.revision ? prev : incoming` matters because
the submitter receives both its own refetch and the broadcast; returning
`prev` by identity also makes React bail out of the re-render, so a duplicate
costs zero `cy.json()` calls. On reconnect (capped 1s→10s backoff), every
successful `open` calls `getDocument()` once — proposal §Out of Scope's
"reconnect-and-refetch", nothing more. Close codes `4401`/`4403`/`4404` are
terminal, so a revoked client never hammers the handshake.

**DD12 — No guard is added for `pendingSourceId`/`pendingTargetId`, because a
remote update structurally cannot touch them; a drag guard IS added.**
Verified at `page.tsx:35-36`: both ids are `useState` local to `DocumentPage`
and `useDocument` never receives a setter for them, so `setDocument` cannot
write them and the click-click gesture survives by construction. The one
intended interaction — `effectiveSourceId` collapsing to `null` when the
remote update removed the pinned class — is already declared correct by the
comment at `page.tsx:67-73` for the local-refetch case. The drag is a real
risk: a remote class addition makes `newClassIds.length > 0` and fires
`cy.layout(...).run()` mid-grab, so `DiagramCanvas` gains
`draggingRef`/`pendingUpdateRef` with `grab`/`free` handlers that defer the
sync until the drag ends.

## 2026-09-13 — Cycle 11 apply: implementation complete (uml-relationship-kinds)

`sdd-apply` implemented all tasks (Phases 1–3; Phase 4 is this entry, Phase 5
is verification) from
`openspec/changes/2026-09-13-uml-relationship-kinds/tasks.md`, following
design.md's DD1–DD6 with strict TDD, single PR, `backend/` diff empty (all
four UML 2.5 kinds were already wired end-to-end; only the frontend
hardcoded `association`). The canvas could previously only draw
associations even though aggregation, composition, and generalization were
already valid on the wire — this cycle closes that gap.

**DD1 — Style per kind with data-attribute selectors (`edge[kind = "..."]`),
not a `classes` string.** `toElements` copies `r.kind` into edge `data`; the
`classes` expression (`"self-loop"` or `undefined`) stays byte-identical.
`kind` is a real domain field the proposal already required in `data`, so a
parallel class-string encoding would duplicate the same fact and leave the
prior cycle's exact-equality self-loop assertion
(`DiagramCanvas.test.tsx:108`, `expect(edge.classes).toBe("self-loop")`)
untouched.

**DD2 — Deleted the blanket `"target-arrow-shape": "triangle"` from the
generic `edge` selector; added `"source-arrow-color": EDGE_LINE` beside the
existing `target-arrow-color`.** Verified in Cytoscape source
(`cytoscape.cjs.js:18669-18688`): all four `*-arrow-shape` prefixes default
to `'none'`, so a plain `association` edge now needs no selector of its own
— "no terminator" is the floor, and each kind rule can only *add* one for
its own edges. `source-arrow-color` had to be set explicitly because a
hollow arrow/diamond is stroked with that color
(`cytoscape.cjs.js:30083-30086`) and its default `#999` is not `EDGE_LINE`.

**DD3 — The three kind rules (`generalization`/`aggregation`/`composition`)
are appended at the end of `STYLE`, after `edge.self-loop`, each declaring
only arrow properties.** Per `styfn.getContextStyle`'s verified merge order
(`cytoscape.cjs.js:16090-16117`, later entry wins per-property, no CSS-style
specificity), the kind rules and `edge.self-loop` declare disjoint property
sets (arrows vs. `loop-*`/`control-point-step-size`/`text-margin-y`), so a
self-referencing generalization gets loop geometry *and* a hollow triangle
regardless of relative order — no conflict with the prior cycle's self-loop
fix exists.

**DD4 — The kind `<Select>` (`Tipo de relación`) renders only in the
both-ids-set confirm branch of `AddRelationshipControl`, above the
multiplicity grid; local `useState<RelationshipKind>("association")`, no
prop change.** The pending-source branch is a transient "pick a target"
prompt where kind has no effect until submit, and the kind↔multiplicity
visibility coupling (DD5) only exists in the confirm branch.

**DD5 — `generalization` hides both multiplicity `<Select>`s and
`handleSubmit` sends the literal `"1"` for both ends when kind is
`generalization`, ignoring the hidden state; switching kind resets
nothing.** The payload must be a function of what is visible — sending the
hidden state would let a user pick `0..*`, switch to generalization, and
silently post `0..*`. Deriving at submit instead of resetting on kind change
also means switching generalization→association restores the earlier
choice, matching the prior cycle's "derive, don't effect" shape.

**DD6 — `STYLE` is now exported from `DiagramCanvas.tsx`.** Same reasoning
as `toElements` (prior cycle's DD6): the stylesheet is a plain data
structure carrying the UML notation contract, assertable with zero DOM and
zero canvas — jsdom has no canvas, so rendered arrowheads are untestable any
other way.

Both scope forks were confirmed by the user before proposal: the
first-clicked class (`source`) is the "whole" end for aggregation/
composition, and generalization's multiplicity selects are hidden entirely
rather than rendered disabled. `backend/apps/uml_documents/schemas.py`'s
`RelationshipIn.kind` was already the full 4-kind `Literal`, confirming zero
backend diff. 278/278 frontend tests pass (18 new — 8 in
`AddRelationshipControl.test.tsx`, 10 in `DiagramCanvas.test.tsx`), `npm run
lint` clean, `npm run build` succeeds, `git diff --stat -- backend` is
empty. `sdd-verify`/`sdd-archive` are the remaining steps.

## 2026-09-13 — Cycle 10 apply: implementation complete (uml-document-list)

`sdd-apply` implemented all 20 tasks (Phases 1–9) from
`openspec/changes/uml-document-list/tasks.md`, following design.md's DD1–DD8
with strict TDD, single PR. A created document was previously reachable only
through the redirect that follows its creation; this cycle adds a list so
`/dashboard` shows every document of the active organization.

**DD1 — `list_documents(*, organization) -> list[ProjectDocument]`, mirroring
`create_document`/`get_document`.** `[_to_project_document(row) for row in
UmlDocument.objects.for_organization(organization).order_by("-updated_at")]`.
Returning a `QuerySet[UmlDocument]` for `api.py` to map, or a `.values()`
projection reaching into `row.data`, were both rejected: either would break
the services-module invariant that it is the sole place reassembling a
`ProjectDocument` from a row + decoded `codec` triple.

**DD2 — New `DocumentSummaryOut(Schema)` with `id`, `name` (flat), `revision`,
`updated_at` — no `model`/`layout`.** Reusing `DocumentOut` was rejected: its
`model`/`layout` are full per-class/attribute/relationship encodings that no
list row renders, and nesting `name` under a `MetadataOut` would drag in a
required `description` field the list never shows.

**DD3 — `GET ""` on `documents_router`, gated by `resolve_membership` only —
no `require_role`.** Pinned to `get_document_view`'s existing gate (verified:
`api.py`'s single-document read has no role check), so a `VIEWER` who can open
a document can also see it listed. Adding `require_role` here would have been
an unrequested permission tightening.

**DD4 — `listDocuments(orgSlug)` = `apiFetch<DocumentSummary[]>(base(orgSlug))`,
no `try/catch`.** Matches every other wrapper in `lib/uml_documents.ts`: a
swallowed error would render "no tienes diagramas" for what is actually a
permission or network failure.

**DD5 — `useDocuments(orgSlug)` is local `useState` + a render-time
tracked-slug reset, cloned from `useMembers`, not a Jotai atom.** A document
list has exactly one consumer (the dashboard container) — the same condition
under which `state/document.ts` and `state/members.ts` both rejected a shared
atom. A module atom would additionally paint the previous org's documents for
a frame after switching orgs.

**DD6 — `DocumentList` rows are real `<Link href="/documents/{id}">` anchors,
not `onClick` handlers; zero documents renders empty-state copy, not `null`.**
A list row is a real destination (unlike `CreateDocumentForm`'s post-mutation
redirect to an id that does not exist ahead of time), so it needs a real
anchor for middle-click/new-tab/prefetch. An empty list is a first-run state
the user must see, unlike `OrgSwitcher`'s "nothing to switch" `null`.

**DD7 — No date column; rows show only `{doc.name}` and `Revisión
{doc.revision}`.** No date-formatting helper exists in this codebase, and
locale-dependent formatting in a Client Component risks hydration mismatches.
`updated_at` is still fetched and still orders the list server-side.

**DD8 — `dashboard/page.tsx`: `useDocuments`/`showCreateForm` called above the
`organizations.length === 0` early return; a new "Mis Diagramas" section
discloses the unmodified `CreateDocumentForm` behind a "Nuevo Diagrama"
button, then renders `{loading ? "Cargando…" : <DocumentList .../>}`.**
Inlining the form horizontally in the header, or a modal, were both rejected:
the header control must be a button, `CreateDocumentForm` is a full form, and
no modal primitive exists in `components/ui/` (already rejected for this
reason in Cycle 9). Gating the empty state behind `loading` prevents "no
tienes diagramas" flashing on every mount.

`backend/apps/uml_documents/models.py` and its migrations are byte-for-byte
unchanged — purely additive on both sides, no schema change. 319/319 backend
tests pass (8 new), 251/251 frontend tests pass (23 new — 2 in
`lib/uml_documents.test.ts`, 4 in the new `state/documents.test.ts`, 3 in the
new `DocumentList.test.tsx`, 5 in the extended `dashboard/page.test.tsx`, plus
1 in `test_schemas.py` and 2+5 in `test_services.py`/`test_api.py`).
`sdd-verify`/`sdd-archive` are the remaining steps.

## 2026-09-13 — Cycle 9 apply: implementation complete (uml-canvas-remove-ui)

`sdd-apply` implemented all 15 tasks (Phases 1–7) from
`openspec/changes/uml-canvas-remove-ui/tasks.md`, following design.md's
DD1–DD8 with strict TDD, single PR, frontend-only (`backend/` diff empty —
`RemoveClass`/`RemoveAttribute`/`RemoveRelationship` already existed on the
command bus and were only unreachable from the UI). This closes the
create/destroy gap left deliberately open by the prior `uml-canvas-ui`
cycle: a diagram could previously only grow.

**DD1 — Three new `UmlCommandIn` members, fields copied verbatim from the
Pydantic schemas.** `{type: "RemoveClass"; class_id}`,
`{type: "RemoveAttribute"; class_id; attribute_id}` (both fields required —
attribute ids are only unique within a class), `{type: "RemoveRelationship";
relationship_id}` (only one field — a relationship id is globally unique).
The union's stale "only three commands" comment now names the six wired
shapes and calls out `RenameClass` as the sole remaining gap. Guessing a
generic escape-hatch shape was rejected — the two asymmetric remove payloads
would only surface a wrong-shape 422 at runtime, not at compile time.

**DD2 — Stale selection eliminated by derivation, not an effect.** Every
control stores only the raw selected id in `useState` and re-derives
`options.find(o => o.id === rawId) ?? null` on every render, feeding
`value={selected?.id ?? ""}` to its `<select>`. A `useEffect` clearing a
dead id was rejected — it fires *after* a render that already holds the
dead id, so a fast submit between refetch and effect could still post a
stale id, which is exactly the silent no-op this cycle exists to prevent.

**DD3 — Leading placeholder option, submit disabled on `null`.** Every
`<select>` renders `<option value="">...` and its submit control is
`disabled` when the derived selection is `null`, so a destructive control
never arrives pre-aimed at something the user never chose. Preselecting
`options[0]` (as `AddAttributeForm` does) was rejected for these three
controls; `AddAttributeForm`'s own init-only preselect shares DD2's
staleness bug but is out of scope this cycle (recorded as an open item).

**DD4 — `RemoveClassControl`'s confirmation is a second render branch, not
`window.confirm()`.** A `confirming` boolean swaps the select for a warning
plus `Confirmar eliminación`/`Cancelar`, the same early-return-on-state
shape `AddRelationshipControl` already uses for pending-source/pending-target.
`window.confirm()` was rejected as untestable under RTL/jsdom without
stubbing a global and as the one UI primitive this codebase uses nowhere;
no modal primitive exists in `components/ui/` and introducing one for a
single call site was judged out of scope.

**DD5 — Cascade count is derived at render, never stored.** `RemoveClassControl`
computes `relationships.filter(r => r.source.class_id === id ||
r.target.class_id === id).length` fresh on every render (including inside
the confirm branch), mirroring `remove_class`'s own source-or-target filter
and `page.tsx`'s pre-existing `danglingRelationshipCount` derivation. Per
design.md's explicit rationale, the confirmation branch always appears
(spec: class removal always confirms) but the "también N relación(es)" line
is omitted when the count is 0 rather than rendering a "0 relación(es)"
line — a deliberate, documented refinement of the spec's literal wording,
not a silent deviation.

**DD6 — Relationship options are labelled by endpoint names and kind, not
multiplicity.** `` `${name(source)} → ${name(target)} (${kind})` `` with
`name(id) = classes.find(c => c.id === id)?.name ?? id`. Reusing the canvas
edge label (`formatMultiplicity`) was rejected — multiplicity does not
disambiguate two relationships between the same class pair. Dangling
relationships are listed, not filtered, using the raw `class_id` fallback:
`toElements` already drops them from the canvas, so this control is the
only way to remove one.

**DD7 — All three controls render after the existing `Add*` block, under a
new `<h2>Eliminar</h2>` heading, in class → attribute → relationship order.**
`ValidationPanel` stays above the forms, unmoved. Interleaving each `Remove*`
beside its `Add*` was rejected — grouping destructive controls behind one
heading reduces the chance of a mis-click landing on a remove select while
adding.

**DD8 — Error handling and submit locking copied verbatim from
`AddAttributeForm`/`AddRelationshipControl`.** `useState` `error`/
`submitting`, `catch (err) { err instanceof ApiError ? err.detail : "Ocurrió
un error inesperado. Intenta de nuevo." }`, `<p role="alert"
className="text-sm text-destructive">`, `variant="destructive"` buttons. A
shared `useCommandSubmit` hook extraction was rejected this cycle — it would
rewrite three already-verified components; logged as tech debt for a future
cycle now that 6 of 7 command shapes duplicate the block.

All 4 modified `web-uml-canvas` requirements pass their scenarios; the full
frontend suite and `npm run lint` are clean (Phase 7); `git diff --stat --
backend` is empty. `sdd-verify`/`sdd-archive` remain.

*Process note*: the three preceding cycles that actually built the canvas
domain (`uml-canvas-ui`, `uml-command-bus`, `uml-document-persistence`, all
merged 2026-09-12 per `git log`) never got a `docs/ai/DECISIONS_LOG.md`/
`CURRENT_STATE.md` sync entry — a pre-existing gap this apply does not
attempt to backfill, since it is out of this change's assigned scope.

## 2026-09-11 — Cycle 6 apply: implementation complete (email-verification-password-reset)

`sdd-apply` implemented all 24 tasks (Phases 1–7) from
`openspec/changes/email-verification-password-reset/tasks.md`, following
design.md's DD1–DD6, strict TDD, single PR with maintainer-approved
`size:exception`. Backend `pytest -q`: 233/233 pass. Frontend `vitest run`:
168/168 pass (17 new). No regressions in either suite.

**DD1 — Single-table token with fast hash lookup.** One `EmailToken` model
(`purpose ∈ {verify, reset}`), `token_hash = sha256(raw).hexdigest()`
(`unique=True`), raw = `secrets.token_urlsafe(32)`. A slow password-style
hash was rejected: 256 bits of CSPRNG entropy is not brute-forceable, so a
slow hash would only add a full-table-scan cost per submission for no
security benefit — `apps/users/tokens.py`.

**DD2 — Purpose column, not two tables.** `EmailToken.purpose` distinguishes
`verify`/`reset` rather than two separate models — identical shape, identical
cooldown/cap query, one migration instead of two.

**DD3 — Throttle by querying `created_at`.** `resend_verification` and
`request_password_reset`'s throttle branch share one query helper
(`_cooldown_active`/`_hourly_cap_reached` in `apps/users/services.py`):
60s cooldown, 5-per-rolling-hour cap. No new dependency (`django-ratelimit`
rejected) — the table already stores the needed timestamp.

**DD4 — Anti-enumeration lives in the service, not the view.**
`request_password_reset` returns `None` on every path (miss, hit, throttled);
`api.py` returns one module-level constant `MessageOut`. The miss/throttled
paths additionally call `time.sleep(_RESET_ANTI_ENUMERATION_DELAY_SECONDS)`
(0.3s) before returning, approximating — not eliminating — the hit path's
real SMTP-send response time (resolved Open Question: exact timing parity
would require a background job queue, explicitly out of scope; the residual
gap is an accepted risk at this project's scale).

**DD5 — Link URL from `FRONTEND_BASE_URL` env var.** `EMAIL_BACKEND/HOST/
PORT/TIMEOUT/DEFAULT_FROM_EMAIL` and `FRONTEND_BASE_URL` are all
`env(...)` with Django's own defaults in `settings.py` — no Mailpit literal
reaches source; `docker-compose.yml`'s new `mailpit` service (SMTP 1025, UI
8025) is reached only via `backend/.env` values documented in
`backend/env.example`. Verified end-to-end at runtime: a real registration
through Mailpit produced a verification email whose link used the
configured `FRONTEND_BASE_URL`, and posting that emailed token to
`/api/auth/verify-email` set `is_verified=True`.

**DD6 — Banner dismissal is session-only (jotai atom), not `localStorage`.**
`state/session.ts`'s new `verifyBannerDismissedAtom` is a plain atom, never
`atomWithStorage`. Unlike `state/organizations.ts`'s active-org key (a
preference that must survive reload), a verification reminder is a nag that
should return next session until resolved — persisting it would also
re-introduce that module's documented SSR hydration-mismatch problem.

**Minor deviation from tasks.md's exact wording**: `(auth)/forgot-password/
page.tsx` is not `Suspense`-wrapped — `ForgotPasswordForm` never calls
`useSearchParams()`, so no boundary is required (matches
`(auth)/register/page.tsx`'s existing precedent, per `(auth)/login/
page.tsx`'s own docblock on when the boundary is actually needed).

## 2026-09-06 — Cycle 5 apply: implementation complete (ssr-protected-routes)

`sdd-apply` implemented all 19 tasks (Phases 1–8) from
`openspec/changes/ssr-protected-routes/tasks.md`, following design.md's
DD1–DD8 (extending proposal.md's D1–D8) with strict TDD, single PR,
frontend-only. 102/102 frontend tests pass (15 new), `backend/`
byte-for-byte unchanged, no new migration.

**D1–D8 summary** (full rationale in `proposal.md`): server-side route
protection closes the gap where `SessionGuard`'s client-only gate let an
anonymous or invalid-session direct/no-JS request receive protected RSC
markup before any client script ran (D1/D2). Implemented as one new module
(`lib/server-session.ts`, D1) rather than Next middleware/`proxy.ts` (D1
rejects it — Edge runtime can't reach the session backend without another
network hop) or duplicating logic per page (D1 also rejects per-page checks
as drift-prone). `SessionGuard` stays untouched (D4) — server-side validity
checking is additive defense-in-depth, not a replacement for the client
skeleton/error/retry UX. Non-`401`/`403` failures (5xx, network errors)
throw and are caught at the gate, rendering normally instead of redirecting
(D2 — an outage must never be misread as a logout).

**DV1–DV5** (design.md's own deviation table, confirmed exactly as
designed): (1) `requireUser(nextPath: string)` takes an explicit required
parameter — Next 16 has no server-side pathname API, so the proposal's
implied path-derivation is impossible; each route group passes its own
canonical literal. (2) `requireUser` catches `getServerUser`'s throw and
returns `null` rather than propagating it — an uncaught throw would hit
Next's error boundary (no `error.tsx` exists) and produce a 500, contradicting
the "falls through to render normally" spec scenario. (3) Added
`lib/__tests__/env.test.ts` (2 cases) — not in the proposal's Affected
Areas, but `internalApiUrl` is evaluated at import time and cannot be
exercised from `server-session.test.ts` (which mocks `@/lib/env` wholesale).
(4) `(app)/layout.tsx`'s docblock needed a rewrite, not just "one line" —
its prior text asserting "no server session exists" became false. (5) The
spec delta's scenario count differs from D7's "all four existing
scenarios" miscount — harmless, already identified by `sdd-spec`.

**Two findings discovered only during Phase 6's mandatory manual
verification** (`docker compose up` + the DD8 8-step `curl` checklist),
not anticipated by design.md, both documented in `tasks.md` Phase 6 and
`CURRENT_STATE.md`:

1. **`ALLOWED_HOSTS` gap.** Django's `CommonMiddleware` rejected the
   `Host: backend:8000` header the frontend container's server-side fetch
   sends inside the Docker network (`400 Bad Request`), which `getServerUser`
   correctly treated as a 5xx-class failure and silently degraded to the
   client-retry fallback — never crashing, but also never proving the
   redirect path. Fixed by adding `ALLOWED_HOSTS: localhost,127.0.0.1,backend`
   to `docker-compose.yml`'s `backend.environment` (same precedence-over-
   `env_file` pattern DD5 already establishes for the frontend's
   `INTERNAL_API_URL`), and documenting the requirement in
   `backend/env.example`.
2. **DD8's literal body-emptiness check doesn't hold, but the spec
   requirement it stands in for does.** design.md's Technical Approach
   claims "nothing has flushed when the gate throws"; verified against both
   `next dev` and a real `next build && next start` production run that
   Next.js 16.3.3 always streams a small inert `<html id="__next_error__">`
   shell alongside a `redirect()`-triggered 307 (a `NEXT_REDIRECT` error
   digest + dev-mode stack trace, consumed by the client router in a real
   browser). It contains zero dashboard/org data and zero `AppTopbar`/
   `SessionGuard`-authenticated markup, so the actual spec scenario ("the
   response body contains no protected-route markup") holds — but DD8's
   `rg -c "<html" body.txt` check, taken literally, does not. Not silently
   passed: recorded here and in `tasks.md` for `sdd-verify`/a future design
   correction to weigh.

`sdd-verify`/`sdd-archive` are the remaining steps.

## 2026-09-06 — Cycle 4 apply: implementation complete (tenant-aware-registration-login)

`sdd-apply` implemented all 23 tasks (Phases 1–9) from
`openspec/changes/tenant-aware-registration-login/tasks.md`, following
design.md's DD1–DD8 (extending proposal.md's D1–D8) with strict TDD,
single PR. 185/185 backend tests pass, 87/87 frontend tests pass (17 new),
no new migration file, `backend/apps/{users,organizations}/{models,api,
schemas,constants}.py` byte-for-byte unchanged as required.

**Backend** (Phases 1–4): `organizations/services.py` gained three additive
functions — `build_slug_base`/`derive_workspace_name` (pure, DB-free,
`hypothesis`-property-tested in the new `test_slug_properties.py`) and
`generate_unique_slug` (DB-touching, bounded 5-attempt suffixed retry +
final long-token fallback, raising `OrganizationError` on total exhaustion).
`users/services.py::register_user` became `@transaction.atomic` and now
provisions exactly one `Organization` + `OWNER` `Membership` per
registration via the existing, unchanged `create_organization`; a forced
`OrganizationError` during provisioning rolls the `User` back too (asserted
via `User.objects.count() == 0`). `test_registration_does_not_auto_create_an_organization`
was rewritten into its inverse (`test_registration_provisions_exactly_one_organization`)
per D7's REMOVED+ADDED requirement pair. `seed_demo.py` needed only a
docstring/`help` text correction — each demo user now also owns an
auto-provisioned personal workspace in addition to `acme-demo`, verified by
a new idempotency-safe assertion.

**Frontend** (Phases 5–8): `lib/next-path.ts` gained `isSafeNext` (the
precedence-rule predicate `LoginForm` needs), with `safe()` re-expressed
through it, byte-identical behavior. `state/organizations.ts` gained
`useSetActiveOrg()` (the write half of `useOrganizations`, extracted so the
auth forms can set the active org without mounting the fetch effect).
`LoginForm.tsx`'s submit handler now branches on `listOrganizations()`
directly (never `useOrganizations()`, which would 401 on the login page):
a valid `next` wins unconditionally; otherwise 0 orgs → `/dashboard`
unchanged, 1 org → set active + `/dashboard`, 2+ orgs → the new
`/select-organization` picker; a post-login org-fetch failure degrades to
`/dashboard` without reusing the login error. `RegisterForm.tsx` adopts the
sole provisioned org (fetched via `listOrganizations()` post-register, per
D2's rejection of org data in `UserOut`) before redirecting, non-fatally on
fetch failure. The post-login picker landed as `components/workspace/OrgPicker.tsx`
(presentational, no `activeSlug` — nothing is active yet) plus a new
`app/(gate)/` route group (`SessionGuard` + centered-card shell, no topbar)
hosting `/select-organization`; `OrgSwitcher.tsx`'s private `ROLE_LABELS`
moved to a shared `components/workspace/roleLabels.ts` so both components
read the same translation table.

Deviations from the proposal, all called out and justified in design.md's
Deviations table (DV1–DV5), confirmed exactly as designed with no further
drift:

1. **`state/organizations.ts` gains `useSetActiveOrg()` (DV1)** despite the
   proposal marking it Untouched — additive only, `useOrganizations`'s
   public shape unchanged.
2. **`lib/next-path.ts` gains `isSafeNext` (DV2)**, not in the proposal's
   Affected Areas — required for the `next`-precedence rule; `safe()`
   stayed byte-identical (all 4 pre-existing tests still pass unmodified).
3. **`OrgSwitcher.tsx`'s `ROLE_LABELS` moved to `roleLabels.ts` (DV3)** —
   zero behavior change, confirmed via the pre-existing `OrgSwitcher.test.tsx`
   passing unmodified as an approval test before and after the extraction.
4. **A new `app/(gate)/` route group (DV4)** — cheaper than reusing `(app)`
   (would double-render via `AppTopbar`) or `(auth)` (no session guard).
5. **The provisioned org is read from `GET /api/orgs`, not the register
   response (DV5)** — D2 already rejects org data in `UserOut`; no spec
   text change, same observable scenario.

One process note, not a design deviation: `generate_unique_slug` was
initially added to `organizations/services.py` in the same edit as the pure
helpers (Phase 1), ahead of Phase 2's dedicated RED test. This was caught
and corrected before the RED/GREEN evidence was recorded — the function was
reverted, its RED test written and confirmed failing (`AttributeError`),
then the function was reinstated as the GREEN step, preserving a truthful
TDD cycle for Phase 2.

## 2026-09-06 — Cycle 3 apply: implementation complete (frontend-auth-integration)

`sdd-apply` implemented all tasks from
`openspec/changes/frontend-auth-integration/tasks.md`, across 3 chained PRs
(`stacked-to-main`, mirroring Cycle 2's split), following design.md's DD1–DD7
(extending the proposal's D1–D8) with strict TDD. 67/67 frontend tests pass,
`npm run lint` clean, `next build` succeeds, `backend/` byte-for-byte
unchanged across all 3 PRs.

- **PR 1** (Phase 0–2): `frontend/env.local.example`; `lib/api.ts` rewritten
  as the credentialed CSRF-aware transport seam (D3); domain clients
  `lib/auth.ts`/`lib/organizations.ts`.
- **PR 2** (Phase 3–5): Jotai state (`state/session.ts`, `state/organizations.ts`,
  D5); `SessionGuard` (D1/D4) and `(auth)`/`(app)` route-group layouts (D2);
  `LoginForm`/`RegisterForm` and their routes.
- **PR 3** (Phase 6–8, this entry): the organization panel (`OrgSwitcher`,
  `OrgEmptyState`, `CreateOrgForm`, `AppTopbar`, `/dashboard`); the
  session-aware landing navbar (proposal Q3); full-suite verification and
  this doc sync.

Deviations from design.md/tasks.md, documented inline in `tasks.md` per
phase, summarized here:

1. **`lib/auth.ts` exports `fetchMe()`, object-arg signatures (PR1, Phase 2).**
   design.md's "Interfaces" section (the literal exported TS contract) was
   followed over tasks.md's looser prose (`getMe()`, positional args):
   `register(input)`, `login(input)`, `fetchMe()`, `createOrganization(input)`
   with `slug` **required** — the backend's `OrganizationIn` schema has no
   slug default, so tasks.md's `createOrganization(name)` shorthand cannot
   construct a valid request body against the real backend.
2. **Route-group layouts get no `LayoutRoutes` entry at all (PR2, Phase
   4.1).** DD4 predicted both `(auth)/layout.tsx` and `(app)/layout.tsx`
   would key on `"/"` in the generated `.next/types/routes.d.ts`; the actual
   generated shape after adding both groups is stricter — route groups
   don't appear in that type at all. DD4's conclusion (explicit
   `{children: React.ReactNode}` typing) still holds, but for a stronger
   reason than originally stated.
3. **`/login` needs a `<Suspense>` boundary (PR2, Phase 5.5).** `LoginForm`
   calls `useSearchParams()`; Next's production build fails without a
   wrapping `Suspense` boundary on a page that calls it from a Client
   Component. Not called out in design.md — discovered via the mandatory
   `frontend/AGENTS.md` doc-gate read, not from memory.
4. **`AppTopbar`/`(app)/layout.tsx` wiring deferred from PR2 to PR3 (Phase
   4.7/5.6).** `AppTopbar` (the only logout affordance, task 5.6) didn't
   exist until Phase 6, so `(app)/layout.tsx` temporarily rendered
   `<SessionGuard>{children}</SessionGuard>` only in PR2; PR3 completed the
   originally intended `<SessionGuard><AppTopbar/>{children}</SessionGuard>`
   tree and picked up 5.6's deferred logout test as 6.7.
5. **`OrgSwitcher`/`CreateOrgForm` made purely presentational (PR3, Phase
   6.1/6.5).** Both were designed self-contained (owning their own
   `useOrganizations()` call) in tasks.md's prose, but `AppTopbar` and
   `app/(app)/dashboard/page.tsx` are siblings under `(app)/layout.tsx` (not
   parent/child), so two self-contained hook instances would each fire an
   independent `listOrganizations()` GET on every dashboard visit. Both
   components now take `organizations`/`activeSlug`/`onCreate`/`onSelect` as
   props from their container instead (container-presentational split),
   collapsing 3 potential hook instances down to 2 (one per container,
   architecturally unavoidable given the sibling layout). The corresponding
   unit tests moved from hook-mocking/localStorage-integration style to
   plain prop-driven assertions; the localStorage persistence and
   stale-slug-fallback behavior stay covered by Phase 3's
   `state/__tests__/organizations.test.ts`, and the full "create → appears
   in list → becomes active without refetch" scenario is proven end-to-end
   in `app/(app)/dashboard/__tests__/page.test.tsx`.
6. **Role label "Lector", not "Visualizador" (PR3, Phase 6.2).** proposal.md
   Q2 already establishes "Propietario / Editor / Lector" as the Spanish
   role-label convention; `OrgSwitcher`'s `ROLE_LABELS` was corrected to
   match rather than introduce a second, inconsistent translation for
   `VIEWER`.
7. **`Navbar.tsx` became a Client Component (PR3, Phase 7.2).** Reading
   `useSession()` to show "Ir al panel" vs. "Iniciar sesión"/"Registrarse"
   requires `"use client"`; confirmed the pre-existing, un-mocked
   `app/__tests__/page.test.tsx` (`Home` page test, which renders `<Navbar/>`
   without stubbing `fetch`) still passes — the real `fetchMe()` call
   rejects harmlessly into `useSession()`'s `error` state after the test's
   synchronous assertions already ran, no regression.

8. **`app/(app)/dashboard/page.tsx` is a full Client Component, not the
   Server-Component-shell pattern (PR3, Phase 6.6; found by `sdd-verify`,
   backfilled here).** design.md's DD3 and File Architecture table describe
   every `(app)` page as a thin static server shell delegating to client
   children, the pattern `(auth)/login/page.tsx` and
   `(auth)/register/page.tsx` follow. `dashboard/page.tsx` instead needs
   `useOrganizations()` directly to own the container half of Phase 6's
   container-presentational split (deviation 5 above), so it is `"use
   client"` end to end. This is not a security regression — a fully
   client-rendered page never puts protected data in the server-rendered RSC
   payload at all, which is stricter than the intended pattern, not weaker —
   and it does not break any spec scenario (17/17 still pass). It is,
   however, the precedent for any future `(app)` page: reach for the
   Server-Component-shell pattern by default, and only fall back to a full
   Client Component when the page's own data (not a child's) is needed
   before render, as here.

`docs/ai/CURRENT_STATE.md` reflects the full post-cycle state, including the
manual smoke checklist (real cross-origin cookie flow, task 8.5) not yet run
against a deployed cross-domain origin. Success criteria from `proposal.md`
are met with these eight noted, non-blocking deviations. `sdd-verify` ran
(`pass_with_warnings`, 0 CRITICAL) and flagged deviation 8 above plus a stale
`web-session/spec.md` line describing the pre-DD2 cookie-only CSRF reading,
both fixed in this same pass; `sdd-archive` remains.

## 2026-09-06 — Cycle 2 follow-up: split `identity` into `users` + `organizations`

Pre-merge, `backend/apps/identity/` was refactored into two apps —
`backend/apps/users/` (`User`, `UserManager`, `register_user`/
`authenticate_user`, `auth_router`) and `backend/apps/organizations/`
(`Organization`, `Membership`, `TenantScopedModel`, the tenancy/membership
services, `permissions.py`, `organizations_router`/`memberships_router`) —
at the project owner's explicit request, per Django's one-app-per-domain
convention. `AUTH_USER_MODEL` is now `"users.User"`; `INSTALLED_APPS` lists
both apps in place of `apps.identity`. Done before any real deployment (no
migration or data cost), so this is a rename/split, not a runtime migration.
168/168 backend tests pass (the app-registration test split into two,
+1 net). `openspec/changes/multi-tenant-identity/{proposal,design,tasks}.md`
and their specs were updated to reference the new module paths; the
2026-09-05 entry below is left as the historical record of that PR's
original (single-app) implementation.

## 2026-09-05 — Cycle 2 apply: implementation complete (multi-tenant-identity)

`sdd-apply` implemented all tasks from
`openspec/changes/multi-tenant-identity/tasks.md` in `backend/apps/identity/`,
across 3 chained PRs (`stacked-to-main`), following design.md's DD1–DD7
(recorded there, extending the proposal's D1–D7) with strict TDD. 167/167
backend tests pass (128 baseline + 39 new this PR), zero regression to
`backend/apps/uml_modeling/` (byte-for-byte unchanged) or `/health`.

- **PR 1**: app skeleton, `AUTH_USER_MODEL = "identity.User"`, `User`/
  `Organization`/`TenantScopedModel`/`Membership` models, the project's
  first migration.
- **PR 2**: `services.py` (all invariants — register/authenticate, org
  CRUD, membership add/role-change/remove, the shared `_assert_not_last_owner`
  guard) and `permissions.py` (`resolve_membership`/`require_role`).
- **PR 3**: `schemas.py`, `api.py` (three routers + centralized exception
  handling per DD6), the DD2 cross-origin session/CSRF settings block, and
  `backend/env.example`.

Three deviations from design.md, found only once real HTTP wiring was
exercised against the actually-installed django-ninja version (full
detail in `tasks.md`'s Phase 5 note):

1. **No `NinjaAPI(csrf=True)` kwarg.** The installed django-ninja
   (resolved as 1.7.0 from `requirements/base.txt`'s `>=1.1,<2.0` range)
   has no `csrf` constructor parameter. CSRF is enforced with equivalent
   coverage instead: `django_auth` (ninja's session auth) enforces the
   double-submit check by default for every authenticated unsafe request;
   the two anonymous unsafe endpoints (`register`, `login`) call
   `ninja.utils.check_csrf()` explicitly. Proven behaviorally by
   `test_cross_origin_session.py`.
2. **Mount-prefix path params need an explicit `Path[str]` annotation.**
   `org_slug` lives in `memberships_router`'s mount prefix, not in each
   operation's own relative path; this ninja version does not
   auto-classify it as a path source (it silently defaulted to "query",
   producing 422s) the way design.md's "Ninja binds the prefix path
   parameter" note assumed. Fixed with `ninja.Path[str]`; no behavior
   change beyond the declared parameter source.
3. **`email-validator` added as a new dependency.** design.md's schema
   code block types `email: EmailStr`, which pydantic requires
   `email-validator` for. The proposal's Affected Areas table states "no
   new dependency" for `backend/requirements/*`; that line is now
   inaccurate by this one small, pure-Python package. Kept the design's
   exact schema shape rather than deviate into hand-rolled validation.

`docs/ai/CURRENT_STATE.md` reflects the full post-cycle state. Success
criteria from `proposal.md` are met with these three noted, non-blocking
deviations; `sdd-verify`/`sdd-archive` remain.

## 2026-09-05 — Cycle 1 apply: implementation complete (canonical-uml-model)

`sdd-apply` implemented all 23 tasks from
`openspec/changes/canonical-uml-model/tasks.md` in `backend/apps/uml_modeling/`,
following DD1–DD9 below exactly, with strict TDD (RED→GREEN→REFACTOR,
`pytest` + `hypothesis`, no `pytest-django` DB fixtures needed). 80 backend
tests pass with zero regression to the pre-existing health-check smoke test
(81/81 total). Notes for `sdd-verify`:

- **`EMPTY_ELEMENT_NAME` on whitespace-only names**: implemented as the
  design's noted deliberate superset — a name is empty if
  `name.strip() == ""`, not only `name == ""`. The spec scenario only
  shows the literal empty-string case; whitespace-only is additionally
  covered and tested (`test_empty_element_name_flags_a_whitespace_only_class_name`).
- **Duplicate-name rules anchor on the second (and later) occurrence**,
  not the first: `DUPLICATE_CLASS_NAME`, `DUPLICATE_ATTRIBUTE_NAME`, and
  `DUPLICATE_ENUMERATION_LITERAL` each flag every element after the first
  one sharing a name, so the diagnostic count is deterministic
  (N-1 diagnostics for N same-named elements). Neither the spec nor the
  design mandated a specific anchor; this was the implementation choice.
- **Integration coverage for uml-validation REQ4** (every `path`/
  `element_ref` resolves to a real element) was added as one dedicated
  test (`test_validation_integration.py`) exercising the full 10-rule
  registry together via `validate()`, plus a shared
  `diagnostic_resolves_to_a_real_element()` helper in `tests/factories.py`
  (task 7.6). The helper was not retrofitted into every individual
  per-rule test file (each already asserts `path`/`element_ref` directly
  against its own fixture) — flagged here rather than silently deviating.
- No deviation from DD1–DD9 or the module layout; no models/migrations/
  urlconf/schemas were added, matching the design's explicit scope limit.

## 2026-09-05 — Cycle 1 design: canonical UML domain, project document, validation engine

Architecture decisions for the `canonical-uml-model` change (SDD design phase).
The scope-level decisions D0–D8 are recorded in
`openspec/changes/canonical-uml-model/proposal.md`; the decisions below (DD1–DD9)
are the design-level ones that govern how the code is actually shaped.

- **Three layers inside one Django app, with `domain/` as a leaf.**
  `backend/apps/uml_modeling/` is a registration shell (`apps.py` only): no
  `models.py`, no migrations, no urlconf, no Ninja/Pydantic schemas. Inside it,
  `validation/` reads `domain/` and `documents.py` composes `domain/`; nothing
  imports `validation/`, and `domain/` imports nothing local. The whole app
  imports neither Django, Ninja, nor Pydantic, so the single `validate()` entry
  point stays callable from every future channel (HTTP, Channels, XMI import,
  assistant, generation) exactly as document section 10 requires.
- **DD1 — Two enforcement layers, deliberately distinct.** Construction
  invariants raise `ValueError`/`TypeError` from `__post_init__`; model-level
  semantic problems become `Diagnostic`s. The specs demand both: a class-typed
  attribute and an empty `owner_id` must be impossible to construct, while
  duplicate names and dangling references must be reportable, navigable, and
  fixable rather than fatal.
- **DD2 — The boundary between those layers.** Construction rejects only what is
  *unrepresentable or mistyped*; it never rejects user-fixable content. Concretely,
  `Multiplicity(-1, None)` and `Multiplicity(2, 1)` MUST remain constructible,
  because otherwise the `INVALID_MULTIPLICITY` diagnostic could never be produced.
  `Multiplicity` is therefore a deliberately unvalidated value object.
- **DD3 — Frozen dataclasses, `tuple` for ordered collections.** `frozen=True`
  combined with `list` fields is only shallow immutability. Real snapshots are
  needed by the later command bus, undo/redo, and optimistic-revision cycles, and
  immutable sequences also make `hypothesis` shrinking deterministic. The specs'
  word "list" is read as "ordered sequence".
- **DD4 — Explicit static rule registry over a decorator registry.** The ten
  Cycle-1 rules are listed as a `RULES: tuple[Rule, ...]` in `validation/engine.py`,
  importing named functions from `validation/rules/`. This gives deterministic
  diagnostic order, no import-time side effects, no hidden global mutable state,
  a greppable list, and a registry that a test can assert on directly. A `@rule`
  decorator would have made ordering depend on import order.
- **DD5 — Registry injected via default argument**: `validate(model, rules=RULES)`.
  The public one-argument call matches the spec exactly, while the engine's
  aggregation and its "never short-circuit" behaviour can be tested with fake
  rules without touching the real ten.
- **DD6 — Rules keep the bare `(CanonicalUmlModel) -> Iterable[Diagnostic]`
  signature** and build their own local id→element dictionaries, instead of the
  engine passing a shared prebuilt index. This preserves the spec's "callable in
  isolation" requirement with zero setup, and at class-diagram scale (tens of
  elements) the repeated dictionary construction is negligible. Adding an optional
  second parameter later is non-breaking.
- **DD7 — `ElementId = NewType("ElementId", str)`, generated from `uuid4().hex`.**
  Strings serialize to JSON and XMI with no adapter, `NewType` costs nothing at
  runtime, and ids are already the alphabet of the diagnostic `path` grammar.
- **DD8 — Pure mutation helpers take an explicit `now: datetime`.**
  `ProjectDocument.with_model(...)` / `.with_layout(...)` never call
  `datetime.now()` internally, keeping the domain clock-free and deterministic;
  revision and timestamp tests need no `freezegun` or monkeypatching.
- **DD9 — `DiagnosticCode` is a `StrEnum`, path builders live in
  `validation/diagnostics.py`.** The ten codes are fixed and closed, so an enum
  prevents typos and enables exhaustiveness tests; the slash-rooted `path` grammar
  is part of the diagnostic contract and belongs next to `Diagnostic` rather than
  in a separate module.
- **Two refinements to the proposal's file layout.** `validation/rules/structure.py`
  was added because `CLASS_WITHOUT_ATTRIBUTES` fits none of the four originally
  proposed rule files, and no separate `paths.py` was created (see DD9).
- **Normative generalization direction.** For `RelationshipKind.GENERALIZATION`,
  `source` is the specific (child) and `target` is the general (parent). Cycle
  detection runs an iterative DFS over the child→parent digraph and emits exactly
  one diagnostic per cycle, anchored at the lowest-sorted participating class id,
  so the diagnostic count is deterministic. A self-generalization is a length-1
  cycle reported as `GENERALIZATION_CYCLE`; `SELF_ASSOCIATION` stays scoped to
  `ASSOCIATION`.
- **No sequence diagram this cycle.** `openspec/config.yaml` requires sequence
  diagrams for realtime/collaboration flows (Django Channels); no realtime flow is
  in Cycle 1's scope, so the rule does not apply. A `validate()` call-flow diagram
  is documented instead, as the only non-obvious control flow in the change.

## 2026-08-31 — Scope pivot to the real exam spec + stack corrections + dual-mobile clarification + SDD adoption

- **Scope pivot: the real project is the CASE-tool exam spec, not the
  originally-scaffolded generic CRUD app.** `product-04-next-django.md`
  (repo root) was found to be the actual, authoritative exam statement — an
  offline-first collaborative CASE tool for UML class diagramming with
  manual/voice/image/XMI input converging into a `CanonicalUmlModel`,
  realtime collaboration, and automatic generation of a Spring Boot
  backend + Next.js frontend + Android (Capacitor) app from the modeled
  domain. The previously scaffolded Django+DRF/Next.js/Flutter CRUD
  skeleton was infrastructure only and never described this real scope.
  `docs/ai/*` is being reconciled to describe the real target, while
  `product-04-next-django.md` itself stays frozen as the authoritative
  source (per its own section 1) and is never edited to reflect progress.
- **Stack corrections applied** (in progress by parallel workstreams at
  the time of this entry, not yet fully confirmed — see
  `CURRENT_STATE.md`): backend moves from Django REST Framework to
  **Django Ninja**; adds **Django Channels + Daphne** (ASGI) for realtime;
  adds **Argon2** password hashing + **PyJWT**; bootstraps
  **pytest + pytest-django + hypothesis**. Frontend adds
  **Tailwind CSS + shadcn/ui + Cytoscape.js + cytoscape-fcose + Jotai**;
  bootstraps **Vitest + React Testing Library**. Cypress (E2E) bootstrap is
  planned but not yet started by anyone.
- **Dual mobile requirement clarified — both mandatory, not conflicting.**
  The document's own generated-output Android strategy (section 26) is
  **Next.js PWA + Capacitor**, wrapping the same generated Next.js code —
  this applies only to applications the tool generates for its end users.
  Separately, the course instructor explicitly and firmly requires this
  project itself to ship a real **Flutter** mobile client (`mobile/`) for
  the main CASE tool. These are two independent requirements from two
  independent sources; neither supersedes or replaces the other, and both
  must be satisfied.
- **Adopted SDD (Spec-Driven Development) going forward, hybrid mode:
  OpenSpec files + Engram.** The spec document's own section 1 mandates
  deriving use cases, grouping them into cycles, proposing acceptance
  criteria, implementing one use case at a time, and maintaining a
  document of real state separate from the vision document — this is
  effectively an SDD-shaped requirement written directly into the exam
  statement. `openspec/` was initialized at the repo root (`sdd-init`) to
  formalize this: every future feature (starting with `CanonicalUmlModel`
  + `ProjectDocument`/`DiagramLayout` + the validation engine) goes through
  explore → propose → spec → design → tasks → apply → verify → archive,
  with Engram persisting cross-session decisions and context.

## Original scaffold decisions

- **Django settings package named `config`** — keeps the settings/urls/wsgi/asgi
  package name generic and decoupled from any specific app or product name.
- **Env vars via django-environ, no hardcoding** — secrets, hosts, DB
  credentials, and CORS origins must never be committed or baked into code;
  `environ.Env` centralizes reading them with sane `.env` file support.
- **psycopg2-binary over psycopg3** — chosen for tutorial/documentation
  ubiquity: most Django docs, tutorials, and Stack Overflow answers still
  assume psycopg2, and the binary wheel avoids build-toolchain friction in
  the Docker image.
- **CORS via django-cors-headers** — the Next.js frontend is a separate
  origin from the Django API, so cross-origin requests need to be
  explicitly allow-listed rather than silently blocked or wide open.
- **Tailwind intentionally NOT added** — it was not requested by the spec;
  adding it now would be an unnecessary dependency/opinion for a bare
  scaffold.
- **Flutter not dockerized** — mobile apps are built/run via the Flutter
  SDK against emulators/physical devices on the host, not inside a Linux
  container; there is no meaningful way to "run" a mobile app in a
  server-style container.
- **Multi-stage Dockerfiles with dev/prod targets (backend + frontend)** —
  a single Dockerfile serves both live-reload local development (bind
  mounts, dev server) and a leaner production image (built artifacts,
  gunicorn/`next start` or standalone output) without duplicating base
  layers.
- **Env-example files written without the leading dot** (`env.example`,
  `env.local.example`) — the Write/Bash sandbox used to generate this
  scaffold refuses any file path containing the substring `.env`, even for
  placeholder content. Documented in each file and in the root README;
  rename them locally (e.g. `mv env.example .env`) to restore the
  conventional dotfile name.
