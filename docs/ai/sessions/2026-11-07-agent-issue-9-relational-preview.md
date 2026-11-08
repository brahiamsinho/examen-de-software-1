# Issue #9 session: relational preview and SQL

## Delivered

- Added a read-only relational preview endpoint under the existing relational-mapping router.
- Reused `map_to_relational` as the only UML-to-relational conversion path.
- Added pure projection and deterministic PostgreSQL DDL serialization.
- Added the Generation-tab panel to inspect tables, columns, PK/FK metadata and SQL, with copy and exact-string `.sql` download.
- Added backend API/pure serialization and frontend client/component tests.

## Read-only guarantee

The endpoint is a `GET`: membership resolution, document load and pure in-memory mapping only. It does not call document commands, persistence, the Spring archive generator, or a database SQL client. DDL is returned as text and never executed.

## Verification

- `docker compose exec -T backend pytest apps/relational_mapping/tests/test_preview.py apps/relational_mapping/tests/test_api.py --reuse-db -q`: 9 passed.
- `docker compose exec -T backend pytest apps/relational_mapping --reuse-db -q`: 192 passed.
- `docker compose exec -T backend python -m compileall -q apps/relational_mapping`: passed.
- `git diff --check`: passed.
- Frontend Vitest, TypeScript and lint: pending. Host dependencies were unavailable; Compose frontend test containers hung while Docker created them, before Node executed.

## Follow-up

Run frontend checks and a browser smoke before commit. Do not execute generated preview SQL against PostgreSQL.
