# Session: generated-project-postman-collection apply (2026-09-20)

Agent: Claude (sdd-apply executor). Strict TDD. Change: `generated-project-postman-collection` (§37 item 15).

## What was built

- `scripts/boot-smoke.sh`: exports the real `/v3/api-docs` body to `docs/openapi.json` as the last statement before `PASS` (exit 8 on failure).
- `backend/apps/postman_export/`: pure stdlib `converter/` (`examples`, `requests`, `collection`, `environment`, `serialize`), plain `__main__` `cli.py` (exit 0/1/2), 60 tests, real fixture `tests/fixtures/api-docs.json`.
- `docker-compose.yml`: `generate-postman` (profile `jvm-verify`, no `depends_on`, no `rm -rf`).
- `scripts/verify-generated-project.sh`: third step `run --rm generate-postman`.
- `backend/config/settings.py`: `apps.postman_export` in `INSTALLED_APPS`.

## Order of work (DD114 fixture-first)

1. Export block added, gate run green, real body captured and committed-ready as the fixture.
2. Fixture inspected: `pageable` is a `$ref` schema, tags are per controller, 2xx codes 200/201/204, `servers` has a loopback host. DD116-DD118 recorded in `design.md`.
3. RED/GREEN pairs for decoupling guard, examples, requests, collection (from the real fixture), environment, determinism, CLI.
4. Compose stanza + gate step, gate green x3, negative A (exit 8) and B (exit 1), all reverted byte-identically.
5. Full suite: 900 passed.

## Lessons

- A test bug surfaced twice: the host/port guard regex matched the `2024-01-01T00:00:00Z` example (fixed with a lowercase word boundary), and a depth guard that also limited scalars made the deepest cycle leaf `None` (only containers are limited now).
- `perl -pi` with backslashes in a bash replacement string silently mangles regexes and writes `\b` as a backspace: write such lines through a heredoc.
- Negative checks that mutate a script must be reverted from a saved copy and compared by `sha1sum`, not just by eye.
- Authored size ended near 1220 lines (source 363, tests 845) against an 800-line estimate: the forecast undercounted tests. `size:exception` is recommended.

## Not done

- Importing the collection into the Postman application.
- Verify, archive and commit (orchestrator/user).

Evidence: `openspec/changes/generated-project-postman-collection/gate-evidence.md`.
