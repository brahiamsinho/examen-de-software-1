# Design: Generated Project Postman Collection

## Technical Approach

Two halves on the path already proven by `generated-project-boot-smoke`. **Capture**: `scripts/boot-smoke.sh` copies the `/v3/api-docs` body it already holds in `$BODY` to a relative file inside the generated project. **Convert**: a new Django app `apps.postman_export` — a pure stdlib `converter/` package behind a plain `__main__` CLI — turns that document into a Postman Collection v2.1.0 plus an environment file, run as a third `verify-generated-project.sh` step so springdoc shape drift fails the gate. Offline pytest drives the converter against a REAL captured fixture; the gate proves the wiring pytest cannot reach.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| **DD108** | Smoke exports `$BODY` to the **relative** path `docs/openapi.json` (working dir `/generated/project`), after the two needle `case` checks and before `log "PASS"`; `mkdir -p docs \|\| die 8` then `cp "$BODY" docs/openapi.json \|\| die 8`. | springdoc Gradle plugin (new plugin+version in the deliverable, boots at build time, unproven on Gradle 9.7/Boot 4.1.1); a second `_http` call (extra network call, DD99). | Reuses the single real response from a really-booted app; ~4 lines; no container path hardcoded in the script (DD84 style). `generate-project` runs `rm -rf /generated/project`, so the export cannot go stale. |
| **DD109** | New app `apps.postman_export`: pure `converter/` + glue (`cli.py`, `apps.py`), registered in `INSTALLED_APPS` after `apps.generation_runner`. No models, no migrations. | Folding it into `apps.generation_runner` (mixes pipeline running with OpenAPI derivation). | One app per domain; natural sibling for the future Domain Manifest; mirrors the `generation_runner` shell exactly. |
| **DD110** | Converter is pure stdlib Python (`json`, `argparse`). | `openapi-to-postmanv2` Node container (new image, runtime npm install, random ids, not offline-testable). | Deterministic, zero new deps, runs in the existing backend image, offline pytest. |
| **DD111** | Fixed output filenames in `--out-dir`: `postman_collection.json` and `postman_environment.json`. `info.name` comes from OpenAPI `info.title`. | Filenames slugified from `info.title` — the gate and the compose command would have to guess the name springdoc chose. | The gate needs a literal path; the human-facing name still tracks the document. |
| **DD112** | Determinism recipe: items sorted by `(path, method)`, folders sorted by tag name; **no** `_postman_id`, no per-item/script `id`, no timestamps, no `uuid4`; serialized with `json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"` written through `open(path, "w", encoding="utf-8", newline="\n")`. | Postman-style generated ids (defeat byte-identity); default `write_text` (CRLF on a Windows dev host). | Two runs on the same input must be byte-identical (success criterion), on Linux container and Windows host alike. |
| **DD113** | Compose service `generate-postman` copies the `generate-project` stanza **without `depends_on` and without the `rm -rf`**; literal absolute command array. | `depends_on: generate-project` (would re-run the generator and **wipe the export** the smoke just wrote). | The wipe is the whole reason ordering is explicit; `verify-generated-project.sh` already sequences steps rather than chaining `depends_on` (DD94). |
| **DD114** | Fixture-first TDD: the FIRST apply task runs the gate with the DD108 export and commits the captured real body as `tests/fixtures/api-docs.json` **before any converter assertion is written**. Mapping details the fixture could contradict (`pageable` query-param shape, `Page<T>` response schema names, springdoc tag naming) are marked **fixture-dependent** and decided at apply against the committed bytes. | Writing converter tests from the exploration's assumed shape and repairing later (the real springdoc document is UNOBSERVED beyond two needles, per gate-evidence). | Prevents freezing a mapping the real document contradicts — the Jinja `StrictUndefined` lesson: assert only what was observed. |
| **DD115** | Assertions: exactly one status-code test per request, derived from the documented 2xx response code. No id chaining, no `auth` block. | A runnable chained end-to-end/newman collection. | Satisfies §25's "colección de pruebas" with a stated assumption; chaining is a named follow-up. |

**Verified by reading** (not assumed): `$BODY` holds the api-docs body at the export point (block 9 `assert_status 200 GET /v3/api-docs` is the last `_http` call; the needles only read it); `generate-project` has no `depends_on`; the gate's `EXIT` trap removes only `gen-db`; exit codes 2–7 are taken; `INSTALLED_APPS` lists `apps.generation_runner` at index 4 of the local block. **Unverified**: the real springdoc JSON shape (DD114 exists precisely for this).

## Data Flow

    generate-project ──(wipes+writes)──▶ generated_project volume
    jvm-verify        ──gradle build───▶ build/libs/*.jar
    jvm-boot-smoke    ──GET /v3/api-docs──▶ $BODY ──cp──▶ /generated/project/docs/openapi.json
    generate-postman  ──python -m apps.postman_export.cli──▶ docs/postman_collection.json
                                                            docs/postman_environment.json

## File Changes

| File | Action | Size est. |
|---|---|---|
| `backend/apps/postman_export/__init__.py`, `apps.py` | Create | ~15 |
| `converter/__init__.py` (public API: `build_collection`, `build_environment`) | Create | ~12 |
| `converter/examples.py` (schema → example: `$ref` resolve, string/uuid/int/number/boolean/date-time/enum/array/object, depth guard for cycles) | Create | ~70 |
| `converter/requests.py` (path split, `{id}` → `:id` + `variable[]`, query params, headers, body) | Create | ~80 |
| `converter/collection.py` (tag folders, `METHOD path` names, `(path, method)` ordering, test scripts) | Create | ~90 |
| `converter/environment.py`, `converter/serialize.py` | Create | ~45 |
| `cli.py` (`--openapi --out-dir [--base-url]`, exit 0/1/2, no `django.setup()`) | Create | ~55 |
| `tests/` (7 modules, below) | Create | ~260 |
| `tests/fixtures/api-docs.json` | Create (captured golden, trimmed to the Customer controller if oversized; provenance springdoc 3.1.1 + capture date in the consuming test docstring) | excluded from authored count |
| `backend/config/settings.py` | Modify | +1 |
| `scripts/boot-smoke.sh` | Modify (export block, `die 8`, header exit table gains `8 OpenAPI export could not be written`) | ~8 |
| `scripts/verify-generated-project.sh` | Modify (third `run --rm generate-postman` line + comment; `cleanup`/`EXIT` trap unchanged — still `rm -sfv gen-db` only) | ~4 |
| `docker-compose.yml` | Modify (`generate-postman` stanza) | ~20 |
| `docs/ai/` (gate-evidence, CURRENT_STATE, HANDOFF_LATEST, NEXT_STEPS, DECISIONS_LOG DD108–DD115) | Modify | docs |

**Authored total ≈ 670 lines** — inside the 800-line single-PR budget with the fixture excluded as a generated golden.

## Interfaces / Contracts

```yaml
# docker-compose.yml — literal command array (DD83/DD84), no depends_on (DD113)
generate-postman:
  build: { context: ./backend, target: dev }
  profiles: [jvm-verify]
  entrypoint: []
  user: root
  volumes:
    - ./backend:/app:ro
    - generated_project:/generated
  command: ["python", "-m", "apps.postman_export.cli",
            "--openapi", "/generated/project/docs/openapi.json",
            "--out-dir", "/generated/project/docs"]
```

Per-request test script (no `id`, `exec` is a line array):

```json
{"listen": "test", "script": {"type": "text/javascript", "exec": [
  "pm.test(\"status is 201\", function () {", "    pm.response.to.have.status(201);", "});"]}}
```

`baseUrl` exists only in `postman_environment.json` (`{"key":"baseUrl","value":"","enabled":true}`); `--base-url` defaults to the empty string, so no host/port/URL literal enters source (AGENTS.md rule 4). Request URLs are `{{baseUrl}}` + path; `servers` is ignored.

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit | example generation per schema type, `$ref`, cycles | `test_examples.py` |
| Unit | `{id}` → `:id`, query params, body presence | `test_requests.py` |
| Integration (offline) | folders, names, ordering, status tests over the REAL fixture | `test_collection_from_real_fixture.py` |
| Determinism | two conversions of the same input are byte-identical; output contains no `_postman_id` | `test_determinism.py` |
| Env file | `baseUrl` present, empty by default, set by `--base-url` | `test_environment.py` |
| CLI | exit 0/1/2, files written, no `django.setup()` (subprocess with `DJANGO_SETTINGS_MODULE`/`POSTGRES_*` stripped, mirroring `generation_runner/tests/test_cli.py`) | `test_cli.py` |
| Decoupling guard | `converter/**` never imports `apps.spring_generator`, `apps.generation_runner` or `django`; importing `apps.postman_export.converter` in a subprocess leaves them out of `sys.modules` | `test_converter_decoupling.py`, AST scan modelled on `test_writer_decoupling.py` |
| Manual gate | export is written, `generate-postman` converts it, collection imports into Postman | `bash scripts/verify-generated-project.sh` + gate-evidence (DD101/DD105 convention) |

**What pytest cannot prove (DD101)**: the backend container mounts only `backend/` as `/app`, so `scripts/` and `docker-compose.yml` are unreachable from tests. pytest therefore cannot pin the `docs/openapi.json` literal, the `die 8` placement, the ordering of the copy relative to later `_http` calls, or the compose stanza. The proposal's "contract test pins the order" mitigation is **not achievable** and is replaced by: the copy is the last statement before `log "PASS"` with an explanatory comment, and the gate run recorded in gate-evidence is the proof. Everything else the gate proves: a really-booted springdoc document, real conversion, and shape-drift detection.

**Failure modes / exit codes**

| Where | Condition | Code |
|---|---|---|
| smoke | export path unwritable | `8` (new) |
| CLI | missing/unreadable/invalid JSON, unwritable out-dir | `1` (message on stderr, no traceback) |
| CLI | usage error | `2` (argparse) |
| gate | any step non-zero | `set -e` stops before the next step |

## Threat Matrix

Shell/subprocess boundary is touched, so the matrix is recorded; the reference's rows are VCS/PR-specific.

| Boundary | Applicability | Response |
|---|---|---|
| Documentation-like paths | N/A — no file is classified or executed by content; `docs/openapi.json` is read as data. |
| Git repository selection | N/A — no `git` invocation. |
| Commit state | N/A — no index/worktree operation. |
| Push state | N/A — nothing is pushed. |
| PR commands | N/A — no PR automation. |
| **Shell/compose argument composition** (project-specific row) | Applicable | Literal `command` arrays only (no `sh -c`, no `eval`), absolute container paths confined to `docker-compose.yml`, `MSYS_NO_PATHCONV=1` already exported by the gate script; `$BODY` is quoted. Proven by the gate, not pytest. |

## Migration / Rollout

No migration; no models, no Django schema impact. The new app is inert until its CLI is invoked.

## Rollback

Two independent reverts, in either order. Revert the gate slice (smoke export + `die 8` + header row, `generate-postman` stanza, third gate step) → the gate returns to compile + verify + smoke, byte-unchanged. Revert the app slice → `apps.postman_export` and its `INSTALLED_APPS` line disappear; nothing imports it (guard enforces this). The generated project is untouched either way; the exported files live only inside the named volume and are wiped by the next `generate-project`.

## Open Questions

- [ ] **Decision point at apply (DD114)**: `pageable` query-param shape and `Page<T>` response naming — resolve against the committed fixture, not before.
- [ ] Fixture size: trim to the Customer controller only if the full document is unwieldy; decide when the real bytes exist.

## Apply-time Decisions (DD114 decision point, task 1.5)

Recorded after inspecting the REAL captured document (`backend/apps/postman_export/tests/fixtures/api-docs.json`, 14408 bytes, springdoc 3.1.1, OpenAPI 3.1.0, captured 2026-09-20 from the gate's `/v3/api-docs` response, stored byte-identical, NOT trimmed: it is not oversized and holds all five sample controllers, not only Customer).

Observed shape: `servers` = one entry with a loopback host (ignored, per design); `info.title` = `OpenAPI definition`; tags are per-controller and every operation has exactly one (`customer-controller`, `tag-controller`, `purchase-controller`, `product-controller`, `product-tag-controller`; no untagged operation); `operationId` values carry numeric suffixes (`findById_4`), confirming names must be `METHOD path`; request bodies use `application/json` and reference `*RequestDto`; responses use the `*/*` media type; documented 2xx codes are 200 (GET/PUT), 201 (POST), 204 (DELETE); `GET /api/{resource}/count` exists next to `/{id}` (sort order `/api/x` < `/api/x/count` < `/api/x/{id}`).

| # | Decision | Rationale |
|---|---|---|
| **DD116** | The `pageable` query parameter is `{"name":"pageable","in":"query","required":true,"schema":{"$ref":"#/components/schemas/Pageable"}}`: the schema is a `$ref` (not inline), so the expansion MUST resolve `$ref` first. `Pageable` is an object with `page` (int32, minimum 0), `size` (int32, minimum 1) and `sort` (array of string). The parameter is expanded into query params named after the resolved schema properties, sorted by name (`page`, `size`, `sort`); `page` = `0`, `size` = `20` (one named constant, the Spring Data default page size), `sort` = empty and `disabled` (optional). The `pageable` param itself is dropped. | Resolves the fixture-dependent item of the spec; contradicts only the design's assumption of an inline object schema, not its mapping. |
| **DD117** | `Page<T>` responses are flat named schemas (`PageCustomerResponseDto`, ...) with no generics and no relevance to request generation; the converter never inspects response bodies, only the documented response codes. | Nothing to map; keeps the converter small. |
| **DD118** | Fixture kept whole (5 controllers) instead of trimmed to Customer; provenance recorded in the consuming test docstring. | 14 KB is not oversized, and trimming would have hidden real ordering/tag behaviour. |

| # | Decision | Rationale |
|---|---|---|
| **DD119** | An operation that documents no numeric 2xx response code (only `default` or 4xx/5xx) gets NO test event: the converter never invents a status. Wildcard codes such as `2XX` are not numeric and are ignored the same way. The sample document never hits this branch; a synthetic test pins it. | The status test is derived from the document (DD115); nothing to derive means nothing to assert. |
| **DD120** | `pytest` proves the converter and CLI only. The DD108 export, `die 8`, the compose stanza and the third gate step are proven by `gate-evidence.md` and the two negative checks (exit 8 on an unwritable export path, exit 1 on a corrupted export), each reverted byte-identically (sha1 equal). | DD101 (`scripts/` and compose are unreachable from pytest). |
