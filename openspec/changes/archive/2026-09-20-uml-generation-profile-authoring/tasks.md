# Tasks: UML Generation Profile Authoring (backend)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~525 |
| 400-line budget risk | High |
| Chained PRs recommended | No |
| Suggested split | single PR (indivisible slice) |
| Delivery strategy | exception-ok |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | SetGenerationProfile end to end | PR 1 | `docker compose exec -T backend pytest -q apps/uml_commands apps/uml_documents` | API tests in `test_api.py` (real endpoint, Docker) | revert the change commits (non-destructive) |

Orchestrator resolutions: R1 services imports ONLY `apps.relational_mapping.mapping.profile_parser`; verified `InvalidGenerationProfileError` is importable from it (line 19 imports it). Design snippet importing from `mapping.errors` is superseded. R2 rescoped layout scenario; pinned-count tests found (below). `docs/ai/TRACEABILITY_MATRIX.md` does not exist: skipped.

## Phase 1: Command bus (`backend/apps/uml_commands/`)

- [x] 1.1 R2 sweep: `rg "_HANDLERS|get_args|nine" backend/apps` (read-only) confirmed pins: `tests/test_commands.py:196`, `tests/test_dispatcher.py:100`, `uml_documents/tests/test_schemas.py:63`; rerun after edits, fix any other.
- [x] 1.2 RED `tests/test_commands.py`: union test -> ten types; construct/frozen/default-None tests.
- [x] 1.3 GREEN `commands.py`: `SetGenerationProfile`, LAST union member, `Mapping` import.
- [x] 1.4 RED `tests/test_generation_profile.py`: handler table (set class/attribute, siblings, replace, None, `{}`, prune-empty, sibling-only, unknown id no raise, no mutation).
- [x] 1.5 GREEN `handlers/generation_profile.py`: `set_generation_profile`.
- [x] 1.6 RED same file: `prune_generation_metadata` (6 scenarios), RemoveClass/RemoveAttribute cascade incl. foreign root `defaultSort` (DD158), rel/op entries kept, same-object.
- [x] 1.7 GREEN `generation_profile.py`, `handlers/classes.py`, `handlers/attributes.py`: prune primitive + cascade.
- [x] 1.8 RED `tests/test_dispatcher.py`: `nine` -> ten entries; registration, revision +1, `validate()`.
- [x] 1.9 GREEN `dispatcher.py`: import + last `_HANDLERS` entry.

## Phase 2: Documents (`backend/apps/uml_documents/`)

- [x] 2.1 RED `tests/test_schemas.py`: nine -> ten shapes; omitted/null/`{}` parse; nested JSON intact.
- [x] 2.2 GREEN `schemas.py`: `SetGenerationProfileIn`, LAST `CommandIn` member.
- [x] 2.3 RED `tests/test_import_boundary.py`: `test_relational_mapping_exception_is_exactly_one_module`; synthetic `mapping.mapper` and `apps.users` still fail.
- [x] 2.4 GREEN same file: `_ALLOWED_EXACT_MODULES`, `_DISALLOWED_PREFIXES` gains `apps.relational_mapping`, exact-match `continue`.
- [x] 2.5 RED `tests/test_services.py`: payload -> `commands.SetGenerationProfile`.
- [x] 2.6 GREEN `services.py`: `_command_from_payload` branch.
- [x] 2.7 RED `tests/test_services.py`: unknown id (also on clear, DD155), parser messages verbatim, wrong level, `defaultSort` own/root-descendant/non-root/unrelated/no-descendants exact messages, no row written.
- [x] 2.8 GREEN `services.py`: helpers, gate in `submit_command`, profile_parser-only imports (R1).
- [x] 2.9 RED->pass `tests/test_import_boundary.py`: static check that `models/codec/services/schemas/errors` define no command, handler, or registration.

## Phase 3: API and integration

- [x] 3.1 `tests/test_api.py`: OWNER/EDITOR 200, VIEWER 403, 422 + `invalid_command_payload`, cross-org 404, clear 200 + broadcast.
- [x] 3.2 Create `tests/test_generation_profile_integration.py`: codec round-trip, `map_to_relational` Table/Column profile, clear -> None, STI root.

## Phase 4: Mutation checks (each reverted, re-verified green)

- [x] 4.1 Design mutations 1-5 (sibling replace, `is not None`, no pruning, DD155 inverted, DD158 narrowed): confirm each named test fails.
- [x] 4.2 Mutations 6-10 (DD157 widened/narrowed, validate after apply, generic message, handler raises): same.

## Phase 5: Verification

- [x] 5.1 `docker compose exec -T backend pytest -q` on `apps/uml_commands`, `apps/uml_documents`, `apps/relational_mapping apps/domain_manifest apps/spring_generator`, then full suite.
- [x] 5.2 `git diff --stat` empty for `frontend/`, `backend/apps/uml_modeling/`, `backend/apps/relational_mapping/`.

## Phase 6: Docs

- [x] 6.1 `docs/ai/DECISIONS_LOG.md`: DD151-DD159 (stress DD154, DD158).
- [x] 6.2 `openspec/changes/uml-generation-profile-authoring/design.md`: patch services import per R1; confirm DD151-DD159 match log.
- [x] 6.3 `docs/ai/CURRENT_STATE.md`: profile authorable via API; slice 2 pending.
- [x] 6.4 `docs/ai/HANDOFF_LATEST.md`: command, guard exception, rescoped requirements.
- [x] 6.5 `docs/ai/NEXT_STEPS.md`: `uml-generation-profile-panel`.
- [x] 6.6 Create `docs/ai/sessions/2026-09-20-agent-uml-generation-profile-authoring.md`.
- [x] 6.7 Archive reminder: merge delta including both MODIFIED requirements and rescoped scenarios; touch up stale text.
