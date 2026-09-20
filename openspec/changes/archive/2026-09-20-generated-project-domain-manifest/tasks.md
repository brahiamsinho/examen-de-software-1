# Tasks: Generated Project Domain Manifest

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~755 authored (slice 1 ~575: code ~295, tests ~280 table-driven; slice 2 ~180: compose/script ~23, docs ~60, spec/gate-evidence/session note ~97) |
| 400-line budget risk | High against 400; Medium against the project review budget of 800 (inside it ONLY if tests stay table-driven) |
| Chained PRs recommended | No |
| Suggested split | Single PR, two sequential revertable slices (slice 1 green offline before slice 2 starts) |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

Table-driven constraint (carried from design, previous change overshot to ~1246 lines): every test module uses ONE `pytest.mark.parametrize` table per behaviour, never one test function per entity, column, or ColumnType. Test line budget: decoupling ~90, attributes ~90, relationships ~70, manifest ~115 (incl. drift guard), determinism ~30, CLI ~80. If `git diff --stat` at 8.3 exceeds ~600 for slice 1, stop and collapse near-duplicate tests before slice 2.

Test-scope rule (DD101/DD120): pytest sees only `backend/` as `/app`. NO pytest task reads `scripts/` or `docker-compose.yml`; those are proven by the gate, gate-evidence.md and one negative check. `docker compose down` MUST never be used. No commit tasks (orchestrator asks the user).

Runner for every RED/GREEN step: `docker compose exec -T backend pytest -q <path>` (no host Python).

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Builder + serialize + CLI + 5 pytest modules + INSTALLED_APPS | PR 1 | `docker compose exec -T backend pytest -q apps/domain_manifest` | N/A: pure offline app, proven by pytest (CLI via subprocess) | Remove `backend/apps/domain_manifest/` and the `INSTALLED_APPS` line |
| 2 | Compose `generate-manifest` + gate step 4 + evidence + docs | PR 1 | N/A (DD101: not reachable from pytest) | `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh` plus 1 negative check | Revert compose stanza, script step 4, docs; gate returns to its 3 proven steps |

## Phase 1: Observe unverified facts (slice 1, BEFORE any dependent assertion)

- [x] 1.1 Read-only: print the relational sample model (`docker compose exec -T backend python -c ...` over `apps.generation_runner.samples.sample_model`). Record: entity count, `product_tag` unique constraints (any oneToOne?), nullability of `vehicle` subclass columns, and confirm the discriminator column and `discriminator_values` shape.
- [x] 1.2 Reconcile: spec names the read operation `get`, design DD125 table says `findById`; decide one and edit the losing artifact. Record any contradiction of the design as DD132+ in `openspec/changes/generated-project-domain-manifest/design.md` (and note it for 11.1). Tasks 3.x-6.x assertions follow this outcome.

## Phase 2: App skeleton and decoupling guard (DD121, DD123, DD124)

- [x] 2.1 RED `backend/apps/domain_manifest/tests/test_builder_decoupling.py`: AST scan of `builder/**` + `serialize.py`, one parametrized forbidden-import table (`django`, `apps.generation_runner`, `apps.postman_export`, `apps.uml_*`, any `apps.spring_generator.*` except allowlist exactly `apps.spring_generator.emit.naming`) with a triangulation case proving `apps.spring_generator.emit.context` is rejected; `cli.py` may import only `apps.generation_runner.samples.sample_model`; subprocess import leaves `django`/`jinja2`/`apps.generation_runner` out of `sys.modules`; no other app imports `apps.domain_manifest`; `INSTALLED_APPS` position right after `apps.postman_export`; no host/port/URL literal in app source; no models or migrations.
- [x] 2.2 GREEN create `backend/apps/domain_manifest/__init__.py`, `apps.py`, `builder/__init__.py` (stub `build_manifest`), `tests/__init__.py`; add `apps.domain_manifest` after `apps.postman_export` in `backend/config/settings.py`.

## Phase 3: Type map and attributes (DD125)

- [x] 3.1 RED `backend/apps/domain_manifest/tests/test_attributes.py`: ONE table `ColumnType -> neutral name` (UUID uuid, VARCHAR string, TEXT text, INTEGER integer, BIGINT long, NUMERIC decimal, BOOLEAN boolean, DATE date, TIMESTAMPTZ datetime, ENUM enum) plus unknown member -> `ValueError`; ONE table over the sample columns for `required`, `maxLength` (VARCHAR only), `primaryKey`, `enum`, FK column keeps `Id` suffix, discriminator column excluded, `subtype` tag per 1.1 outcome.
- [x] 3.2 GREEN `backend/apps/domain_manifest/builder/attributes.py` (closed type map, column -> attribute dict, names via `emit.naming`).

## Phase 4: Relationships (DD123, DD125)

- [x] 4.1 RED `backend/apps/domain_manifest/tests/test_relationships.py`: ONE table over sample FK columns (`field`, `attribute`, `column`, `kind`, `target`, `required`); `oneToOne` proven with ONE hand-built table whose unique constraint equals the FK column set; sample expectations for `product_tag` follow 1.1.
- [x] 4.2 GREEN `backend/apps/domain_manifest/builder/relationships.py` (FK index; local 3-line oneToOne rule, not imported from `emit/context`).

## Phase 5: Entities, operations, subtypes (DD125, DD126)

- [x] 5.1 RED in `backend/apps/domain_manifest/tests/test_manifest.py` (part 1): ONE table over all sample tables checking `name`/`table`/`resourcePath`/`discriminatorColumn`/`uniqueConstraints`; operations: 6 fixed CRUD ops in order with method/path/successStatus (201/200/200/204/200/200); empty `operations` AND `resourcePath: null` for inheritance tables (biconditional, DD126); `vehicle` subtypes `Car`/`Truck` sorted; `Customer` scenario (`/api/customers`, `fullName`, one primaryKey).
- [x] 5.2 GREEN `backend/apps/domain_manifest/builder/entities.py` (operations table, subtypes, entity assembly).

## Phase 6: Manifest top level, ordering, exclusions, drift guard (DD125, DD129, DD131)

- [x] 6.1 RED in `backend/apps/domain_manifest/tests/test_manifest.py` (part 2): envelope (`schemaVersion == 1`, `entities`/`enums` lists); enums with `value`/`label` and ordering by name, referenced by attribute `enum`; entities sorted by name, relationships by `field`; one recursive scan with ONE parametrized table of the six excluded keys (searchable, sortable, defaultSort, auditable, readOnly, aliases) absent at any depth; no `generation_metadata`.
- [x] 6.2 GREEN `backend/apps/domain_manifest/builder/manifest.py` and public API `build_manifest` in `backend/apps/domain_manifest/builder/__init__.py`.
- [x] 6.3 Drift guard in `backend/apps/domain_manifest/tests/test_manifest.py` (part 3): resource paths and `operations[].path` from the sample manifest equal the `paths` keys of `backend/apps/postman_export/tests/fixtures/api-docs.json` (read-only), BOTH directions (5 resources, no `vehicles`). Characterization test: a failure is a real drift finding, fix the builder, never the fixture.
- [x] 6.4 Run `docker compose exec -T backend pytest -q apps/domain_manifest/tests/test_manifest.py apps/domain_manifest/tests/test_attributes.py apps/domain_manifest/tests/test_relationships.py`; all green.

## Phase 7: Serialization and determinism (DD127)

- [x] 7.1 RED `backend/apps/domain_manifest/tests/test_determinism.py`: ONE parametrized table over checks: two `build_manifest` calls equal; serialized text byte-identical across two writes; ends with exactly one `\n`; no `\r`; no timestamp/id-like key; re-serializing the parsed file reproduces the bytes.
- [x] 7.2 GREEN `backend/apps/domain_manifest/serialize.py` (duplicated, ~15 lines, `indent=2, sort_keys=True, ensure_ascii=False`, `newline="\n"`; no import of `apps.postman_export`).

## Phase 8: CLI and slice 1 checkpoint (DD124, DD127)

- [x] 8.1 RED `backend/apps/domain_manifest/tests/test_cli.py` (subprocess, `DJANGO_SETTINGS_MODULE`/`POSTGRES_*` stripped; mirror `backend/apps/postman_export/tests/test_cli.py` (read-only)): exit 0 creates the out-dir and writes only `domain-manifest.json`; exit 1 with `error:` on stderr, no traceback and nothing written when `--out-dir` is an existing regular file; exit 2 naming `--out-dir` when missing; `django.setup` trap plus its control; two runs byte-identical.
- [x] 8.2 GREEN `backend/apps/domain_manifest/cli.py` (argparse, no `django.setup()`, builds `sample_model` in-process, catches `OSError` and builder `ValueError`/naming errors -> exit 1).
- [x] 8.3 (DONE: pytest green, 87 tests; slice 1 = 811 authored lines (259 non-test, 552 tests) > ~600 stop threshold; accepted as size:exception by orchestrator decision, tests kept, commit-time split-vs-exception asked later) SLICE 1 GATE: REFACTOR, run `docker compose exec -T backend pytest -q apps/domain_manifest`, green and offline; `git diff --stat` slice 1 must be near ~575 lines (see forecast); do NOT start slice 2 until green.

## Phase 9: Slice 2, compose and gate wiring (DD128, DD130)

- [x] 9.1 `docker-compose.yml`: add `generate-manifest` per design (profile `jvm-verify`, `entrypoint: []`, `user: root`, `./backend:/app:ro` + `generated_project:/generated`, literal command array `python -m apps.domain_manifest.cli --out-dir /generated/project/docs`; NO `depends_on`, NO `rm -rf`, no `env_file`) with a comment.
- [x] 9.2 `scripts/verify-generated-project.sh`: append step 4 `docker compose --profile jvm-verify run --rm generate-manifest` after `generate-postman` with a comment; no new exit code (forwards the CLI's 1 or 2), `EXIT` trap unchanged.
- [x] 9.3 Run `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh`; expect exit 0 and `docs/domain-manifest.json` present in the volume.
- [x] 9.4 Negative check: record `sha1sum docker-compose.yml`, temporarily point the stanza `--out-dir` under the existing regular file `docs/openapi.json`, run the gate; observe CLI exit 1 (`error:` on stderr, no traceback) and a non-zero gate exit; revert; confirm sha1 equals the pre-edit value and `git diff` on `docker-compose.yml` is empty.
- [x] 9.5 Confirm `docker compose config --services` default set is unchanged and `gen-db` is removed afterwards (never `docker compose down`).
- [x] 9.6 Write `openspec/changes/generated-project-domain-manifest/gate-evidence.md`: gate command, exit 0, `BUILD SUCCESSFUL`, statuses 201/200/204/404, `generate-postman` result, `generate-manifest` result with `domain-manifest.json`, negative check exit codes and sha1 equality, default-services result.

## Phase 10: Full suite

- [x] 10.1 Run `docker compose exec -T backend pytest -q` (full backend); green and offline; the 41-file sample oracle unchanged and no manifest file in generated sources.

## Phase 11: Docs

- [x] 11.1 `docs/ai/DECISIONS_LOG.md`: add DD121-DD131 (plus DD132+ from 1.2); DD131 body records the section 33 UML vs own-profile split note.
- [x] 11.2 `docs/ai/CURRENT_STATE.md`: verify each stale line on disk first, then refresh; note delta specs `domain-manifest-export` (new) and `generated-project-verification` (modified) merge at archive.
- [x] 11.3 `docs/ai/HANDOFF_LATEST.md`: verify stale lines on disk, then refresh.
- [x] 11.4 `docs/ai/NEXT_STEPS.md`: verify stale lines on disk, including the postman note that says the next step is the Domain Manifest; replace with the next real step and add the follow-up that the mapper must carry `generation_metadata` before searchable/sortable/defaultSort/auditable/readOnly/aliases can exist.
- [x] 11.5 `docs/ai/sessions/2026-09-20-agent-generated-project-domain-manifest.md`: session note.
