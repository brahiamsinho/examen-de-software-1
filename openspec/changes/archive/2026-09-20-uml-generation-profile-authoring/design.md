# Design: UML Generation Profile Authoring (Backend)

## Technical Approach

One new command (`SetGenerationProfile`) carried through the existing four-layer path — `schemas.py` → `services._command_from_payload` → `dispatcher.apply` → `handlers/` — plus cascade pruning inside the two existing remove handlers. The handler stays purely structural and never raises (DD6); every semantic rule is enforced at write time in `services.submit_command` by calling the already-shipped strict parser (`parse_table_profile` / `parse_column_profile`, DD135-DD141) rather than duplicating §33 rules. `codec.py` already round-trips `generation_metadata` verbatim, so persistence, `DocumentOut`, and the Channels broadcast need zero change.

> Size note: this artifact deliberately exceeds the 800-word default budget. The orchestrator required exact, copy-verbatim names, semantics, and error strings so `sdd-spec` and `sdd-tasks` can be mechanical. Density is in tables, not prose.

## Architecture Decisions

### DD151 — One command, `SetGenerationProfile(element_id, profile | None)`, server-inferred level

**Choice**: a single frozen dataclass; the server decides table-level vs column-level by looking the id up in the model.
**Alternatives**: `SetTableProfile` + `SetColumnProfile`; a `level` field on the payload.
**Rationale**: D6. The model already knows whether an id is a class or an attribute; a client-supplied level is a second source of truth that can disagree with the model. Mirrors `_collect_profiles`'s own dispatch (`mapper.py:97-105`), so write time and generation time infer the level identically.

### DD152 — The command carries the raw validated `Mapping`, not `TableProfile`/`ColumnProfile`

**Choice**: `profile: Mapping[str, object] | None` — the JSON body as received, stored verbatim into `generation_metadata[element_id]["profile"]`.
**Alternatives**: parse into the `relational_mapping` value objects and store those; re-serialize them on save.
**Rationale**: `apps/uml_commands` MUST NOT import `apps.relational_mapping` (its guard allows only `apps.uml_modeling` + self + stdlib), and `CanonicalUmlModel.generation_metadata` is typed `Mapping[ElementId, Mapping[str, object]]` — an opaque container by design. Storing value objects would force the codec to learn a §33 encoder for no gain; the parser is the authority at both ends and is called on the way in.

### DD153 — Semantic validation lives in `services.submit_command`, inside the row lock

**Choice**: `_validate_generation_profile(model, command)` runs after `_to_project_document(row)` and before `apply(...)`, inside the existing `@transaction.atomic` + `select_for_update()` block.
**Alternatives**: validate in `command_from_payload` (where the other payload decoding lives); validate in the handler; validate in `api.py`.
**Rationale**: the rules are model-relative (is this id a class or an attribute? does `defaultSort.attribute` exist?) and `command_from_payload` has no document. Validating inside the lock means a concurrent `RemoveAttribute` cannot slip between the check and the write. The handler cannot validate without breaking DD6's never-raises contract.

### DD154 — One named module exception to the `uml_documents` import guard

**Choice**: `apps.relational_mapping.mapping.profile_parser` becomes an exact-match allowance; every other `apps.relational_mapping.*` target is added to `_DISALLOWED_PREFIXES` and fails loudly. `apps/uml_commands`'s guard is untouched and stays pure.
**Alternatives**: copy the 12 validation rules into `uml_documents`; move `profile_parser` into `uml_modeling`; widen the allowlist to `apps.relational_mapping`.
**Rationale**: duplicating the rules guarantees write-time/generation-time drift (proposal risk #2). `profile_parser` is model-free and dependency-light by DD135 (`domain.profile`, `mapping.errors`, `uml_modeling.domain.ids` only), so no cycle is created. An exact-module allowance keeps the exception auditable — a prefix allowance would silently admit `mapper`, `schema`, and the whole app.

### DD155 — Level inference always runs; parsing runs only when a body is present

**Choice**: an `element_id` matching neither a class nor an attribute is a 422 even when `profile` is `None`/`{}` (a clear). Parsing is skipped for an empty body.
**Alternatives**: treat a clear on an unknown id as a silent no-op (the DD6 shape).
**Rationale**: a typo'd id in a clear request would otherwise return 200 while changing nothing, which reads as success to the client. The handler still short-circuits unknown ids (DD156), so the two layers disagree only in observability, never in stored state.

### DD156 — The handler owns exactly the `"profile"` key and prunes empties

**Choice**: `set_generation_profile` copies the existing entry, sets or pops only `"profile"`, and drops the whole entry when it becomes empty. Sibling keys (`source`, `confidence`, anything outside `"profile"`) are preserved byte-for-byte. An unknown `element_id` returns the model unchanged (DD6), never raises.
**Alternatives**: replace the whole entry; add `source`/`updatedBy` provenance keys.
**Rationale**: D5 and DD138 — provenance keys live outside `"profile"` and are explicitly not this change's business. Pruning the empty entry keeps `generation_metadata` free of `{}` residue, so "undeclared" has exactly one representation (DD133).

### DD157 — `defaultSort.attribute` is resolved at write time against the class, plus descendants for an inheritance root

**Choice**: the allowed id set is the class's own attribute ids; if the class is an **inheritance root** (no outgoing `GENERALIZATION` edge where it is `source`), the transitive descendants' attribute ids are added.
**Alternatives**: accept any id (parser behaviour, DD140); resolve only own attributes.
**Rationale**: D4. The parser stores the id unresolved by design, and the mapper attaches `Table.profile` to the **STI root** (`root_id = tree_class_ids[0]`), whose single table holds every descendant-owned column. A root legitimately sorts by a subclass attribute; a non-root class's profile never becomes a `Table.profile`, so widening it would be meaningless.

### DD158 — `RemoveClass` pruning must also clear a *foreign* `defaultSort` (correction)

**Choice**: `RemoveClass(C)` removes the entries keyed by `C.id` and by each of `C`'s attribute ids, **and** clears `defaultSort` on any *other* entry whose `defaultSort.attribute` is one of those removed attribute ids.
**Alternatives considered and rejected**: the narrower "`defaultSort` can only point at own attributes, so only the same class is affected". That is false under DD157 — an inheritance root's `defaultSort` may legitimately point at a **descendant's** attribute, so removing the descendant dangles the root's profile and makes generation fail. `RemoveClass` and `RemoveAttribute` therefore share one pruning primitive.

### DD159 — Relationship- and operation-keyed entries are not pruned

**Choice**: `RemoveRelationship` and `RemoveOperation` keep byte-identical behaviour; `RemoveClass` does not prune operation ids.
**Rationale**: `_collect_profiles` (`mapper.py:97-105`) dispatches only class ids and attribute ids and **skips every other id unvalidated**, so such entries are inert — never parsed, never emitted. Nothing in this change authors them. Touching those handlers would add diff with no observable effect.
**Accepted limitation**: removing a `GENERALIZATION` edge can leave a root's `defaultSort` pointing at an attribute that is no longer a descendant. The attribute still exists, so nothing dangles structurally; resolution to a column name is a later slice (DD140). Recorded in Open Questions.

## Data Flow

```
POST /api/orgs/{slug}/documents/{id}/commands
   │  {"type":"SetGenerationProfile","element_id":"...","profile":{...}|null}
   ▼
api.submit_command_view ── resolve_membership ── require_role(OWNER, EDITOR)   [VIEWER -> 403]
   ▼
services.command_from_payload ──► _command_from_payload ──► commands.SetGenerationProfile
   ▼
services.submit_command   @transaction.atomic + select_for_update()
   │
   ├─ _validate_generation_profile(document.model, command)          ◄── the only new gate
   │     ├─ id is a class id      ──► parse_table_profile({"profile": body})
   │     │                             └─► default_sort ──► _check_default_sort(...)
   │     ├─ id is an attribute id ──► parse_column_profile({"profile": body})
   │     └─ neither               ──► InvalidCommandPayloadError ──► 422
   │           InvalidGenerationProfileError ──► InvalidCommandPayloadError (message preserved) ──► 422
   ▼
dispatcher.apply ──► handlers.generation_profile.set_generation_profile (pure, never raises)
   ▼
codec.to_json (verbatim) ──► UmlDocument.data ──► on_commit ──► broadcast_document
   ▼
later: codec.from_json ──► map_to_relational ──► Table.profile / Column.profile
```

### Sequence — realtime fan-out (per `rules.design`)

```
Editor(HTTP)   api.py        services.submit_command      Postgres     ChannelLayer   Socket(s)
   │  POST cmd   │                    │                      │              │            │
   ├────────────►│                    │                      │              │            │
   │             ├─ require_role ────►│                      │              │            │
   │             │                    ├─ SELECT ... FOR UPDATE ─────────────►│           │
   │             │                    ├─ _validate_generation_profile        │           │
   │             │                    │     (422 here => rollback, no write) │           │
   │             │                    ├─ apply() -> revision+1               │           │
   │             │                    ├─ _save() ───────────►│               │            │
   │             │                    ├─ on_commit(broadcast_document)       │            │
   │  200 {rev}  │◄───────────────────┤   COMMIT ───────────►│               │            │
   │◄────────────┤                    └──────────────────────┴─ group_send ─►├─ document.update ─►
```

No command travels over the socket; the full document is broadcast after commit, unchanged from the `realtime-uml-collaboration` cycle.

## Interfaces / Contracts

### `backend/apps/uml_commands/commands.py` (modify)

```python
from collections.abc import Mapping   # new import

@dataclass(frozen=True)
class SetGenerationProfile:
    element_id: ElementId
    profile: Mapping[str, object] | None = None


UmlCommand = (
    AddClass | RemoveClass | RenameClass
    | AddAttribute | RemoveAttribute
    | AddOperation | RemoveOperation
    | AddRelationship | RemoveRelationship
    | SetGenerationProfile          # new, LAST member of the union
)
```

`profile` values MUST be JSON-native (`dict`, `list`, `str`, `int`, `float`, `bool`, `None`) — they arrive from a parsed JSON body and are written back through `codec.to_json` unchanged. The dataclass is frozen but not hashable in practice (a `Mapping` field); no existing code hashes commands.

### `backend/apps/uml_commands/handlers/generation_profile.py` (create)

```python
def set_generation_profile(
    model: CanonicalUmlModel, command: SetGenerationProfile
) -> CanonicalUmlModel:
    """Owns exactly the "profile" key of generation_metadata[element_id]."""
```

Exact semantics, in order:

| # | Condition | Result |
|---|---|---|
| 1 | `element_id` is neither a class id nor an attribute id of any class | return `model` **unchanged** (DD6), no raise |
| 2 | `command.profile` is truthy (a non-empty mapping) | `entry["profile"] = dict(command.profile)`, every sibling key preserved |
| 3 | `command.profile` is `None` or `{}` | `entry.pop("profile", None)` |
| 4 | the resulting `entry` is empty | drop `metadata[element_id]` entirely |
| 5 | the resulting metadata equals the input | return `model` unchanged (no `dataclasses.replace`) |

Never raises. Never touches `classes`, `enumerations`, or `relationships`.

Second public function in the same module, shared by both remove handlers (DD158):

```python
def prune_generation_metadata(
    metadata: Mapping[ElementId, Mapping[str, object]],
    removed_ids: frozenset[ElementId],
) -> Mapping[ElementId, Mapping[str, object]]:
```

| # | Rule |
|---|---|
| 1 | drop every entry whose key is in `removed_ids` |
| 2 | on every surviving entry, if `entry["profile"]["defaultSort"]["attribute"]` is a `str` whose `ElementId` is in `removed_ids`, pop `"defaultSort"` |
| 3 | if `"profile"` became empty, pop `"profile"`; if the entry became empty, drop the entry |
| 4 | any non-`Mapping` shape encountered on the way down is left untouched — structural only, never raises |
| 5 | return the **same object** when nothing changed, so callers can skip `dataclasses.replace` |

### `backend/apps/uml_commands/handlers/{classes,attributes}.py` (modify)

```python
# classes.remove_class, after the existing classes/relationships tuples:
removed = frozenset({command.class_id, *(a.id for a in target.attributes)})
metadata = prune_generation_metadata(model.generation_metadata, removed)
return dataclasses.replace(model, classes=..., relationships=..., generation_metadata=metadata)

# attributes.remove_attribute, after `remaining`:
metadata = prune_generation_metadata(model.generation_metadata, frozenset({command.attribute_id}))
return dataclasses.replace(model, classes=classes, generation_metadata=metadata)
```

`remove_class` must capture `target = model.class_by_id(command.class_id)` (it currently only null-checks it) to reach the attribute ids. Every other branch and every other handler is byte-identical.

### `backend/apps/uml_commands/dispatcher.py` (modify)

Add `SetGenerationProfile` to the `commands` import block, `set_generation_profile` to a new `from apps.uml_commands.handlers.generation_profile import ...` line, and the last `_HANDLERS` entry:

```python
_HANDLERS: dict[type, Handler] = {
    ...,
    RemoveRelationship: remove_relationship,
    SetGenerationProfile: set_generation_profile,
}
```

### `backend/apps/uml_documents/schemas.py` (modify)

```python
class SetGenerationProfileIn(Schema):
    type: Literal["SetGenerationProfile"]
    element_id: str
    profile: dict | None = None      # absent, null, and {} all mean "clear"
```

Appended as the last member of the `CommandIn` `Union` (discriminator `"type"` unchanged).

### `backend/apps/uml_documents/services.py` (modify)

New imports (the DD154 exception + the wrapped error). Per R1 the error is imported from `profile_parser` (which re-exports it from line 19), never from `mapping.errors`: `profile_parser` is the only `apps.relational_mapping` module `services.py` may import.

```python
from apps.relational_mapping.mapping.profile_parser import (
    InvalidGenerationProfileError,
    parse_column_profile,
    parse_table_profile,
)
from apps.uml_modeling.domain.elements import RelationshipKind   # already imported
```

`_command_from_payload`, appended after the `RemoveRelationshipIn` branch:

```python
if isinstance(payload, schemas.SetGenerationProfileIn):
    return commands.SetGenerationProfile(
        element_id=ElementId(payload.element_id), profile=payload.profile
    )
```

`submit_command`, two inserted lines between `document = _to_project_document(row)` and `result = apply(...)`:

```python
if isinstance(command, commands.SetGenerationProfile):
    _validate_generation_profile(document.model, command)
```

New private helpers:

```python
def _attribute_owner(model, element_id) -> UmlClass | None      # class holding this attribute id
def _descendant_class_ids(model, class_id) -> frozenset[ElementId]
    # BFS over relationships where kind is GENERALIZATION and target.class_id == current
def _is_inheritance_root(model, class_id) -> bool
    # no GENERALIZATION relationship with source.class_id == class_id
def _validate_generation_profile(model, command) -> None
```

`_validate_generation_profile` body, in order:

1. `owner = _attribute_owner(model, command.element_id)`; `target = model.class_by_id(command.element_id)`.
2. If `target is None and owner is None` → raise
   `InvalidCommandPayloadError(f"Unknown element id {command.element_id!r}: not a class or attribute of this document")`.
3. If `not command.profile` (None or `{}`) → `return` (a clear needs no parse).
4. `entry = {"profile": dict(command.profile)}`.
5. Inside `try: ... except InvalidGenerationProfileError as exc: raise InvalidCommandPayloadError(str(exc)) from exc` — the parser's message is preserved **verbatim**, including the `element_id`/`key` framing:
   - class id → `parsed = parse_table_profile(command.element_id, entry)`
   - attribute id → `parse_column_profile(command.element_id, entry)` then `return`
6. If `parsed is not None and parsed.default_sort is not None`, resolve it:
   - `allowed = {a.id for a in target.attributes}`
   - `descendants = _descendant_class_ids(model, target.id) if _is_inheritance_root(model, target.id) else frozenset()`
   - `allowed |= {a.id for cid in descendants for a in model.class_by_id(cid).attributes}`
   - if `parsed.default_sort.attribute_id not in allowed` → raise `InvalidCommandPayloadError` with the exact message below.

**Exact `defaultSort` rejection messages** (chosen to mirror `InvalidGenerationProfileError`'s own `element_id`/`key` framing so a client sees one consistent shape):

| Case | Message |
|---|---|
| class is not an inheritance root, or has no descendants | `Invalid generation profile for element {element_id!r}, key 'defaultSort.attribute': {attribute_id!r} is not an attribute of this class` |
| class is an inheritance root **with** at least one descendant | `Invalid generation profile for element {element_id!r}, key 'defaultSort.attribute': {attribute_id!r} is not an attribute of this class or its descendants` |

All three raise `InvalidCommandPayloadError`, already mapped to **422** with `{"detail": ..., "code": "invalid_command_payload"}` by `api.register_exception_handlers`. No change to `api.py`.

### `backend/apps/uml_documents/tests/test_import_boundary.py` (modify) — DD154

```python
_DISALLOWED_PREFIXES = ("apps.users", "apps.relational_mapping")
# DD154: the single named exception. services.py calls the strict §33 parser at
# write time so write-time and generation-time rules cannot drift. Exact match
# only — a prefix allowance would admit mapper/schema and the rest of the app.
_ALLOWED_EXACT_MODULES = ("apps.relational_mapping.mapping.profile_parser",)
```

Inside `test_no_disallowed_imports_exist`'s loop, immediately after the `sys.stdlib_module_names` `continue` and **before** both assertions:

```python
            if target in _ALLOWED_EXACT_MODULES:
                continue
```

Plus a new meta-guard test in the same file so any future widening is deliberate:

```python
def test_relational_mapping_exception_is_exactly_one_module():
    assert _ALLOWED_EXACT_MODULES == ("apps.relational_mapping.mapping.profile_parser",)
```

`backend/apps/uml_commands/tests/test_import_boundary.py` is **not** touched: `uml_commands` stays `apps.uml_modeling` + self-package + stdlib only. The new handler imports nothing new.

### Persisted-spec rescoping — `uml-document-persistence`

The persisted requirement `uml_documents Import Boundary` (`openspec/specs/uml-document-persistence/spec.md:129-145`) currently ends with a change-local freeze that this change necessarily violates:

> `MUST NOT modify any file under `apps/uml_modeling/` or `apps/uml_commands/`.`
>
> `#### Scenario: uml_modeling and uml_commands have zero diff`
> `- GIVEN this change's complete diff`
> `- WHEN files under `apps/uml_modeling/` and `apps/uml_commands/` are inspected`
> `- THEN neither directory shows any modified, added, or removed file`

`sdd-spec` MUST emit this as a `## MODIFIED Requirements` entry that rewrites the constraint from a frozen-diff rule into a standing **dependency-direction** rule:

- Keep `apps/uml_modeling/` frozen for this capability.
- Replace the `apps/uml_commands/` freeze with: `apps.uml_documents` MUST NOT own UML mutation semantics — every command dataclass, handler, and dispatcher registration MUST live under `apps/uml_commands/`; `uml_documents` MUST only construct `apps.uml_commands.commands` values and call `dispatcher.apply`.
- Add the DD154 exception sentence: `services.py` MAY import `apps.relational_mapping.mapping.profile_parser`, and no other `apps.relational_mapping` module.
- Replace the single scenario with three: `uml_modeling has zero diff`; `command semantics stay in uml_commands` (static inspection of `models/codec/services/schemas/errors` finds no command dataclass, handler function, or dispatcher registration); `exactly one relational_mapping module is importable`.

## File Changes

| File | Action | Description | ~LoC |
|---|---|---|---|
| `backend/apps/uml_commands/commands.py` | Modify | `SetGenerationProfile` + union member + `Mapping` import | 10 |
| `backend/apps/uml_commands/handlers/generation_profile.py` | Create | `set_generation_profile`, `prune_generation_metadata` | 60 |
| `backend/apps/uml_commands/handlers/classes.py` | Modify | `remove_class` cascade (DD158) | 6 |
| `backend/apps/uml_commands/handlers/attributes.py` | Modify | `remove_attribute` cascade | 5 |
| `backend/apps/uml_commands/dispatcher.py` | Modify | imports + `_HANDLERS` entry | 4 |
| `backend/apps/uml_documents/schemas.py` | Modify | `SetGenerationProfileIn` + union member | 8 |
| `backend/apps/uml_documents/services.py` | Modify | payload branch, 4 helpers, `submit_command` gate, imports | 70 |
| `backend/apps/uml_documents/tests/test_import_boundary.py` | Modify | DD154 exact allowance + meta-guard test | 12 |
| `backend/apps/uml_commands/tests/test_generation_profile.py` | Create | handler + pruning unit tests | 110 |
| `backend/apps/uml_commands/tests/test_dispatcher.py` | Modify | registration + revision-bump case | 15 |
| `backend/apps/uml_documents/tests/test_schemas.py` | Modify | discriminated-union round trip | 15 |
| `backend/apps/uml_documents/tests/test_services.py` | Modify | write-time validation cases | 70 |
| `backend/apps/uml_documents/tests/test_api.py` | Modify | 200 / 422 / viewer 403 | 40 |
| `backend/apps/uml_documents/tests/test_generation_profile_integration.py` | Create | codec + `map_to_relational` end to end | 60 |
| `docs/ai/DECISIONS_LOG.md`, `docs/ai/CURRENT_STATE.md`, `docs/ai/HANDOFF_LATEST.md`, `docs/ai/NEXT_STEPS.md` | Modify | project convention (see below) | 40 |
| `backend/apps/uml_documents/codec.py`, `api.py`, `models.py`, `apps/relational_mapping/**`, `apps/uml_modeling/**` | Unchanged | no change needed — round-trip and 422 handler already exist | 0 |

**Estimate: ~285 source + ~310 test + ~40 docs ≈ 525 lines** (`additions + deletions`, authored). Above the 400-line review budget but inside the 800-line change budget. Delivery strategy is `single-pr` (resolved by the orchestrator) — `size:exception` is accepted here because the slice has no internal seam: the guard amendment, the handler, and the write-time validation are only meaningful together, and splitting them would ship a command that can persist an unvalidatable profile.

## Testing Strategy

Strict TDD — each row's RED test precedes its implementation, in file order above.

| Layer | File | What to test | Approach |
|---|---|---|---|
| Unit — handler | `uml_commands/tests/test_generation_profile.py` | Set on a class id; set on an attribute id; sibling keys (`source`, `confidence`) preserved; `None` removes only `"profile"`; `{}` removes only `"profile"`; entry dropped when it becomes empty; sibling-only entry survives a clear; unknown id → model unchanged and **no raise**; input model never mutated | `@pytest.mark.parametrize` over `(initial_metadata, command, expected_metadata)` |
| Unit — pruning | same file | `RemoveClass` drops the class entry + each attribute entry; a **root's** `defaultSort` pointing at a removed **descendant** attribute is cleared (DD158); `"profile"` dropped when `defaultSort` was its only key; entry dropped when `"profile"` was its only key; `RemoveAttribute` drops the attribute entry and clears its class's `defaultSort`; unrelated entries untouched; empty `generation_metadata` → same object identity (byte-identical no-op) | table-driven over `(model, command, expected_metadata)` |
| Unit — dispatcher | `uml_commands/tests/test_dispatcher.py` | `SetGenerationProfile` resolves a handler; `revision` bumps by exactly 1; `validate()` still runs | extend the existing per-command table |
| Unit — schema | `uml_documents/tests/test_schemas.py` | `{"type":"SetGenerationProfile", ...}` discriminates to `SetGenerationProfileIn`; `profile` omitted / `null` / `{}` all parse; nested `crud` list and `defaultSort` object survive as plain JSON | `TypeAdapter(CommandIn).validate_python` |
| Unit — validation | `uml_documents/tests/test_services.py` | Unknown id → exact "Unknown element id" message; each parser rule (unknown key, non-bool, bad `crud` member, duplicate `crud`, bad `defaultSort.direction`) → 422 message **identical** to `str(InvalidGenerationProfileError)`; table key on an attribute id and column key on a class id both rejected; `defaultSort` to an own attribute OK; to a descendant attribute of an **inheritance root** OK; to a descendant attribute of a **non-root** rejected with the non-root message; to an unrelated class's attribute rejected; clearing an unknown id still 422 (DD155); **no document row is written on any 422** (assert `revision` unchanged) | parametrized over `(profile_body, expected_message)` |
| Integration — HTTP | `uml_documents/tests/test_api.py` | OWNER 200 `{revision, validation}`; EDITOR 200; VIEWER **403**; invalid profile **422** with `code == "invalid_command_payload"`; cross-org id 404 | existing `conftest.py` client + membership factories |
| Integration — end to end | `uml_documents/tests/test_generation_profile_integration.py` | POST a full table profile + a column profile → `codec.to_json` → reload → `codec.from_json` → `map_to_relational` produces `Table.profile == TableProfile(entity=True, auditable=True, crud=(CREATE, READ), default_sort=DefaultSort(...))` and `Column.profile == ColumnProfile(searchable=True, ...)`; then POST `profile=None` → the table maps back to `Table.profile is None`; STI case: a root's `defaultSort` on a descendant attribute survives the round trip | real document row + the `relational_mapping` test factories |
| Boundary | `uml_documents/tests/test_import_boundary.py` | The amended guard passes; the meta-guard pins the one-module tuple; a synthetic `apps.relational_mapping.mapping.mapper` target still fails | existing AST helper |
| Regression | full backend suite | `uml_commands`, `uml_documents`, `relational_mapping`, `domain_manifest`, `spring_generator` goldens unchanged | `docker compose exec -T backend pytest -q` |

**Mutation-check candidates** (each must be caught by a named test above):

1. Sibling-key preservation replaced by whole-entry replacement → the `source`/`confidence` case must fail.
2. `if command.profile` weakened to `if command.profile is not None` → the `{}`-clears case must fail.
3. Empty-entry pruning removed → the "entry dropped when empty" case must fail.
4. DD155 inverted (unknown id silently no-ops on a clear) → the "clearing an unknown id is 422" case must fail.
5. DD158 narrowed to same-class only → the root/descendant `defaultSort` pruning case must fail.
6. DD157 widened to accept any attribute id in the model → the "unrelated class's attribute" case must fail.
7. DD157 narrowed to own attributes only → the inheritance-root descendant case must fail.
8. Validation moved after `apply()` or outside the lock → the "no row written on 422" case must fail.
9. `str(exc)` replaced by a generic 422 message → every parser-message assertion must fail.
10. Handler made to raise on an unknown id → the DD6 no-op case must fail.

### Verification commands (Docker)

```
docker compose exec -T backend pytest -q apps/uml_commands
docker compose exec -T backend pytest -q apps/uml_documents
docker compose exec -T backend pytest -q apps/relational_mapping apps/domain_manifest apps/spring_generator
docker compose exec -T backend pytest -q
```

## Documentation (project convention — `openspec/config.yaml` `rules.design`)

Architecture decisions MUST be recorded in **both** places; `sdd-tasks` MUST emit these as explicit work units, not as an afterthought:

| File | Required content |
|---|---|
| `docs/ai/DECISIONS_LOG.md` | DD151-DD159 with rationale, **especially DD154** — the first named exception to an app import boundary in this codebase (proposal risk #1 mitigation) and DD158's correction of the naive same-class pruning rule |
| `docs/ai/CURRENT_STATE.md` | `generation_metadata` is now authorable from the backend API; slice 2 (frontend panel) still pending |
| `docs/ai/HANDOFF_LATEST.md` | The new command, the guard exception, the rescoped persisted requirement |
| `docs/ai/NEXT_STEPS.md` | Follow-up change `uml-generation-profile-panel` (slice 2) |
| `docs/ai/TRACEABILITY_MATRIX.md` (if present) | `SetGenerationProfile` → `uml-command-bus` requirement → handler → tests |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The change is in-process Python over an already-authenticated Django Ninja endpoint; it adds no I/O sink, no dynamic import, and no user-supplied code path. The one security-relevant surface (authorization) is unchanged: the existing `require_role(OWNER, EDITOR)` gate already covers the endpoint, and the VIEWER-403 case is an explicit test row. The one new trust boundary is untrusted JSON reaching `generation_metadata`; it is closed by the strict parser at write time (DD153), which rejects every key outside the §33 vocabulary before anything is persisted.

## Migration / Rollout

No migration required. Additive and backward compatible: existing rows carry `generation_metadata = {}`, which already parses to `None`, and the parser ignores unknown element ids. No feature flag — the command is inert until a client sends it, and the frontend does not yet send it (slice 2). Rollback is a plain revert of the change commits; reverting leaves every persisted profile intact but unreadable by the write path, and generation continues to parse it, so a revert is non-destructive.

## Open Questions

- [ ] None blocking.
- [ ] Deferred (DD159): removing a `GENERALIZATION` edge can leave an inheritance root's `defaultSort` pointing at an attribute that is no longer a descendant. Nothing dangles structurally (the attribute still exists) and `DefaultSort.attribute_id` is stored unresolved by DD140, so this is deliberately left to the slice that resolves `defaultSort` to a column name.
- [ ] Deferred (proposal): last-writer-wins on concurrent profile edits — no base-revision check exists anywhere in the command bus today; adding one is a bus-wide change, not a profile-specific one.
