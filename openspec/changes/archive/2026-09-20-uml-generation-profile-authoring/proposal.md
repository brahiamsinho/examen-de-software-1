# Proposal: UML Generation Profile Authoring (Backend)

## Intent

The §33 generation profile is parsed strictly at generation time (`relational_mapping/mapping/profile_parser.py`, DD132-DD141), but no command writes it: every real document carries `generation_metadata = {}`, so every generated table/column is undeclared. This change adds the backend write path so a profile can be authored, persisted, and consumed end to end. Slice 1 of 2 (backend only).

## Scope

### In Scope

- `SetGenerationProfile(element_id, profile | None)` frozen command + `CommandUnion` member (D6: one command, server infers table vs column level from the model).
- Structural handler: owns only the `"profile"` key, preserves sibling metadata keys, prunes the entry when the profile is empty/`None` (D5: no provenance keys).
- Dispatcher registration in `_HANDLERS`.
- `SetGenerationProfileIn` Pydantic schema + `CommandIn` discriminated-union member; `services.command_from_payload` mapping.
- Write-time validation in `services.submit_command` via `parse_table_profile` / `parse_column_profile`; `InvalidGenerationProfileError` → `InvalidCommandPayloadError` → 422.
- Narrow named amendment of the `uml_documents` import guard allowing only `apps.relational_mapping.mapping.profile_parser`.
- `defaultSort.attribute` must resolve to an attribute of the class, or of its descendants for an inheritance root (D4).
- Cascade pruning on `RemoveClass` (class entry + its attribute entries) and `RemoveAttribute` (attribute entry + clear a `defaultSort` pointing at it).
- Tests: handler, schema, services/API (viewer 403, 422), cascade, integration through `codec` + `map_to_relational`.

### Out of Scope

- Frontend panel — follow-up change `uml-generation-profile-panel` (slice 2).
- Undo/redo, version history, provenance keys, `RenameAttribute`, Spring-side filtering by profile.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `uml-command-bus`: new `SetGenerationProfile` requirement; `RemoveClass` / `RemoveAttribute` cascade extended to `generation_metadata`.
- `uml-document-persistence`: command submission accepts the new payload and performs write-time profile validation; import-boundary requirement amended for the single named parser module (and its "zero diff in `apps/uml_commands/`" scenario rescoped).
- `generation-profile`: unchanged — the parser stays the sole strict authority, reused at write time.

## Approach

Keep the handler purely structural (DD6: never raises) and put semantic validation in `services`, before `apply`, reusing the existing parser rather than duplicating rules. The codec already round-trips `generation_metadata` verbatim, so persistence and WS broadcast need no change.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/uml_commands/commands.py` | Modified | New command + union member |
| `backend/apps/uml_commands/handlers/` | New/Modified | New handler; cascade in remove handlers |
| `backend/apps/uml_commands/dispatcher.py` | Modified | `_HANDLERS` entry |
| `backend/apps/uml_documents/schemas.py` | Modified | `SetGenerationProfileIn` |
| `backend/apps/uml_documents/services.py` | Modified | Mapping + write-time validation |
| `backend/apps/uml_documents/tests/test_import_boundary.py` | Modified | Named guard exception |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Guard amendment weakens app isolation | Med | Allow exactly one module path; record the exception in `docs/ai/DECISIONS_LOG.md` |
| Write-time and generation-time rules drift | Med | Call the same parser; integration test through `map_to_relational` |
| Last-writer-wins overwrites a concurrent profile edit | Med | Accepted (no base revision anywhere today); full-document broadcast keeps clients converged |
| Viewer attempts to author (403) | Low | Existing `require_role(OWNER, EDITOR)` gate (D3); covered by test |
| Inheritance-root `defaultSort` resolution is subtle | Med | Explicit descendant-scan scenario in spec and tests |

## Rollback Plan

Revert the change commit(s). The feature is additive: dropping the command leaves existing documents valid, since `generation_metadata` entries already parse to `None` when empty and the parser ignores unknown element ids.

## Dependencies

- Archived `relational-generation-metadata` (parser, value objects, key vocabulary) — already landed.

## Success Criteria

- [ ] A profile authored via the commands endpoint survives save → codec round-trip → `map_to_relational` into `Table.profile` / `Column.profile`.
- [ ] Invalid profiles (bad key, non-bool, unknown `defaultSort.attribute`) return 422 and never persist.
- [ ] Removing a class or attribute leaves no stale `generation_metadata` entry and no dangling `defaultSort`.
- [ ] VIEWER gets 403; OWNER/EDITOR succeed.
- [ ] Backend suite green; diff ≈350-450 lines, within the 800-line budget.
