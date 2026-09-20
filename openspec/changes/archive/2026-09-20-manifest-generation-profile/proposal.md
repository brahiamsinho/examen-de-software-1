# Proposal: Emit the Declared Generation Profile in the Domain Manifest

## Intent

`relational-generation-metadata` made the mapper carry §33 profile data (`Column.profile`, `Table.profile`), but no consumer reads it. The Domain Manifest still hides those facts behind the `Declared-Facts-Only Exclusion` requirement, written when the data did not exist (DD131). The assistant and a future frontend therefore cannot learn which attributes are searchable/sortable/read-only, which entities are auditable/read-only, which CRUD operations the author intended, or the default sort. This change closes that gap without inventing defaults.

## Scope

### In Scope

- Entity-level `profile` from `Table.profile`: `auditable`, `readOnly`, `crud` (canonical `create,read,update,delete` order), `defaultSort {attribute, direction}`.
- Attribute-level `profile` from `Column.profile`: `searchable`, `sortable`, `readOnly`.
- Omission rules: omit any key whose value is `None`; omit the whole `profile` object when the profile is `None` or declares no key.
- Resolve `defaultSort.attribute` from the raw `ElementId` to the manifest attribute name via `Column.source_element_id`; an unresolvable id raises `ManifestError`.
- Keep the builder decoupled: duck-typed attribute access, no `apps.relational_mapping` import (AST guard).

### Out of Scope

- `entity` (§33 flag) — semantics deferred (DD139).
- `aliases`, `entity` and `generation_metadata` — never emitted (`entity` semantics deferred, DD139; `aliases` not modelled, DD138).
- Filtering `operations[]` by `crud`; `crud` documents intent only. Open follow-up.
- Any edit to `apps/relational_mapping` or `apps/spring_generator`; compose/gate changes.
- Authoring path (UI/API/commands) for profile data.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `domain-manifest-export`: `Declared-Facts-Only Exclusion` becomes declared-facts-only *emission* — the five profile keys are emitted when declared and omitted when undeclared; `aliases`, `entity` and `generation_metadata` stay forbidden. `Entity Content` gains the optional `profile` objects.

## Approach

Additive, `schemaVersion` stays `1`. A new builder module (`builder/profile.py`) turns a duck-typed profile object into a dict of declared keys, returning `None` when empty; `entities.py` and `attributes.py` merge it in only when non-`None`. `defaultSort` resolution needs the table's columns, so it is done in the entity builder where both are in hand. Strict TDD, one PR.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/domain_manifest/builder/profile.py` | New | Profile → declared-keys dict |
| `backend/apps/domain_manifest/builder/entities.py` | Modified | Entity `profile` + `defaultSort` resolution |
| `backend/apps/domain_manifest/builder/attributes.py` | Modified | Attribute `profile` |
| `backend/apps/domain_manifest/builder/manifest.py` | Modified | `ManifestError` reuse |
| `backend/apps/domain_manifest/tests/*` | Modified | `EXCLUDED_KEYS`, `test_profile_output_neutral.py`, new profile tests |
| `docs/ai/DECISIONS_LOG.md` | Modified | New DDs |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Sample-model gate output drifts | Low | Sample declares no profile → byte-identical; pinned by existing determinism/gate tests |
| Builder re-couples to `relational_mapping` | Med | Existing AST guard in `test_builder_decoupling.py` |
| `EXCLUDED_KEYS` guard now over-broad | High (expected) | Narrow it to `aliases` + `entity` + `generation_metadata`, add positive emission tests |
| Unresolvable `defaultSort` id | Low | Typed `ManifestError`, fail fast, tested |

## Rollback Plan

Revert the single PR: delete `builder/profile.py`, restore the two builder modules and the test guards. No persisted state, no migration, no schema bump to undo.

## Dependencies

- Archived `relational-generation-metadata` (`Column.profile`, `Table.profile`, `DefaultSort`) — already merged.

## Success Criteria

- [ ] A declared table/column profile appears under `profile` with only declared keys.
- [ ] An undeclared profile emits no `profile` key at any level.
- [ ] `crud` is emitted in canonical order as a list of strings.
- [ ] `defaultSort.attribute` is the manifest attribute name; an unknown id raises `ManifestError`.
- [ ] `aliases`, `entity` and `generation_metadata` never appear; `schemaVersion` stays `1`.
- [ ] Sample-model `docs/domain-manifest.json` stays byte-identical; full backend suite green.
