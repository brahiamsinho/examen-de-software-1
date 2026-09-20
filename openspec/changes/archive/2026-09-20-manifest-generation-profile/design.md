# Design: Emit the Declared Generation Profile in the Domain Manifest

## Technical Approach

Proposal Approach, unchanged. One new pure module `builder/profile.py` shapes a duck-typed profile object into a dict of *declared* keys (or `None`); `attributes.py` attaches it per column, `entities.py` per table and owns `defaultSort` resolution because only it holds the table's columns. `ManifestError` moves to a new `builder/errors.py` to break the import cycle (DD143). `schemaVersion` stays `1`; the sample model declares no profile, so every existing sample assertion and the gate output stay byte-identical. Strict TDD, one PR, no compose/script change.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| **DD142** | New `backend/apps/domain_manifest/builder/profile.py` with exactly two pure functions, `build_column_profile(profile)` and `build_table_profile(profile, resolve_attribute)`. Both take the **profile object**, never the `Column`/`Table`, and read fields with `getattr(profile, "<snake_name>", None)`. No `apps.relational_mapping` import. | Inlining the shaping in `attributes.py`/`entities.py` (duplicates the omission rule twice); importing `ColumnProfile`/`TableProfile` for `isinstance` (breaks the AST guard in `tests/test_builder_decoupling.py`, which flags every `apps.*` name outside `apps.spring_generator.emit.naming`). | One omission rule, one module to test table-driven. `getattr(..., None)` is the duck-typing contract: a profile object missing a field is "undeclared", not an `AttributeError`. |
| **DD143** | `ManifestError` is defined in new `builder/errors.py`; `manifest.py` does `from .errors import ManifestError` and keeps exporting it, `builder/__init__.py` is unchanged. | Keeping it in `manifest.py` (`entities.py` → `manifest.py` → `entities.py` cycle); raising a local error and wrapping it in `manifest.py` (the message would have to be rebuilt, and the wrap point is far from the fact). | Smallest move that lets `entities.py` raise the app's one typed error. `from apps.domain_manifest.builder import ManifestError` (used by `tests/test_manifest.py:7` and the CLI) keeps working. |
| **DD144** | `defaultSort.attribute` is resolved in `entities.py` by an injected closure over the table; the manifest attribute name comes from a new shared `attributes.attribute_name(column) -> str` (`camel_case(column.name)`), which `_attribute()` now calls too. | Resolving inside `profile.py` (needs table knowledge and the error type); re-deriving `camel_case(column.name)` in `entities.py` (two naming sources, exactly the drift DD123 exists to prevent). | The resolver is the only place that knows both the column set and the failure mode; a single `attribute_name()` makes `defaultSort.attribute` provably equal to the emitted `attributes[].name`. |
| **DD145** | Omission: a key whose value is `None` is omitted; a profile that yields zero keys, or a `profile` attribute that is `None`/absent, produces **no `profile` key** at all. `entity` is never read (DD139 defers its semantics); `aliases` does not exist in the profile objects (DD138). | Emitting `null` for undeclared keys, as DD125 does for `maxLength`/`enum`. | DD131/DD133: for *these* keys, absence is the only honest encoding of "the author declared nothing"; `null` would read as a declared value. DD125's fixed-key rule stays for the pre-existing keys, so this is an additive exception, not a retype. |
| **DD146** | Enum members are read duck-typed through one helper, `_text(value) -> getattr(value, "value", value)`. `crud` becomes `list[str]` in declared canonical order; `defaultSort.direction` becomes the plain `str` `"asc"`/`"desc"`. | Passing `StrEnum` members straight into the dict (`json.dumps` would serialize them, but `manifest == expected_plain_dict` comparisons and `type(...) is str` checks get subtle); `str(member)`. | `.value` yields a real `str`, so the built dict is plain JSON data with no `apps.relational_mapping` type leaking into a consumer, and the AST guard never sees an import. |
| **DD147** | `crud` documents intent only: it does **not** filter `operations[]`. Recorded here as explicit tech debt and logged in `docs/ai/DECISIONS_LOG.md`. | Filtering the six operations by the declared `crud` subset. | `operations[]` is specified (spec: *CRUD Operations*) as what the generated controller actually serves; the generator ignores `crud` today, so filtering would make the manifest describe endpoints that exist. Revisit when the generator consumes `crud`. |
| **DD148** | `tests/test_manifest.py:71 EXCLUDED_KEYS` narrows to `["aliases", "entity", "generation_metadata"]`. The five newly legal keys get **positive emission tests** instead. | Deleting the guard; keeping it and asserting absence only on the sample model. | The guard's value is unchanged for what is still forbidden; the five keys move from "never" to "iff declared", which a positive test states and an absence test cannot. |
| **DD149** | `tests/test_profile_output_neutral.py` is retargeted, not deleted: a profile-carrying model now **does** change the manifest; an undeclared-profile model and the sample model do not. | Deleting the module (loses the sample-model neutrality half). | The old assertion encoded DD131, which this change supersedes; the surviving half is the byte-identity proof for the gate. |
| **DD150** | No `docker-compose.yml`, `scripts/verify-generated-project.sh` or gate change, and no new golden. Byte-identity of `docs/domain-manifest.json` is pinned by existing tests: `tests/test_manifest.py::test_sample_entity_header` (asserts `set(entity) == ENTITY_KEYS` for all six sample tables), `tests/test_attributes.py::test_sample_attribute` (full-dict equality per sample attribute) and `tests/test_determinism.py`. | Re-running the gate and recording new evidence. | The sample UML model carries no `generation_metadata`, so every profile is `None` and both key sets are unchanged by construction — proven offline, not by a gate run. |

## Interfaces / Contracts

`backend/apps/domain_manifest/builder/profile.py` (new, ~40 lines):

```python
"""Generation profile -> declared-keys dict (design.md DD142, DD145, DD146)."""

# (JSON key, profile attribute) in section 33 declaration order.
_COLUMN_KEYS = (("searchable", "searchable"), ("sortable", "sortable"), ("readOnly", "read_only"))
_TABLE_FLAGS = (("auditable", "auditable"), ("readOnly", "read_only"))


def _text(value):
    """A StrEnum member's wire value, duck-typed: no `apps.relational_mapping` import."""
    return getattr(value, "value", value)


def _declared(profile, keys) -> dict:
    declared = {}
    for json_key, field in keys:
        value = getattr(profile, field, None)
        if value is not None:
            declared[json_key] = value
    return declared


def build_column_profile(profile) -> dict | None:
    if profile is None:
        return None
    return _declared(profile, _COLUMN_KEYS) or None


def build_table_profile(profile, resolve_attribute) -> dict | None:
    if profile is None:
        return None
    declared = _declared(profile, _TABLE_FLAGS)
    crud = getattr(profile, "crud", None)
    if crud is not None:
        declared["crud"] = [_text(operation) for operation in crud]
    default_sort = getattr(profile, "default_sort", None)
    if default_sort is not None:
        declared["defaultSort"] = {
            "attribute": resolve_attribute(default_sort.attribute_id),
            "direction": _text(default_sort.direction),
        }
    return declared or None
```

`attributes.py` (modified):

```python
def attribute_name(column) -> str:          # new, shared with entities.py (DD144)
    return camel_case(column.name)

def _attribute(table, column) -> dict:
    attribute = {"name": attribute_name(column), ...}        # existing keys unchanged
    profile = build_column_profile(column.profile)           # duck-typed: getattr(column, "profile", None) is not needed,
    if profile is not None:                                  # `Column.profile` is a declared field with default None
        attribute["profile"] = profile
    return attribute
```

`entities.py` (modified):

```python
def _resolver(table):
    def resolve_attribute(attribute_id) -> str:
        for column in table.columns:
            if column.name != table.discriminator_column and column.source_element_id == attribute_id:
                return attribute_name(column)
        raise ManifestError(
            f"table {table.name!r} declares defaultSort on unknown attribute id {attribute_id!r}"
        )
    return resolve_attribute

def build_entity(table) -> dict:
    entity = {...}                                           # existing keys, unchanged order
    profile = build_table_profile(table.profile, _resolver(table))
    if profile is not None:
        entity["profile"] = profile                          # last key when present
    return entity
```

### Emitted shape

```json
{
  "name": "Purchase", "table": "purchase", "resourcePath": "/api/purchases",
  "attributes": [
    {"name": "total", "column": "total", "type": "decimal", "required": true,
     "primaryKey": false, "maxLength": null, "enum": null, "subtype": null,
     "profile": {"readOnly": false, "searchable": true, "sortable": true}}
  ],
  "profile": {
    "auditable": true,
    "crud": ["create", "read"],
    "defaultSort": {"attribute": "total", "direction": "desc"},
    "readOnly": false
  }
}
```

- **Builder insertion order** is the section 33 declaration order (`auditable, readOnly, crud, defaultSort`; `searchable, sortable, readOnly`). **Serialized order is alphabetical** — `serialize.write_json` already uses `sort_keys=True` (DD127), so the JSON text is the order shown above regardless of insertion. Dict equality ignores order, so tests may assert either.
- `crud` is a JSON **array of lowercase strings** in the canonical order the mapper already froze (`create, read, update, delete` filtered to the declared subset, DD134) — the builder never re-sorts it.
- `defaultSort` is exactly `{"attribute": <manifest attribute name>, "direction": "asc"|"desc"}`. Both values are plain `str`. The key is `attribute`, never `attributeId`: `tests/test_determinism.py` forbids the key `id` at any depth, and a name is what a consumer can join against `attributes[].name`.
- Value types: `auditable`/`readOnly`/`searchable`/`sortable` are JSON booleans passed through untouched (the parser already enforced `isinstance(v, bool)`, rule 4 of DD135).

### `defaultSort` resolution

| Case | Result |
|---|---|
| `attribute_id` matches a non-discriminator `Column.source_element_id` of this table | `attribute_name(column)` = `camel_case(column.name)` — identical to the emitted `attributes[].name` by construction (DD144) |
| STI: the id belongs to a **subclass-owned** attribute | Resolves normally. Subclass columns live in the root table (`owning_class_id` = subclass) and the attributes builder emits them with `subtype` set, so the name exists in `attributes[]` |
| Id matches no column, matches a synthetic column (`id`, `class_type`, FK — all `source_element_id is None`), or belongs to another table | `ManifestError("table 'vehicle' declares defaultSort on unknown attribute id 'attr-x'")` — raised during `build_entity`, so `build_manifest` fails before returning a partial document |

The discriminator column is excluded from the search because the attributes builder excludes it (`attributes.py:52`); resolving to a name absent from `attributes[]` would be a dangling reference.

### Determinism

No new ordering, naming or `set` iteration reaches the output: the two key tuples are literals, `crud` preserves the mapper's canonical tuple order, the resolver scans `table.columns` in order and returns the first match, and every emitted value is `bool`, `str`, `list[str]` or a two-key dict. `_text` returns the enum's `str` value, so re-serializing parsed JSON reproduces the bytes (`tests/test_determinism.py::test_serialization_is_sorted_indented_and_keeps_non_ascii`).

## Data Flow

    Table.profile ─┐
                   ├─▶ entities.build_entity ─▶ build_table_profile(profile, _resolver(table))
    table.columns ─┘                                   │  defaultSort.attribute_id
                                                       ▼
                                          scan columns ─▶ attribute_name(column) | ManifestError
    Column.profile ──▶ attributes._attribute ──▶ build_column_profile(profile)
                                                       │
                                                       ▼
                                   entity["profile"] / attribute["profile"]  (omitted when None)

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/domain_manifest/builder/profile.py` | Create | `_text`, `_declared`, `build_column_profile`, `build_table_profile` (~40) |
| `backend/apps/domain_manifest/builder/errors.py` | Create | `ManifestError(ValueError)` moved out of `manifest.py` (DD143, ~5) |
| `backend/apps/domain_manifest/builder/manifest.py` | Modify | `from .errors import ManifestError`; drop the class body; docstring no longer claims DD131 exclusion |
| `backend/apps/domain_manifest/builder/attributes.py` | Modify | `attribute_name()`; attach `profile` (~8) |
| `backend/apps/domain_manifest/builder/entities.py` | Modify | `_resolver()`; attach `profile` (~14) |
| `backend/apps/domain_manifest/tests/test_profile.py` | Create | Unit table for both builders + omission rules (~110) |
| `backend/apps/domain_manifest/tests/test_manifest.py` | Modify | Narrow `EXCLUDED_KEYS` (DD148); positive emission + `ManifestError` cases (~45) |
| `backend/apps/domain_manifest/tests/test_attributes.py` | Modify | Attribute-level `profile` present/absent (~20) |
| `backend/apps/domain_manifest/tests/test_profile_output_neutral.py` | Modify | Retarget to the new truth (DD149, ~15) |
| `backend/apps/domain_manifest/tests/test_builder_decoupling.py` | Unchanged | `_guarded_files()` globs `builder/**`, so `profile.py` and `errors.py` are scanned automatically |
| `openspec/specs/domain-manifest-export/spec.md` | Modify | Delta: `Declared-Facts-Only Exclusion` → emission; `Entity Content` gains `profile` |
| `docs/ai/DECISIONS_LOG.md`, `CURRENT_STATE.md`, `HANDOFF_LATEST.md`, `NEXT_STEPS.md`, `docs/ai/sessions/` | Modify | DD142-DD150 + the DD147 tech-debt entry |
| `docker-compose.yml`, `scripts/verify-generated-project.sh`, `apps/relational_mapping/**`, `apps/spring_generator/**` | Unchanged | DD150 |

Authored total ≈ 260 lines — comfortably inside the 800-line budget.

## Testing Strategy

Strict TDD: a RED test precedes each module, in the order below.

| Layer | What to test | Approach |
|---|---|---|
| Unit — `tests/test_profile.py` | `build_column_profile`: full/subset/all-`None`/`None` input; `build_table_profile`: flags, `crud` list of `str` in canonical order, `defaultSort` dict shape, `direction` is exactly `"asc"`/`"desc"` and `type(...) is str`; `{}`-equivalent profile → `None`; a `SimpleNamespace` with **no** profile fields → `None` (duck typing); `resolve_attribute` is called **only** when `default_sort` is declared | `@pytest.mark.parametrize` over `(profile, expected)` built from `SimpleNamespace` and from the real `ColumnProfile`/`TableProfile` (tests may import `apps.relational_mapping`; only `builder/**` is guarded) |
| Unit — `tests/test_attributes.py` | A `Column(profile=ColumnProfile(searchable=True))` emits `{"searchable": true}` and nothing else; `Column(profile=None)` emits **no** `profile` key; the six sample attributes stay byte-equal (existing `test_sample_attribute`) | Extend the existing `_table()` helper |
| Integration — `tests/test_manifest.py` | Entity `profile` emitted with the four declared keys; `defaultSort.attribute` equals the entity's own `attributes[].name`; STI: a subclass-owned attribute id resolves on the root entity; unknown id raises `ManifestError` with the exact message; `entity`/`aliases` never appear even when the table profile declares `entity=True`; `schemaVersion` still `1` | Hand-built `Table(..., profile=TableProfile(...))` + `dataclasses.replace` on the sample model |
| Guard (narrowed) | `EXCLUDED_KEYS == ["aliases", "entity", "generation_metadata"]` still absent from the sample manifest | DD148 |
| Neutrality / byte-identity | `test_profile_output_neutral.py`: a profile-carrying model **changes** the manifest (`!=`, and `"profile"` present); a model whose `generation_metadata` is `{}` and the sample model produce the manifest unchanged | DD149 |
| Regression | `tests/test_determinism.py`, `test_builder_decoupling.py`, `test_cli.py`, `generation_runner/tests/test_sample_model.py`, `spring_generator` goldens — all unchanged, zero edits to expected values | Existing tests |

**Mutation-check candidates** (each must be caught by a named test):

1. `if value is not None` → truthiness: a declared `readOnly: false` / `searchable: false` must still be emitted.
2. `or None` dropped: an all-`None` profile must emit **no** `profile` key, not `{}`.
3. `profile is None` guard dropped: a `Table.profile is None` must not raise and must emit no key.
4. `_text` returning the member instead of `.value`: `type(direction) is str` and `type(crud[0]) is str`.
5. `crud` re-sorted or turned into a `set`/`tuple`: `["create", "read"]` stays a list in that order.
6. Resolver returning `column.name` instead of `attribute_name(column)`: `full_name` vs `fullName`.
7. Resolver's `raise` replaced by `return None`/`""`: the unknown-id case must raise `ManifestError`, message pinned on both `table.name` and the id.
8. Discriminator exclusion dropped from the resolver: an id resolving to `class_type` must raise, since that name is absent from `attributes[]`.
9. `entity` added to `_TABLE_FLAGS`: `EXCLUDED_KEYS` still forbids it (DD139/DD148).
10. `crud` wired into `_operations()`: the six operations must stay six for a table declaring `crud: ["read"]` (DD147).

### Verification commands (run in Docker)

```
docker compose exec -T backend pytest -q apps/domain_manifest
docker compose exec -T backend pytest -q apps/relational_mapping apps/generation_runner
docker compose exec -T backend pytest -q
```

No gate run is required (DD150).

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. This change is in-process pure-Python dict shaping over an already-parsed, already-validated value object; it adds no I/O, no dynamic import, and no new CLI argument. The compose/gate boundary recorded in DD128/DD130 is untouched.

## Migration / Rollout

No migration required. Additive, single PR, no persisted state, no feature flag, no `schemaVersion` bump. Consumers written against v1 keep working: the new keys are optional and the document is a superset only when a profile is declared. Rollback = revert the PR (delete `profile.py`, fold `ManifestError` back into `manifest.py`, restore the two builder modules and the four test modules).

## Open Questions

- [ ] None blocking. Deferred and re-confirmed: `entity` semantics (DD139), `aliases` (DD138), `crud` → `operations[]` filtering (DD147, logged as tech debt), and the authoring path (UI/API/commands) for profile data.
