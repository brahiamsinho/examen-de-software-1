# Proposal: Generated Project Postman Collection

## Intent

§37 item 15 (and §25's flow: generated backend -> OpenAPI -> Postman Collection). The generated Spring backend now serves `/v3/api-docs`, but that document dies with the container: nothing captures it and nothing turns it into the deliverable test collection. A grader cannot exercise the ~40 generated CRUD operations without hand-writing requests. This slice captures the real document and converts it, deterministically and offline.

## Scope

### In Scope

- `scripts/boot-smoke.sh`: after the existing needle checks and before PASS, copy the already-fetched `$BODY` to a relative static file (`mkdir -p` parent, `cp ... || die 8`). No new HTTP call.
- New Django app `apps.postman_export`: pure `converter/` plus a plain `__main__` CLI (`--openapi`, `--out-dir`, `--base-url`), registered in INSTALLED_APPS, with a decoupling guard mirroring `generation_runner`.
- Output: Postman Collection **v2.1.0** plus an environment file exposing `baseUrl` (value from optional `--base-url`, default empty — never a literal in code).
- Mapping: folder = first operation tag, request name `METHOD path`, items sorted by (path, method), `{id}` -> `:id`, `servers` ignored, `Pageable` expanded into `page`/`size`/`sort`, body examples generated from the request schema.
- Assertions (stated assumption for "colección de pruebas"): one status-code test per request, derived from the documented 2xx code. No id chaining, no `auth` block.
- Compose service `generate-postman` (profile `jvm-verify`, same stanza as `generate-project`, literal command array) as the third step of `scripts/verify-generated-project.sh`, so springdoc shape drift fails the gate.
- TDD fixture: first apply task runs the gate to capture the REAL `/v3/api-docs` body and commits it (trimmed to the Customer controller if oversized, provenance recorded: springdoc 3.1.1 + date).

### Out of Scope

- Domain Manifest (§37 item 16), auth, Swagger UI, Java config or ProblemDetail documentation, Gradle wrapper/plugin, frontend/mobile.
- A runnable chained end-to-end / newman collection (id chaining) — explicit follow-up.
- Deriving the document from the relational model (already rejected: bypasses springdoc).

## Capabilities

### New Capabilities

- `postman-collection-export`: converting a captured OpenAPI document into a deterministic Postman v2.1.0 collection plus environment file, and the CLI contract that drives it.

### Modified Capabilities

- `generated-project-verification`: `Boot Smoke Execution` (smoke also exports the document, new exit 8), `Compose Chain Contract` (`generate-postman`), `Single Gate Command` (third step), `Manual Gate Evidence`, and `Boot Change Isolation` wording.

## Approach

Capture, then convert, both on the path already proven. The smoke owns capture because it is the only place holding a real response from a really-booted app; it costs ~4 lines and is wiped by the next `generate-project` run, so no stale artifact survives. Conversion is stdlib Python in its own app — deterministic (own ids, sorted items, no `_postman_id`), unit-testable offline against the committed real fixture, and reusable by the Domain Manifest. The gate runs the converter against the live export so a springdoc shape change fails loudly instead of silently producing a wrong collection.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/postman_export/` | New | Converter, CLI, decoupling guard, tests |
| `backend/config/settings*` | Modified | INSTALLED_APPS entry |
| `scripts/boot-smoke.sh` | Modified | Static export, exit 8 |
| `scripts/verify-generated-project.sh`, `docker-compose*.yml` | Modified | `generate-postman` third step |
| `openspec/specs/generated-project-verification/` | Modified | Delta |
| `docs/ai/` (gate evidence, CURRENT_STATE, DECISIONS_LOG) | Modified | DD101/DD105 convention |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Real springdoc shape unobserved (Pageable, `Page<T>`) | High | Capture the real fixture as task 1; write tests against it, not assumptions |
| Committed fixture goes stale after a springdoc bump | Medium | Gate step 3 runs the converter live; record fixture provenance |
| `$BODY` overwritten by a later `_http` call | Medium | Copy placed after needle checks, before PASS; contract test pins the order |
| "Colección de pruebas" implies more than status-code tests | Medium | Stated assumption; chained collection is a named follow-up |
| Windows/Git Bash path mangling | Low | `MSYS_NO_PATHCONV=1`, literal compose command array |

## Rollback Plan

Two independent reverts. Revert slice B (smoke export lines, compose service, gate step) and the gate returns to compile + verify + smoke unchanged. Revert slice A and `apps.postman_export` disappears with its INSTALLED_APPS entry; no other app imports it (decoupling guard enforces this), and the generated project is untouched either way.

## Dependencies

- Docker plus network for the manual gate (fixture capture and gate step 3).
- The already-shipped springdoc `/v3/api-docs` endpoint (archived change `generated-project-openapi-springdoc`).

## Success Criteria

- [ ] Gate recorded: smoke writes the static OpenAPI file; `generate-postman` produces collection + environment from it.
- [ ] Collection imports into Postman and lists the generated CRUD operations under tag folders.
- [ ] Converter output is byte-identical across two runs on the same input.
- [ ] `baseUrl` appears only in the environment file; no host, port or URL literal in source.
- [ ] `pytest -q` stays green, Docker-free and offline, driven by the committed real fixture.
