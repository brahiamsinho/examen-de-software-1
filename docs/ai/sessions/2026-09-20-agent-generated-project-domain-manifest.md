# Session: generated-project-domain-manifest apply (2026-09-20)

Agent: Claude (sdd-apply executor, two runs). Strict TDD. Change: `generated-project-domain-manifest` (§37 item 16).

## What was built

- `backend/apps/domain_manifest/`: pure `builder/` (`attributes`, `relationships`, `entities`, `manifest`), `serialize.py` (duplicated), plain `__main__` `cli.py`, `apps.py`, 6 table-driven test modules (87 tests).
- `backend/config/settings.py`: `apps.domain_manifest` right after `apps.postman_export`.
- `docker-compose.yml`: `generate-manifest` (profile `jvm-verify`, no `depends_on`, no `rm -rf`, literal command).
- `scripts/verify-generated-project.sh`: fourth step `run --rm generate-manifest`.

## Order of work

1. Observed the real sample model before asserting (6 tables, `product_tag` one composite unique, `vehicle` discriminator `class_type`).
2. RED/GREEN pairs: decoupling guard, attributes, relationships, entities, manifest + drift guard, determinism, CLI. Slice 1 ended at 811 authored lines (259 non-test): stop threshold exceeded, accepted as `size:exception` by the orchestrator, tests kept.
3. Slice 2: compose stanza + gate step, gate exit 0 (`domain-manifest.json` 12496 bytes), negative check exit 1 reverted by equal sha1, default services unchanged.
4. Full suite: 987 passed. Docs updated (DD121-DD131).

## Lessons

- Naming errors from `emit.naming` are not `ValueError`; the builder wraps them so the CLI has one error type.
- The `sd` binary is not installed on this host: a sed-style replace that silently fails leaves the file untouched and the "negative" gate then passes. Check that the mutation landed (`rg`) before running the gate.
- `git diff` of a compose file is not empty after adding a stanza; compare hashes of the diff before and after the negative check instead.
- Docs go stale between commits (the HANDOFF still called the Postman change uncommitted): verify each line on disk.

## Next

`sdd-verify`, archive, commit (never `.pi/`). Follow-up: carry `generation_metadata` through the mapper before adding searchable/sortable/defaultSort/auditable/readOnly/aliases (DD131).
