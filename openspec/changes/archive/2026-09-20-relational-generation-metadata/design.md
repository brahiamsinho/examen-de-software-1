# Design: Carry Generation Profile Metadata Through Relational Mapping

## Technical Approach

Proposal Option A. Two frozen, hashable value objects in a new `relational_mapping/domain/profile.py`; a pure, model-free strict parser in a new `relational_mapping/mapping/profile_parser.py`; one typed error added to the existing `mapping/errors.py` hierarchy; optional `profile` fields (default `None`) on `Column` and `Table`; ~30 lines of wiring inside `mapper.py`. Nothing else reads `profile` in this change: `domain_manifest/` and `spring_generator/` are untouched, so the 41-file Spring oracle and the Domain Manifest output stay byte-identical.

## Architecture Decisions

### DD132 — Profile value objects live in `domain/profile.py`, not in `schema.py`

**Choice**: new module `backend/apps/relational_mapping/domain/profile.py` exporting `SortDirection`, `CrudOperation`, `DefaultSort`, `ColumnProfile`, `TableProfile`.
**Alternatives**: append to `schema.py`; put them in `domain/types.py`.
**Rationale**: `schema.py` is the §21 relational shape and `types.py` is the column/FK vocabulary; profile is §33 generation vocabulary, a different concern. A separate module also gives the import-purity guard a single, precise target.

### DD133 — Tri-state fields: `None` = undeclared, per key and per element

**Choice**: every profile field is `X | None`, default `None`; `Column.profile` / `Table.profile` default `None`; a `"profile"` mapping that parses to zero declared keys canonicalizes to `None`.
**Alternatives**: `bool` defaults of `False`; a sentinel `UNDECLARED` object.
**Rationale**: DD131 blocked the manifest precisely because an invented default is indistinguishable from author intent. One canonical representation of "nothing declared" also keeps equality/hashing and future emission deterministic.

### DD134 — Hashability by construction (no `Mapping`, no `list`, no `set` fields)

**Choice**: `@dataclass(frozen=True)` with only hashable field types — `bool | None`, `str`, `StrEnum`, `tuple[...]`, and nested frozen dataclasses. `crud` is `tuple[CrudOperation, ...]`, canonically ordered `create, read, update, delete`, never a `set`/`frozenset`/`list`.
**Alternatives**: `Mapping[str, object]` passthrough (proposal Option B); `frozenset[CrudOperation]`.
**Rationale**: exploration §2 — a `Mapping` field breaks `Column`'s structural hashing. A canonically ordered tuple is hashable *and* deterministic to emit in slice 2, which `frozenset` is not.

### DD135 — Strict parser is model-free and pure

**Choice**: `profile_parser.py` exposes exactly two entry points taking one raw entry, not the model:
`parse_table_profile(element_id, entry) -> TableProfile | None` and `parse_column_profile(element_id, entry) -> ColumnProfile | None`.
It imports only `apps.relational_mapping.domain.profile`, `apps.relational_mapping.mapping.errors`, and `apps.uml_modeling.domain.ids.ElementId`. It must NOT import `apps.uml_modeling.domain.model`, `apps.domain_manifest`, `apps.spring_generator`, Django, or any DB/Java module — pinned by an AST guard test.
**Alternatives**: parser takes `CanonicalUmlModel` and returns both maps.
**Rationale**: a model-free parser is table-driven-testable without building UML models, and keeps the level dispatch (class id vs attribute id) as the mapper's job, where that knowledge already lives.

### DD136 — `InvalidGenerationProfileError` subclasses `UnmappableModelError` in `mapping/errors.py`

**Choice**: defined in `backend/apps/relational_mapping/mapping/errors.py` next to the four existing errors.
**Alternatives**: define it inside `profile_parser.py`.
**Rationale**: callers already catch `UnmappableModelError` as the single mapper failure contract; splitting the hierarchy across two modules would break that one-import guarantee.

### DD137 — Key levels are disjoint except `readOnly`

**Choice**: table-level keys `entity, auditable, readOnly, crud, defaultSort`; column-level keys `searchable, sortable, readOnly`. A table-level key inside an attribute entry (and vice versa) is an unknown key at that level and raises.
**Alternatives**: one flat key set validated identically at both levels; `readOnly` table-only.
**Rationale**: §33 names the vocabulary without levels; disjoint levels turn a misplaced key into a loud error instead of silently dropped intent. `readOnly` is genuinely meaningful at both (a read-only entity vs a non-writable field).

### DD138 — `aliases`, `required`, `unique`, and provenance keys are out

**Choice**: `aliases` is NOT a profile key (it is absent from §33); `required`/`unique` are deferred per the proposal; `source`/`confidence` and every other key *outside* `"profile"` are ignored, not migrated, not validated. `aliases` stays in `domain_manifest/tests/test_manifest.py:71 EXCLUDED_KEYS`.
**Rationale**: strictness applies only inside the reserved `"profile"` namespace; existing fixtures carrying provenance must keep mapping unchanged.

### DD139 — `entity` is parsed and carried, its semantics deferred

**Choice**: `entity: bool | None` is accepted and stored; no mapper behaviour branches on it.
**Rationale**: proposal defers `entity: false` semantics because acting on it would change generated output; rejecting the key would force a re-parse change in slice 2.

### DD140 — `defaultSort.attribute` is stored as a raw `ElementId`, unresolved

**Choice**: `DefaultSort.attribute_id: ElementId`. The parser performs no cross-element lookup; an id that matches no attribute is not an error here (proposal: unknown element ids ignored). Resolution to a column name belongs to slice 2/3.
**Alternatives**: resolve to the mapped column name in the mapper.
**Rationale**: keeps the parser pure and avoids ordering coupling between profile parsing and column naming.

### DD141 — Profiles are collected up front, in one pass, before any table work

**Choice**: `map_to_relational` calls a new private `_collect_profiles(model, class_by_id, attribute_owner_by_id)` immediately after `class_by_id` is built (`mapper.py:529`) and before `_map_enumerations`.
**Alternatives**: parse lazily at each attachment point.
**Rationale**: lazy parsing leaves a malformed entry on an unvisited element silently unvalidated. Up-front iteration over `model.generation_metadata` in its own order makes "first offending entry" deterministic.

## Interfaces / Contracts

`backend/apps/relational_mapping/domain/profile.py` (new):

```python
class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"

class CrudOperation(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"

_CRUD_ORDER = (CrudOperation.CREATE, CrudOperation.READ,
               CrudOperation.UPDATE, CrudOperation.DELETE)

@dataclass(frozen=True)
class DefaultSort:
    attribute_id: ElementId
    direction: SortDirection

@dataclass(frozen=True)
class ColumnProfile:          # JSON keys: searchable, sortable, readOnly
    searchable: bool | None = None
    sortable: bool | None = None
    read_only: bool | None = None

@dataclass(frozen=True)
class TableProfile:           # JSON keys: entity, auditable, readOnly, crud, defaultSort
    entity: bool | None = None
    auditable: bool | None = None
    read_only: bool | None = None
    crud: tuple[CrudOperation, ...] | None = None
    default_sort: DefaultSort | None = None
```

`backend/apps/relational_mapping/domain/schema.py` (modified) — one field appended to each, defaults preserve every existing construction site:

```python
@dataclass(frozen=True)
class Column:
    ...
    owning_class_id: ElementId | None = None
    profile: ColumnProfile | None = None     # new, last field

@dataclass(frozen=True)
class Table:
    ...
    discriminator_values: Mapping[ElementId, str] = EMPTY
    profile: TableProfile | None = None      # new, last field
```

`backend/apps/relational_mapping/mapping/errors.py` (modified):

```python
class InvalidGenerationProfileError(UnmappableModelError):
    def __init__(self, element_id: ElementId, reason: str, key: str | None = None):
        self.element_id = element_id
        self.key = key
        self.reason = reason
        if key is None:
            super().__init__(f"Invalid generation profile for element {element_id!r}: {reason}")
        else:
            super().__init__(
                f"Invalid generation profile for element {element_id!r}, key {key!r}: {reason}"
            )
```

### JSON input shape

```python
generation_metadata = {
    ElementId("class-order"): {
        "source": "llm", "confidence": 0.9,          # outside "profile" -> ignored
        "profile": {
            "entity": True,
            "auditable": True,
            "readOnly": False,
            "crud": ["read", "create"],              # -> (CREATE, READ)
            "defaultSort": {"attribute": "attr-total", "direction": "desc"},
        },
    },
    ElementId("attr-total"): {
        "profile": {"searchable": True, "sortable": True, "readOnly": False},
    },
}
```

### Validation rules (exact `reason` strings)

| # | Condition | `key` | `reason` |
|---|---|---|---|
| 1 | entry is not a `Mapping` | `None` | `metadata entry is not a mapping` |
| 2 | `entry["profile"]` is not a `Mapping` | `"profile"` | `expected an object` |
| 3 | key not in this level's set | the key | `unknown table-level profile key` / `unknown column-level profile key` |
| 4 | boolean key whose value fails `isinstance(v, bool)` | the key | `expected a boolean` |
| 5 | `crud` not a `list`/`tuple`, or a non-`str` member | `"crud"` | `expected a list of CRUD operations` |
| 6 | member outside the four operations | `"crud"` | `unknown CRUD operation {value!r}` |
| 7 | repeated member | `"crud"` | `duplicate CRUD operation {value!r}` |
| 8 | `defaultSort` not a `Mapping` | `"defaultSort"` | `expected an object with 'attribute' and 'direction'` |
| 9 | `attribute` or `direction` missing | `"defaultSort"` | `missing required key {name!r}` |
| 10 | unknown nested key | `"defaultSort.<key>"` | `unknown key` |
| 11 | `attribute` not a non-empty `str` | `"defaultSort.attribute"` | `expected a non-empty string` |
| 12 | `direction` not `"asc"`/`"desc"` | `"defaultSort.direction"` | `expected 'asc' or 'desc'` |

Within a single entry the rules are applied in numeric order (1..12) and the first failing rule raises; e.g. `{"auditable": 1, "colour": True}` reports the unknown key (rule 3), not the boolean (rule 4).

Rules 4 and 6 use strict `isinstance(value, bool)` / exact-value membership: `1`, `"true"`, `"READ"` and `None` all raise. `"profile"` absent, or present and yielding zero declared keys, returns `None` (DD133). Keys outside `"profile"` and element ids matching neither a class nor an attribute are skipped without validation.

## Data Flow

```
CanonicalUmlModel.generation_metadata
        │
        ▼  _collect_profiles()  (mapper.py, after line 529)
   id is a class id ──→ parse_table_profile  ──→ table_profile_by_id[class_id]
   id is an attribute id ─→ parse_column_profile ─→ column_profile_by_id[attr_id]
   id is neither ─────→ skipped
        │
        ├─→ _map_table_for_root(...) ─→ draft.profile = table_profile_by_id.get(root_id)
        │        └─→ _map_attribute_column(..., profile=column_profile_by_id.get(attribute.id))
        │
        └─→ _freeze_table(draft) ──→ Table(..., profile=draft.profile)
```

### Mapper wiring, by line

| Location (current line) | Change |
|---|---|
| `mapper.py:18-34` imports | import `ColumnProfile`, `TableProfile` from `domain.profile`; `parse_column_profile`, `parse_table_profile` from `mapping.profile_parser`; `InvalidGenerationProfileError` from `mapping.errors` |
| `_TableDraft` (`:60-77`) | add `profile: TableProfile | None = None` as last field |
| new `_collect_profiles` (after `:78`) | build `attribute_owner_by_id` from `model.classes`; dispatch each `generation_metadata` entry by id kind; return `(table_profile_by_id, column_profile_by_id)` |
| `_map_attribute_column` (`:205-213`) | add keyword-only `profile: ColumnProfile | None = None`; pass `profile=profile` in BOTH `Column(...)` returns (`:221-228` enum branch, `:231-238` primitive branch) |
| `_map_table_for_root` (`:241-248`) | add keyword-only `table_profile_by_id` and `column_profile_by_id` params |
| `_map_table_for_root` (`:263`) | `draft.profile = table_profile_by_id.get(root_id)` right after `_TableDraft(...)` |
| `_map_table_for_root` (`:281-288`) | pass `profile=column_profile_by_id.get(attribute.id)` to `_map_attribute_column` |
| `_freeze_table` (`:507-517`) | add `profile=draft.profile` to `Table(...)` |
| `map_to_relational` (`:529-530`) | call `_collect_profiles(...)`; raises before any naming/table work |
| `map_to_relational` (`:537-543`) | thread both maps into `_map_table_for_root` |

### STI and synthetic columns

- **Table profile: root class only.** `draft.profile` is looked up with `root_id` (`tree_class_ids[0]`). A class-level `"profile"` entry on an STI **subclass** is parsed (so malformed data still raises) but never becomes a `Table.profile`.
- **Subclass-owned attribute columns.** Attribute profiles are keyed by the attribute's own element id, so an attribute declared on a subclass still receives its profile; the column's `owning_class_id` stays the subclass id, unchanged.
- **Synthetic columns are always `profile=None`.** `id` (`:265`), `class_type` (`:273`), simple FK columns (`:333`), and both join-table FK columns plus the join-table `id` (`_build_join_table`, `:361+`) are constructed without `profile` and need no code change. Join tables also keep `Table.profile is None`.

### Determinism

No new naming, ordering, or set iteration reaches the output. `crud` is canonicalized to `_CRUD_ORDER`; every profile field is an immutable scalar/tuple; parsing order follows `generation_metadata`'s own order, so the first offending entry — and therefore the raised message — is stable. Two `map_to_relational` calls on the same model stay `==`, with equal hashes for their columns and table profiles (`Table` and `RelationalModel` were already unhashable and remain compared by equality only).

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/relational_mapping/domain/profile.py` | Create | `SortDirection`, `CrudOperation`, `DefaultSort`, `ColumnProfile`, `TableProfile` |
| `backend/apps/relational_mapping/mapping/profile_parser.py` | Create | `parse_table_profile`, `parse_column_profile` + strict rules |
| `backend/apps/relational_mapping/mapping/errors.py` | Modify | Add `InvalidGenerationProfileError` |
| `backend/apps/relational_mapping/domain/schema.py` | Modify | `Column.profile`, `Table.profile`, default `None` |
| `backend/apps/relational_mapping/mapping/mapper.py` | Modify | `_collect_profiles` + the wiring table above |
| `backend/apps/relational_mapping/tests/test_profile.py` | Create | Value-object shape, frozen, hashable, import-purity guard |
| `backend/apps/relational_mapping/tests/test_profile_parser.py` | Create | Table-driven happy paths + all 12 error rules |
| `backend/apps/relational_mapping/tests/test_map_profiles.py` | Create | Mapper wiring, STI, synthetic columns, ignored keys/ids |
| `backend/apps/relational_mapping/tests/test_schema.py` | Modify | `profile is None` in `test_column_defaults` (`:49`) and `test_table_defaults` (`:94`) |
| `backend/apps/relational_mapping/tests/test_determinism.py` | Modify | Profile-carrying model maps equal + equal hash |
| `backend/apps/domain_manifest/`, `backend/apps/spring_generator/` | Unchanged | No consumer reads `profile` in this change |
| `backend/apps/uml_modeling/domain/model.py` | Unchanged | Container shape and `uml-domain-model` spec stay as-is |

## Testing Strategy

Strict TDD: a failing (RED) test precedes each implementation step, in the file order above.

| Layer | What to test | Approach |
|---|---|---|
| Unit — `test_profile.py` | All-`None` defaults; `FrozenInstanceError` on assignment; `hash()` works; `{p} == {p2}` for equal values; `hash(Column(..., profile=ColumnProfile(searchable=True)))` succeeds | Mirror `test_schema.py`'s existing style |
| Unit — purity guard | `domain.profile` and `mapping.profile_parser` import nothing matching `_FORBIDDEN_IMPORT_PREFIXES` (`django`, `psycopg`, `sqlite3`, `MySQLdb`, `java`, `org.springframework`), and `profile_parser` additionally imports no `apps.uml_modeling.domain.model`, `apps.domain_manifest`, `apps.spring_generator` | Reuse the `ast`+`inspect` `_imported_module_names` helper from `test_schema.py:30-38` |
| Unit — `test_profile_parser.py` | Happy paths (full table entry, full column entry, subset entries, `crud` reordering, `{}` → `None`, missing `"profile"` → `None`, provenance-only entry → `None`); one parametrized case per validation rule 1-12 asserting `InvalidGenerationProfileError` and `str(exc)` exactly | `@pytest.mark.parametrize` over `(entry, expected)` and `(entry, expected_message)` tuples |
| Integration — `test_map_profiles.py` | Declared class profile on the mapped `Table`; declared attribute profile on the mapped `Column`; undeclared → `None`; `id`/`class_type`/FK/join-table columns → `None` even when the owning class declares a profile; STI root wins and a subclass class-level entry sets no `Table.profile`; subclass-owned attribute keeps its profile with `owning_class_id` unchanged; unknown element ids ignored; malformed entry raises before any table is produced | Hand-built `generation_metadata` on the existing `tests/factories.py` models |
| Regression | `test_schema.py` defaults; `test_determinism.py` equality/hash; full `relational_mapping` suite unchanged | Existing tests, two new assertions |
| Byte-identity | 41-file Spring oracle and Domain Manifest output unchanged | Commands below |

**Mutation-check candidates** (each must be caught by a named test):

1. `isinstance(v, bool)` → truthiness: `{"searchable": 1}` must raise rule 4.
2. STI root lookup → any-class-in-tree: a subclass-only class entry must leave `Table.profile is None`.
3. `{}`/all-absent canonicalization → returning an empty instance instead of `None`.
4. `crud` canonical ordering dropped: `["read", "create"]` must yield `(CREATE, READ)`.
5. Synthetic-column guard removed: `id`/`class_type`/FK columns must stay `None`.
6. Strictness inverted: keys *outside* `"profile"` must never raise; unknown keys *inside* must always raise.
7. Error message shortened: assertions pin both `element_id` and `key` in `str(exc)`.

### Verification commands (run in Docker)

```
docker compose exec -T backend pytest -q apps/relational_mapping
docker compose exec -T backend pytest -q apps/generation_runner/tests/test_sample_model.py   # EXPECTED_FILE_COUNT = 41 + determinism
docker compose exec -T backend pytest -q apps/spring_generator/tests/test_inheritance_backward_compatibility.py  # per-file sha256 goldens
docker compose exec -T backend pytest -q apps/domain_manifest      # EXCLUDED_KEYS + manifest determinism
docker compose exec -T backend pytest -q                            # full backend suite
```

Byte-identity is verified by the two existing oracles, not by new goldens: `test_sample_model.py` pins the 41-file count and generation determinism, and `test_inheritance_backward_compatibility.py` pins per-file sha256 digests. `domain_manifest/tests/test_manifest.py::test_undeclared_facts_are_never_emitted` (parametrized over `EXCLUDED_KEYS`, which keeps `aliases`) plus `domain_manifest/tests/test_determinism.py` pin the manifest output. All four must pass unchanged, with zero edits to their expected values.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. This change is in-process pure-Python dataclass construction and dict parsing; it adds no I/O, no dynamic import, and no user-supplied code path.

## Migration / Rollout

No migration required. Additive only, single PR, no persisted state, no feature flag. Revert removes `profile.py`, `profile_parser.py`, the error, and the two fields; the mapper returns to ignoring `generation_metadata`.

## Open Questions

- [ ] None blocking. Deferred by the proposal and re-confirmed here: `required`/`unique` keys, `entity: false` semantics, `defaultSort.attribute` → column-name resolution, and the authoring path (commands/schemas/API/UI).
