# Exploration: uml-generation-profile-authoring

Read-only exploration. Goal: let a user author the §33 generation profile so it lands in `CanonicalUmlModel.generation_metadata[element_id]["profile"]` (parsed strictly at generation time by `relational_mapping/mapping/profile_parser.py`, DD132-DD141). Today no command touches it and real documents carry `{}`.

## 1. Write path today

- **UI:** the right sidebar of `frontend/src/app/(app)/documents/[docId]/page.tsx:176-285` is a stack of `Card`s ("Agregar"/"Eliminar") wrapping presentational forms that receive `classes`, `onSubmit={submitCommand}`, `disabled`. There is no inspector; the canvas only taps/drags nodes.
- **Frontend command type:** `frontend/src/lib/uml_documents.ts:116-142` (`UmlCommandIn`, 8 of 9 backend shapes), `submitCommand` (`:177-186`) POSTs `/api/orgs/{slug}/documents/{id}/commands`. `state/document.ts:324-336` refetches the doc after the POST; WS `document.update` merges by revision.
- **HTTP:** `backend/apps/uml_documents/api.py:70-92`: membership -> `require_role(OWNER, EDITOR)` (VIEWER gets 403) -> `services.command_from_payload` -> `services.submit_command` -> `{revision, validation}`.
- **Schema:** `schemas.py:15-107`, one Pydantic `*In` per command, discriminated union `CommandIn`. `services.py:186-233` maps payload to command; `KeyError/ValueError/TypeError` become `InvalidCommandPayloadError` -> 422.
- **Persistence:** `services.py:130-146` `submit_command` (atomic, row lock, `apply`, `_save`, `on_commit(broadcast_document)`).
- **Command bus:** `uml_commands/commands.py` (frozen dataclasses + union), `dispatcher.py` (`_HANDLERS`, `apply` bumps revision and validates), handlers are pure `(model, command) -> model`, never raise (DD6).
- **Codec:** `codec.py:80/89` already round-trips `generation_metadata` verbatim, so a nested `{"profile": {...}}` survives. The frontend already types `UmlModel.generation_metadata`.
- **Realtime:** Django Channels; commands are not sent over the socket; every commit broadcasts the full doc. No undo/redo/version history exists, and last-writer-wins applies (no base revision).

## 2. Existing pattern

9 commands (AddClass, RemoveClass, RenameClass, AddAttribute, RemoveAttribute, AddOperation, RemoveOperation, AddRelationship, RemoveRelationship). Backend layout `uml_commands/{commands,dispatcher,handlers/*}.py`; tests under `uml_commands/tests` and `uml_documents/tests`. Frontend: presentational component with its own Vitest test in `components/workspace/__tests__/`; UI stack Next 16 (breaking changes: read `node_modules/next/dist/docs/` before page-level edits), React, jotai, Tailwind, `@base-ui/react`, local `components/ui/*`. UI copy is Spanish.

## 3. Validation, dangling ids, renames

- Import boundaries: `uml_commands` may import only `uml_modeling`/`uml_commands` + stdlib (`test_import_boundary.py:24-25`); `uml_documents` allowlist excludes `relational_mapping` for `models/codec/services/schemas/errors` (`test_import_boundary.py:43-53`, `api.py` excluded). `profile_parser.py` imports only `relational_mapping.domain.profile`, `mapping.errors` and `uml_modeling`; no cycle.
- Recommendation: validate at write time in `services.submit_command` by calling `parse_table_profile` (class id) or `parse_column_profile` (attribute id) with `{"profile": body}`, converting `InvalidGenerationProfileError` into `InvalidCommandPayloadError` (existing 422). This needs one deliberate, narrow amendment of the `uml_documents` boundary guard (allow only `apps.relational_mapping.mapping.profile_parser`). The handler stays purely structural. Generation-time strict parsing remains the authority.
- The parser stores `defaultSort.attribute` unresolved (DD140) and generation raises `ManifestError` on an unknown id, so write time should also check the target exists.
- Deletion: `remove_class` and `remove_attribute` never touch `generation_metadata`. A stale `defaultSort.attribute` after `RemoveAttribute` would make generation fail. Cascade pruning is needed (class entry + its attribute entries; attribute entry + clear `defaultSort` pointing at it).
- Rename: ids are stable, metadata keys never go stale.

## 4. Slicing (800-line budget)

- **Slice 1 backend (~350-450 lines):** `SetGenerationProfile(element_id, profile|None)`, structural handler (only touches the `"profile"` key, preserves sibling keys, empty/None removes it), dispatcher registration, `SetGenerationProfileIn`, write-time validation in services + guard amendment, cascade pruning, tests (handler, schema, service/api incl. viewer 403 and 422, cascade, integration through codec and `map_to_relational`).
- **Slice 2 frontend (~350-450 lines):** `UmlCommandIn` variant, presentational `GenerationProfileForm.tsx` (tri-state controls unset/true/false, prefill from `generation_metadata`), a new "Perfil de generación" Card in the sidebar, Vitest tests.
- Risks: guard amendment is an architectural exception (record in DECISIONS_LOG); last-writer-wins; tri-state needed because absent means "undeclared" and differs from `false`; Next 16 caveat for the page edit.

## Orchestrator resolution of the decisions (the user delegated: "ok hacelo"; recommended options taken, to be recorded in the proposal)

- D1 properties: all keys (table: entity, auditable, readOnly, crud, defaultSort; column: searchable, sortable, readOnly); `defaultSort` restricted to the class's own attributes in the UI.
- D2 UI location: a new "Perfil de generación" Card group in the existing sidebar (slice 2).
- D3 roles: the existing OWNER/EDITOR gate; VIEWER read-only.
- D4 `defaultSort.attribute`: rejected at write time when the id is not an attribute of the class (or, for inheritance roots, of its descendants); cleaned up on `RemoveAttribute`.
- D5 the command owns only the `"profile"` key; no provenance keys added.
- D6 one command `SetGenerationProfile(element_id, profile|None)` for both levels; the server infers the level from the model.
- Split: this change (`uml-generation-profile-authoring`) is slice 1, backend only. The frontend panel is a separate follow-up change (`uml-generation-profile-panel`).
