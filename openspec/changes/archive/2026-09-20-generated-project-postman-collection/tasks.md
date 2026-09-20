# Tasks: Generated Project Postman Collection

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~670 authored (code ~350, tests ~260, scripts/compose ~32, settings 1) + docs; captured fixture excluded (generated golden) |
| 400-line budget risk | Medium (project review budget is 800; estimate is inside it) |
| Chained PRs recommended | No |
| Suggested split | Single PR, three revertable units (fixture+export / converter app / gate wiring) |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

Test-scope rule (DD101): pytest sees only `backend/` as `/app`. NO pytest task asserts anything in `scripts/` or `docker-compose.yml`; those are proven by the manual gate, gate-evidence.md and two negative checks. No commit tasks (orchestrator asks the user).

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Smoke export + captured real fixture | PR 1 | `docker compose exec -T backend pytest -q apps/postman_export` (fixture loads) | `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh` (exit 0, `docs/openapi.json` written) | Revert the `boot-smoke.sh` block and fixture |
| 2 | `apps.postman_export` converter + CLI | PR 1 | `docker compose exec -T backend pytest -q apps/postman_export` | N/A: pure offline app, proven by pytest | Remove the app dir and the `INSTALLED_APPS` line |
| 3 | Compose `generate-postman` + third gate step + evidence | PR 1 | N/A (DD101: not reachable from pytest) | `bash scripts/verify-generated-project.sh` plus 2 negative checks | Revert compose stanza and gate line |

## Phase 1: Fixture-first capture (DD108, DD114) - BEFORE any converter assertion

- [x] 1.1 `scripts/boot-smoke.sh`: after the two needle `case` checks and as the LAST statement before `log "PASS"`, add `mkdir -p docs || die 8` and `cp "$BODY" docs/openapi.json || die 8` with a comment (no HTTP call after it; `generate-project` wipes the volume); add header exit-table row `8 OpenAPI export could not be written`.
- [x] 1.2 Run `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh` (still two steps); expect exit 0 and no `die 8`.
- [x] 1.3 Read the exported `/generated/project/docs/openapi.json` (read-only) from the `generated_project` volume (e.g. `docker compose --profile jvm-verify run --rm --no-deps --entrypoint cat generate-project /generated/project/docs/openapi.json`).
- [x] 1.4 Save those bytes unmodified as `backend/apps/postman_export/tests/fixtures/api-docs.json` (trim to the Customer controller only if oversized; state it in 3.5 docstring).
- [x] 1.5 DECISION POINT: inspect the fixture for the `pageable` query-param shape, `Page<T>` response schema names, tag naming and lowest 2xx codes; record the outcome. If it contradicts the design, add DD116+ to `openspec/changes/generated-project-postman-collection/design.md` and `docs/ai/DECISIONS_LOG.md`. Fixture-dependent tasks below (3.4, 3.5, 3.6) follow this decision.

## Phase 2: App skeleton and decoupling guard (DD109)

- [x] 2.1 RED `backend/apps/postman_export/tests/test_converter_decoupling.py`: AST scan of `converter/**` and `cli.py` (no `django`, `apps.spring_generator`, `apps.generation_runner`); subprocess import leaves them out of `sys.modules`; no other app imports `apps.postman_export`; app in `INSTALLED_APPS`; string literals contain no host/port/`http` URL except the Postman schema URL; no `3.1.1` literal in app source.
- [x] 2.2 GREEN create `backend/apps/postman_export/__init__.py`, `apps.py`, `converter/__init__.py` (empty stub) and `tests/__init__.py`; add `apps.postman_export` after `apps.generation_runner` in `backend/config/settings.py`.

## Phase 3: Converter, TDD pairs (DD110-DD112, DD115)

- [x] 3.1 RED `backend/apps/postman_export/tests/test_examples.py`: string, uuid, int, number, boolean, date-time, enum first value, array, object, `$ref`, self-referencing schema terminates (depth guard), deterministic values.
- [x] 3.2 GREEN `backend/apps/postman_export/converter/examples.py`.
- [x] 3.3 RED `backend/apps/postman_export/tests/test_requests.py`: `{id}` becomes `:id` in `url.variable`, raw URL `{{baseUrl}}` + path, `servers` ignored, name `METHOD path` (not `operationId`), JSON body present only with a request body.
- [x] 3.4 GREEN `backend/apps/postman_export/converter/requests.py`, including pageable expansion to `page`/`size`/`sort` per the 1.5 decision.
- [x] 3.5 RED `backend/apps/postman_export/tests/test_collection_from_real_fixture.py` (docstring: springdoc 3.1.1 + capture date, trimming note): envelope (`info.schema`, `info.name` = title, no `auth` anywhere), tag folders and `default`, shuffled-input ordering, one status test per request on the lowest 2xx code, no variable-setting scripts, pageable expanded.
- [x] 3.6 GREEN `backend/apps/postman_export/converter/collection.py` (schema URL kept in exactly one constant; folders sorted by tag, items by (path, method); no ids).
- [x] 3.7 RED `backend/apps/postman_export/tests/test_environment.py`: `baseUrl` present, empty by default, set by value, absent from the collection.
- [x] 3.8 GREEN `backend/apps/postman_export/converter/environment.py`.
- [x] 3.9 RED `backend/apps/postman_export/tests/test_determinism.py`: two conversions equal, serialized files byte-identical, no `_postman_id`, output ends with one `\n` and has no `\r`.
- [x] 3.10 GREEN `backend/apps/postman_export/converter/serialize.py` (`indent=2, sort_keys=True, ensure_ascii=False`, `newline="\n"`) and public API `build_collection`/`build_environment` in `converter/__init__.py`.
- [x] 3.11 RED `backend/apps/postman_export/tests/test_cli.py` (subprocess, `DJANGO_SETTINGS_MODULE`/`POSTGRES_*` stripped): exit 0 writes `postman_collection.json` + `postman_environment.json` (creates out-dir); exit 1 with stderr and no output for missing file, non-JSON, no `paths`, unwritable out-dir; exit 2 without `--openapi`; `--base-url` lands only in the environment file.
- [x] 3.12 GREEN `backend/apps/postman_export/cli.py` (argparse, no `django.setup()`, no traceback).
- [x] 3.13 REFACTOR + run `docker compose exec -T backend pytest -q apps/postman_export`; all green offline.

## Phase 4: Gate wiring and manual proof (DD108, DD113)

- [x] 4.1 `docker-compose.yml`: add `generate-postman` per design (profile `jvm-verify`, `entrypoint: []`, `user: root`, `./backend:/app:ro`, `generated_project:/generated`, literal command array; NO `depends_on`, NO `rm -rf`, no `env_file`).
- [x] 4.2 `scripts/verify-generated-project.sh`: add third step `run --rm generate-postman` with a comment; `cleanup`/`EXIT` trap unchanged.
- [x] 4.3 Run `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh`; expect exit 0 and both files present in the volume.
- [x] 4.4 Negative check A: point the export path at an unwritable location in `scripts/boot-smoke.sh`, run the gate, observe exit 8 without PASS; revert byte-identically (`git diff` empty).
- [x] 4.5 Negative check B: corrupt the exported `docs/openapi.json` in the volume, run `docker compose --profile jvm-verify run --rm generate-postman`; observe exit 1 and a non-zero gate.
- [x] 4.6 Confirm `docker compose config --services` default set is unchanged and gen-db is removed afterwards.
- [x] 4.7 Write `openspec/changes/generated-project-postman-collection/gate-evidence.md`: command, exit 0, `BUILD SUCCESSFUL`, statuses 201/200/204/404, export evidence, `generate-postman` result and file names, negative exits (8, 1), fixture provenance (springdoc 3.1.1 + date), optional Postman import result.

## Phase 5: Full suite

- [x] 5.1 Run `docker compose exec -T backend pytest -q` (full backend); green and offline; generated sources unchanged.

## Phase 6: Docs

- [x] 6.1 `docs/ai/DECISIONS_LOG.md`: add DD108-DD115 (plus DD116+ if 1.5 produced any).
- [x] 6.2 `docs/ai/CURRENT_STATE.md`, `docs/ai/HANDOFF_LATEST.md`, `docs/ai/NEXT_STEPS.md`: refresh; note that delta specs `postman-collection-export` (new) and `generated-project-verification` (modified) merge at archive.
- [x] 6.3 `docs/ai/sessions/2026-09-20-agent-generated-project-postman-collection.md`: session note.
