# Session — Generated Project Boot Smoke (apply)

Date: 2026-09-19

## Goal

Implement `generated-project-boot-smoke` (spec §37 item 13, slice 3 of 3): extend the manual compile gate so it also boots the generated Spring jar against a throwaway Postgres and proves one CRUD round-trip.

## Accomplished

- Wrote `backend/apps/generation_runner/tests/test_boot_smoke_contract.py` (8 Docker-free tests). It is a characterization test: it passes immediately, and two temporary mutations turned 2 of 8 tests red before being reverted.
- Probed the Gradle image: `curl 8.18.0` is present, so the single `_http` seam needed no fallback.
- Added `gen-db` and `jvm-boot-smoke` to `docker-compose.yml` (profile `jvm-verify`, no ports); default `docker compose config --services` is unchanged.
- Created `scripts/boot-smoke.sh` and extended `scripts/verify-generated-project.sh` with a second `run` step and an EXIT trap that removes `gen-db` (never `down`).
- Ran the gate: exit 0, `BUILD SUCCESSFUL`, ready in 4-5s, statuses 201/200/204/404. Negative run exits 4 with `password authentication failed`; no `gen-db` container survives.
- Full backend suite: 836 passed; `apps/generation_runner`: 67 passed.

## Findings

- F1: the design used one `GEN_DB_PASSWORD` for both `gen-db` and the app, so the first negative run passed with exit 0. Fixed by giving `gen-db` its own `GEN_DB_SERVER_PASSWORD`.
- F2: a stack trace pushed the root cause out of the failure-log tail. Fixed by listing `FATAL`/`Caused by` lines first.
- No generator defect was exposed.

## Relevant Files

- `scripts/boot-smoke.sh`, `scripts/verify-generated-project.sh`, `docker-compose.yml`
- `backend/apps/generation_runner/tests/test_boot_smoke_contract.py`
- `openspec/changes/generated-project-boot-smoke/gate-evidence.md`
- `docs/ai/DECISIONS_LOG.md` (DD92-DD102)

## Next Steps

- Run `sdd-verify`, then archive; commit only when the user is ready (never `.pi/`). No commit was created in this session.
