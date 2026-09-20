# Gate Evidence: Generated Project Postman Collection

Recorded 2026-09-20 on Windows + Git Bash (Docker Desktop). Nothing here is asserted by pytest (DD101): `scripts/` and `docker-compose.yml` are unreachable from the test process, so these runs are the proof.

## Fixture provenance (DD114)

- Captured by the FIRST gate run after the DD108 export was added (`docs/openapi.json` inside the `generated_project` volume), read back with `docker compose --profile jvm-verify run --rm --no-deps -T --entrypoint cat generate-project /generated/project/docs/openapi.json`.
- Stored byte-identical as `backend/apps/postman_export/tests/fixtures/api-docs.json` (14408 bytes, springdoc 3.1.1, OpenAPI 3.1.0, 2026-09-20). Not trimmed: it holds all five sample controllers.
- Later gate runs export the same 14408 bytes (`ls -l` in the volume), so the fixture matches the live document.

## Positive gate (three steps)

Command: `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh`

| Check | Observed |
|---|---|
| Exit code | 0 |
| Compile | `BUILD SUCCESSFUL in 42s` |
| CRUD statuses | `POST /api/customers -> 201`, `GET /api/customers/{id} -> 200`, `DELETE ... -> 204`, `GET ... -> 404` |
| OpenAPI | `GET /v3/api-docs -> 200`, `boot-smoke: PASS` |
| Export | `docs/openapi.json` (14408 B) written by the smoke, last statement before `PASS` |
| generate-postman | `wrote postman_collection.json and postman_environment.json to /generated/project/docs` |
| Files in volume | `openapi.json` 14408 B, `postman_collection.json` 33039 B, `postman_environment.json` 187 B |
| Environment file | single variable `baseUrl`, empty value, `enabled: true` |

## Negative checks (both reverted byte-identically)

| # | Mutation | Observed | Revert proof |
|---|---|---|---|
| A | In `scripts/boot-smoke.sh`, the export `cp` target was pointed at `/proc/nope/openapi.json` | gate exit 8, `boot-smoke: FAIL: could not write docs/openapi.json`, no `PASS` | `sha1sum scripts/boot-smoke.sh` equals the pre-mutation copy (`cdd3d3c3...`); `git diff` shows only the intended export block |
| B1 | Volume `docs/openapi.json` overwritten with `{corrupt`, then `docker compose --profile jvm-verify run --rm generate-postman` | converter exit 1, stderr `error: ... is not valid JSON: ...`, no traceback | n/a (volume content only) |
| B2 | Full gate with the smoke export replaced by `echo "{corrupt" > docs/openapi.json` | smoke printed `PASS`, third step printed the same `not valid JSON` error, gate exit 1 | `sha1sum` equals the pre-mutation copy (`cdd3d3c3...`) |

After the negatives, one more unmodified gate run was green (exit 0, `BUILD SUCCESSFUL in 42s`, 201/200/204/404, `PASS`, both Postman files written).

## Housekeeping

- `docker compose config --services` (default profile) is unchanged: `backend db frontend mailpit redis`. `generate-postman` is only in the `jvm-verify` profile.
- `docker compose ps -a` after the runs shows no `gen-db`; db/redis/backend/frontend/mailpit stayed up (`down` is never used).
- `generate-postman` has no `depends_on`, no `rm -rf`, no `env_file`, and a literal command array.

## Not run

- Importing `postman_collection.json` into the Postman application: not available in this environment. The shape follows Postman Collection v2.1.0 (`info.schema` URL, `item` folders, `event` test scripts).
