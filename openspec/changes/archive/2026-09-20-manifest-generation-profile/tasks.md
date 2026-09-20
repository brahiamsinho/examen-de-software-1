# Tasks: Emit the Declared Generation Profile in the Domain Manifest

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~260 (tests ~190, prod ~70) plus docs |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Profile emission in manifest | PR 1 | `docker compose exec -T backend pytest -q apps/domain_manifest` | N/A: pure in-process, no gate (DD150) | Revert the PR; no state |

## Phase 1: ManifestError move (DD143)

- [x] 1.1 RED: in `backend/apps/domain_manifest/tests/test_manifest.py`, assert `builder.errors.ManifestError` is `builder.ManifestError` and subclasses `ValueError`.
- [x] 1.2 GREEN: create `backend/apps/domain_manifest/builder/errors.py`; `manifest.py` imports it, drops the class body and the DD131 docstring claim.

## Phase 2: Profile shaping (DD142, DD145, DD146)

- [x] 2.1 RED: create `backend/apps/domain_manifest/tests/test_profile.py`, parametrized: each key, declared `false`, omission, all-`None` and no-field `SimpleNamespace` give `None`, crud plain-str list, direction plain str, resolver spy not called.
- [x] 2.2 GREEN: create `backend/apps/domain_manifest/builder/profile.py` (`_text`, `_declared`, `build_column_profile`, `build_table_profile`).

## Phase 3: Attribute profile (DD144)

- [x] 3.1 RED: in `tests/test_attributes.py`, `attribute_name` (`fullName`) and column profile present, `{"searchable": false}`, absent.
- [x] 3.2 GREEN: `builder/attributes.py`: add `attribute_name(column)`, use it in `_attribute`, attach column profile.

## Phase 4: Entity profile and defaultSort

- [x] 4.1 RED: in `tests/test_manifest.py`: full entity profile, `fullName` resolution, STI subclass id, unknown/synthetic/foreign/discriminator id with exact message, `entity=True` not emitted.
- [x] 4.2 GREEN: `builder/entities.py`: `_resolver`, `ManifestError` raise, attach table profile last.

## Phase 5: Guards (DD148)

- [x] 5.1 Narrow `EXCLUDED_KEYS` to `["aliases", "entity", "generation_metadata"]` in `tests/test_manifest.py`; add alphabetical-serialization and `schemaVersion == 1` tests.

## Phase 6-8: Neutrality, crud, determinism

- [x] 6.1 Retarget `tests/test_profile_output_neutral.py` (DD149): profile model differs and has `profile`; `{}` metadata equals sample.
- [x] 7.1 Test in `tests/test_manifest.py`: `crud: ["read"]` keeps six `operations[]` (DD147).
- [x] 8.1 Test in `tests/test_manifest.py`: profile-carrying model built and serialized twice is byte-identical, no `id` key.

## Phase 9: Mutation checks (revert each, re-run `pytest -q apps/domain_manifest`)

- [x] 9.1 M1-M5: truthiness, `or None` dropped, `None` guard dropped, `_text` member, crud re-sorted.
- [x] 9.2 M6-M8: `column.name` resolver, `raise` to `return None`, discriminator exclusion dropped.
- [x] 9.3 M9-M10: `entity` in `_TABLE_FLAGS`, `crud` wired into `_operations()`.

## Phase 10: Verification (Docker)

- [x] 10.1 `docker compose exec -T backend pytest -q apps/domain_manifest`.
- [x] 10.2 Tripwires unedited: `test_sample_entity_header`, `test_sample_attribute`, `test_determinism`.
- [x] 10.3 `test_builder_decoupling.py` passes unedited; run `pytest -q apps/relational_mapping apps/generation_runner`.
- [x] 10.4 `docker compose exec -T backend pytest -q` (full suite).
- [x] 10.5 `git diff --stat` empty for `backend/apps/relational_mapping` (read-only), `backend/apps/spring_generator` (read-only), `docker-compose.yml` (read-only), `scripts` (read-only).

## Phase 11: Docs

- [x] 11.1 `docs/ai/DECISIONS_LOG.md`: DD142-DD150, DD131 superseded, DD147 tech debt.
- [x] 11.2 Update `docs/ai/CURRENT_STATE.md`, `docs/ai/HANDOFF_LATEST.md`, `docs/ai/NEXT_STEPS.md`.
- [x] 11.3 Add session note under `docs/ai/sessions/`.
- [x] 11.4 Archive-time: in `openspec/specs/domain-manifest-export/spec.md` REPLACE (not append) heading `Declared-Facts-Only Exclusion` with `Declared-Facts-Only Emission`; fix Purpose text saying §33 `generation_metadata` is out of scope.
