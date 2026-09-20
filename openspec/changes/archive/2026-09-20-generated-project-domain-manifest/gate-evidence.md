# Gate Evidence: Generated Project Domain Manifest

Recorded 2026-09-20 during apply. Not reachable from pytest (DD101/DD120).

## Positive run

Command: `MSYS_NO_PATHCONV=1 bash scripts/verify-generated-project.sh`

- Exit code: 0.
- Step 1 `jvm-verify`: `BUILD SUCCESSFUL in 46s`.
- Step 2 `jvm-boot-smoke`: POST /api/customers -> 201, GET by id -> 200, DELETE -> 204, GET again -> 404, GET /v3/api-docs -> 200.
- Step 3 `generate-postman`: `wrote postman_collection.json and postman_environment.json to /generated/project/docs`.
- Step 4 `generate-manifest`: `wrote domain-manifest.json to /generated/project/docs`.
- Volume `generated_project`, `docs/` holds: `domain-manifest.json`, `openapi.json`, `postman_collection.json`, `postman_environment.json`.
- Read-back of `docs/domain-manifest.json`: 12496 bytes, `schemaVersion` 1, 6 entities, 1 enum (`PurchaseStatus`), 5 resource paths (`/api/customers`, `/api/product-tags`, `/api/products`, `/api/purchases`, `/api/tags`), `Vehicle` has `resourcePath: null` and empty `operations`.

## Negative check

- Before: `sha1sum docker-compose.yml` = `617d3ead113fde6b490dff0fc73c0d967e53b578` (taken after the stanza was added).
- Temporary edit: stanza `--out-dir` set to `/generated/project/docs/openapi.json/x` (under the existing regular file).
- Observed: steps 1-3 passed, step 4 printed `error: [Errno 20] Not a directory: '/generated/project/docs/openapi.json/x'` (no traceback); gate exit code 1 (the CLI exit code forwarded, no new exit code).
- Revert: `sha1sum docker-compose.yml` = `617d3ead113fde6b490dff0fc73c0d967e53b578` (equal); `git diff docker-compose.yml` hash equal to the pre-edit hash (the diff is the 17-line `generate-manifest` stanza, not empty because the stanza is this change).
- Note: a first attempt with an unavailable `sd` binary did not modify the file and the gate then ran as a second positive run (exit 0); it is not counted as the negative check.

## Default services

- `docker compose config --services` (no profile): `mailpit redis db backend frontend` (unchanged; `generate-manifest` has profile `jvm-verify`).
- With `--profile jvm-verify`: adds `gen-db generate-manifest generate-postman jvm-boot-smoke generate-project jvm-verify`.
- `gen-db` container: absent after the gate (removed by the EXIT trap; `docker compose down` never used).

## Full suite

`docker compose exec -T backend pytest -q`: 987 passed (900 baseline + 87 new), offline.
