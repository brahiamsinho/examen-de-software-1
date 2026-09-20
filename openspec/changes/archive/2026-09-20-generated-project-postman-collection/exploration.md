# Exploration: generated-project-postman-collection

Spec `product-04-next-django.md` §37 item 15. Engram: `sdd/generated-project-postman-collection/explore` (obs 708).

## Current State

- The spec gives almost no Postman detail. §25 says the flow is generated backend -> OpenAPI -> Postman Collection and that the generated "colección de pruebas" MUST be a Postman Collection. §22 lists springdoc-openapi (it wins over §25's Django Ninja wording per DECISIONS_LOG 2026-09-19). Nothing fixes the format version, folders, `baseUrl`, auth, examples or an environment file.
- Generated backend (`Controller.java.j2`): each entity is mounted at `/api/<plural>` with POST (201), GET /{id}, PUT /{id}, DELETE /{id} (204), GET (`Page<Dto>` via `Pageable`) and GET /count. No Spring Security, so no auth. The sample model has 7 entities, about 40 operations.
- `scripts/boot-smoke.sh` block 9 fetches `/v3/api-docs` into `$BODY` as its last call (`${TMPDIR:-/tmp}/boot-smoke-body.txt`, overwritten by every call). Working dir is `/generated/project`. `generate-project` runs `rm -rf /generated/project` on each run, so a file written inside it is wiped on regeneration.
- `verify-generated-project.sh` order: resolve GRADLE_IMAGE via `generate-project`, `jvm-verify`, `jvm-boot-smoke`.
- Established pattern to run Python against the volume: the `generate-project` service (`build: ./backend`, `entrypoint: []`, `./backend:/app:ro`, `generated_project:/generated`, no DB or .env).
- `generation_runner` has a plain `__main__` CLI (exit 0/1/2, no django.setup), pure `writer/` and `domain/` guarded by `test_writer_decoupling.py`.
- The real springdoc document shape is UNOBSERVED: the archived gate-evidence only checked the needles `"openapi":` and `"/api/customers"`. Pageable/`Page<T>` expectations are assumptions until the first real capture.

## Q2. Capturing a static openapi.json

| Option | Pros | Cons | Effort |
|---|---|---|---|
| (a) Smoke copies `$BODY` to a relative file in the working dir | ~4 lines of bash, reuses the single call against the real running app, no plugin or version coupling, wiped on regeneration (no stale file) | Smoke also becomes an exporter; verifiable only by the manual gate | Low |
| (b) springdoc Gradle plugin | Plain Gradle task | New plugin + version in generated `build.gradle` (versions.py, DD72), boots the app at build time (needs DB), unproven on Gradle 9.7 / Boot 4.1.1, dev tool in the deliverable | Med-High |
| (c) Derive from relational model | Offline | Already rejected (bypasses springdoc) | - |

Recommendation: (a). Export after the needle checks and before `log "PASS"` with `cp "$BODY" <relative path> || die 8` (plus `mkdir -p`), before any later `_http` call. Existing assertions untouched; the only new failure mode is an unwritable path (exit 8).

Testing: the export is proven by the manual gate plus gate-evidence (DD101/DD105 convention); the converter by pytest against a REAL captured fixture; a third gate step runs the converter on the live export so springdoc shape drift fails the gate.

## Q3. OpenAPI -> Postman

| Option | Pros | Cons |
|---|---|---|
| Pure Python converter (stdlib `json`, Collection v2.1.0) | Deterministic (own ids/ordering, no `_postman_id`, sorted items), offline pytest, zero new deps, runs in the existing backend image, full control of naming/`{{baseUrl}}`/Pageable, reusable by the Domain Manifest | Owns a small OpenAPI-subset mapping (~150-200 lines) |
| `openapi-to-postmanv2` (Node container) | Battle-tested | New Node image, runtime npm install (network flake), pin outside versions.py, random ids, not offline-testable |

Recommendation: pure Python converter.

Design notes:
- Ignore `servers` (springdoc fills it from the request host). URLs are `{{baseUrl}}` + path; `{id}` becomes `:id`.
- Folder = first operation tag (default `customer-controller`), fallback `default`. Request name = `METHOD path` (not `operationId`, which collides across controllers).
- Sort folders and items by (path, method) for determinism.
- Body examples generated from the request schema: resolve `$ref`; string/uuid/int/number/boolean/date-time/enum/array/object; depth guard for cycles.
- Pageable expected as one `pageable` query param with an object schema; expand into `page`/`size`/`sort` (confirm on the real fixture).
- No `auth` block. ProblemDetail is not documented and is irrelevant for requests, so no Java tuning and no conflict with "no Java config".
- Output: `<name>.postman_collection.json` (schema `https://schema.getpostman.com/json/collection/v2.1.0/collection.json`, `info.name` from OpenAPI `info.title`) and `<name>.postman_environment.json` with `baseUrl`, value from an optional `--base-url` (default empty; never a literal in code, AGENTS.md rule 4).

## Q4. Where the code lives

Recommendation: new app `apps.postman_export` (pure `converter/` + plain `__main__` CLI: `python -m apps.postman_export.cli --openapi <file> --out-dir <dir> [--base-url ...]`). Matches the one-app-per-domain preference, natural sibling of the Domain Manifest, no generator coupling (DD75-style guard). Alternative (inside `generation_runner`) mixes pipeline running with OpenAPI derivation. Compose gets a `generate-postman` service (profile `jvm-verify`, same stanza as `generate-project`, literal `command` array) run as the third step of `verify-generated-project.sh`.

## Recommended split (800-line budget)

1. `apps.postman_export`: converter + CLI + tests driven by a fixture. First apply task: run the gate once with the export to capture the REAL `/v3/api-docs` body and commit it as the fixture (trim to the Customer controller if too large, say so in the test docstring).
2. Gate wiring: smoke export (exit 8), compose service, third gate step, gate-evidence, docs/ai.

Estimated ~550 lines excluding docs (converter ~180, CLI ~60, tests ~250, compose/scripts ~40).

## Risks

- Real springdoc shape unobserved (Pageable, `Page<T>` names, Boot 4.1.0 vs 4.1.1 gap): capture the fixture first.
- Committed fixture can go stale after a springdoc bump; only the manual gate catches it. Record provenance (springdoc 3.1.1, date).
- Reusing `$BODY` is fragile: copy must precede later `_http` calls.
- Path order and `servers` host are environment-dependent: sort and ignore `servers`.
- §25's "colección de pruebas" may imply assertions.
- Windows/Git Bash needs `MSYS_NO_PATHCONV=1`; the compose command stays a literal array.

## Decisions

1. "Colección de pruebas" and assertions. Default adopted (no user answer needed unless they disagree): requests + generated body examples + one status-code test per request derived from the documented 2xx code, with NO id chaining. A runnable end-to-end collection (chained ids, newman-ready) is a separate follow-up.
2. Technical defaults: `baseUrl` via environment file with empty default, no auth, folder-per-tag, request names `METHOD path`.
