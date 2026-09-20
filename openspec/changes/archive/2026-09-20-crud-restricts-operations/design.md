# Design: CRUD Declaration Restricts Operations (slice 1 — shared function + Domain Manifest)

## Technical Approach

One pure derivation `effective_operations(profile)` lands in `apps.relational_mapping.domain.profile` (the `generation-profile` capability's own home) and is exposed to the manifest builder as a **property of the `Table` protocol the builder already duck-types**, so `tests/test_builder_decoupling.py` stays unedited. `builder/entities.py` filters its existing `_OPERATIONS` rows by the effective names and suppresses `resourcePath` when the set is empty. Slice 2 (`spring-generator-crud-restriction`) imports the same function directly.

## Architecture Decisions

Numbering continues after DD159 (highest in `docs/ai/DECISIONS_LOG.md`). Per `openspec/config.yaml` `rules.design`, DD160-DD167 MUST be written to `DECISIONS_LOG.md` **and** kept here (dual documentation is a project convention).

### DD160 — `effective_operations` home, signature and export

**Choice**: in `backend/apps/relational_mapping/domain/profile.py`, module level, public (no underscore), no `__all__` in that module today so plain module-level definition is the export:

```python
# The controller's own declaration order (Controller.java.j2); mirrored by
# domain_manifest.builder.entities._OPERATIONS, pinned by a cross-app test.
OPERATION_NAMES: tuple[str, ...] = ("create", "findById", "update", "delete", "list", "count")

_CRUD_TO_OPERATIONS = {
    CrudOperation.CREATE: ("create",),
    CrudOperation.READ: ("findById", "list", "count"),
    CrudOperation.UPDATE: ("update",),
    CrudOperation.DELETE: ("delete",),
}
_READ_OPERATIONS = frozenset(_CRUD_TO_OPERATIONS[CrudOperation.READ])


def effective_operations(profile: "TableProfile | None") -> tuple[str, ...]:
    """Operation names a table's declared profile leaves enabled (DD160-DD161)."""
    crud = None if profile is None else profile.crud
    allowed = set(OPERATION_NAMES) if crud is None else {name for op in crud for name in _CRUD_TO_OPERATIONS[op]}
    if profile is not None and profile.read_only is True:
        allowed &= _READ_OPERATIONS
    return tuple(name for name in OPERATION_NAMES if name in allowed)
```

**Alternatives rejected**: a new module `domain/operations.py` (splits one 60-line value-object module for no gain, and the capability spec names `domain/profile.py`); returning `list`/`set` (breaks hashability conventions and determinism); returning `CrudOperation` members (the consumers need controller-method names, not the four CRUD verbs).
**Rationale**: pure, zero new imports, so the existing `Module import purity` scenario of `generation-profile` keeps covering it unchanged.

### DD161 — Truth table (D1/D2/D3 confirmed; exhaustive, copy verbatim into spec and tests)

`profile is None` and `TableProfile()` are identical rows. Output is always a subtype-free `tuple[str, ...]` in `OPERATION_NAMES` order, independent of declared `crud` order.

| `crud` | `read_only` `None` / `False` | `read_only` `True` |
|---|---|---|
| `None` (or `profile is None`) | `("create","findById","update","delete","list","count")` | `("findById","list","count")` |
| `()` | `()` | `()` |
| `(CREATE,)` | `("create",)` | `()` |
| `(READ,)` | `("findById","list","count")` | `("findById","list","count")` |
| `(UPDATE,)` | `("update",)` | `()` |
| `(DELETE,)` | `("delete",)` | `()` |
| `(CREATE, READ)` | `("create","findById","list","count")` | `("findById","list","count")` |
| `(CREATE, UPDATE, DELETE)` | `("create","update","delete")` | `()` |
| `(CREATE, READ, UPDATE, DELETE)` | all six | `("findById","list","count")` |

Empty result `()` is reachable exactly two ways: a declared empty `crud`, or `read_only=True` with a `crud` containing no `READ`. `read_only=True` never *adds* an operation. No parse-time rejection of `readOnly` + write `crud` (D3, DD133 "never invent").

### DD162 — Decoupling: a `Table` property, not an import and not caller injection

**Evidence**: `_guarded_files()` is `(ROOT / "builder").rglob("*.py") + [serialize.py]`, so `builder/entities.py` **is** scanned; `_offenders` allows only `apps.spring_generator.emit.naming`. `cli.py` (the only caller of `build_manifest`) is separately restricted to `CLI_ALLOWED = ("apps.domain_manifest", "apps.generation_runner.samples.sample_model")`.

| Option | Guard impact | Verdict |
|---|---|---|
| (a) `entities.py` imports `effective_operations` | Breaks `test_builder_and_serializer_import_only_the_naming_module`; contradicts spec `Profile Builder Decoupling` | Rejected |
| (b) Narrow guard amendment (DD154 shape) | Turns a structural invariant into an exception list; DD154 was justified by 12 duplicated validation rules with write-path drift risk — here the alternative is free | Rejected |
| (c) Caller injection (`build_entity(table, operations=...)`) | `cli.py` cannot import `apps.relational_mapping` either, so it breaks `test_cli_imports_only_its_own_app_and_the_sample_model` too, **and** changes a public builder signature | Rejected (strictly worse) |
| (d) `Table.effective_operations` property, read duck-typed | **Zero guard change, zero spec change** | **Chosen** |

**Choice**: add to `apps.relational_mapping.domain.schema.Table` (which already imports `TableProfile` and already carries the method `column_by_name`):

```python
    @property
    def effective_operations(self) -> tuple[str, ...]:
        return effective_operations(self.profile)
```

`entities.py` reads `table.effective_operations` exactly as it already reads `table.name`, `table.columns`, `table.profile` and `table.discriminator_column` — one more attribute on a protocol it already consumes without importing. A **property** (not a method) is chosen so it cannot be confused with the `getattr(..., None)` omission idiom of `builder/profile.py`, and because a property is not a dataclass field: `__eq__` and `repr` of the frozen `Table` are unaffected (determinism preserved; `Table` stays unhashable because of a dict-typed field, unchanged by this change). Direct attribute access (not `getattr` with a fallback) is used deliberately: a silent all-six fallback would hide a broken contract.

### DD163 — `entities.py`: filter the rows, suppress the path, keep name validation

`_OPERATIONS` stays the single source of `method` / path suffix / `successStatus`. Only the name column is filtered:

```python
def _operations(resource_path: str | None, names: tuple[str, ...]) -> list[dict]:
    if resource_path is None:
        return []
    return [
        {"name": name, "method": method, "path": resource_path + suffix, "successStatus": status}
        for name, method, suffix, status in _OPERATIONS
        if name in names
    ]


def build_entity(table) -> dict:
    operations = table.effective_operations
    # Inheritance tables render as entity + repository only (DD126); an empty effective set has the same shape (DD163).
    resource_path = None if _has_inheritance(table) else "/api/" + resource_path_segment(table.name)
    if not operations:
        resource_path = None
```

Iteration order comes from `_OPERATIONS`, never from `names`, so canonical order holds regardless of the caller. The path segment is still computed **before** suppression for every non-inheritance table, so `resource_path_segment()`'s `InvalidResourcePathError` (→ `ManifestError`) fires exactly as today; only emission is suppressed. The inheritance short-circuit is untouched, so no inheritance table is newly validated. `build_table_profile` is not touched: `crud` and `readOnly` keep being emitted verbatim in `entity["profile"]`.

### DD164 — One owner for "`resourcePath` is null iff `operations[]` is empty"

**Choice**: the owner is **`CRUD Operations`** in `openspec/specs/domain-manifest-export/spec.md`, which already owns the inheritance coupling scenario (`operations[] == []` and `resourcePath is null`). The delta generalizes it from "inheritance" to "no generated controller" (inheritance **or** empty effective set) and states the biconditional once.

**Reconciliation, no delta needed on the other two**:
- `Entity Content` (line 39) lists required keys and says `resourcePath` (`/api/<segment>`). It is already silent about the existing `null` case for inheritance, so this change introduces **no new** contradiction; the null rule is stated by the owner requirement. Leaving it unmodified avoids restating five scenarios for a pre-existing imprecision.
- `Manifest Derivation and Purity` → `Names follow the generator` is bound to "a table and column in the sample model". The sample declares no profile, output is byte-identical, so the scenario stays exactly as true as today. **Unchanged.**

sdd-spec MUST NOT open either requirement.

### DD165 — Drift guard and DECISIONS_LOG history stay as they are

`Endpoint Drift Guard` and `test_computed_paths_equal_the_paths_springdoc_served` are **unchanged**: the sample model declares no profile, so computed paths and the 15 fixture paths still match, and the test already compares only entities that have a resource path (`resources = {e["resourcePath"] for e in entities if e["resourcePath"]}`). Recorded latent constraint (not a slice-1 change): `resources <= computed` only holds while every entity with a resource path keeps at least one suffix-`""` operation (`create` or `list`); a future *sample* model declaring e.g. `crud: ["delete"]` would break that assertion, not this change.

`Profile Emission Determinism and Sample Neutrality` → `Decision log records supersession and debt` requires the log to record "the DD147 tech-debt entry". The DD147 line MUST therefore be **annotated as retired in place, never deleted**, which keeps that scenario true and avoids a five-scenario MODIFIED block.

### DD166 — Transient manifest/generator divergence, time-boxed to slice 2

Between slice 1 and slice 2, a *profile-restricted* model produces a manifest with fewer operations than the generator's still-six endpoints. Accepted, by construction, single release. No committed fixture uses a restricted model (`api-docs.json`, the Postman fixture and the boot-smoke `Customer` all come from the profile-free sample), so no golden, `docker-compose.yml` or `scripts/` change is needed and no gate run is required. Slice 2 removes the divergence by consuming the same function.

### DD167 — DD147 retired for the manifest

DD147 ("declared `crud` does NOT filter `operations[]`", tech debt) is retired for `domain-manifest-export` by DD160-DD163, and fully retired once slice 2 lands. The log keeps the original DD147 text plus a "retired by DD167 (manifest) / slice 2 (generator)" annotation.

## Data Flow

    CanonicalUmlModel ─→ profile_parser ─→ TableProfile(crud, read_only)
                                                │
                       relational_mapping.domain.profile.effective_operations(profile)
                                                │
                              Table.effective_operations  (property, DD162)
                                    │                         │
        (slice 1) builder/entities.py                  (slice 2) spring_generator/emit/context.py
          filter _OPERATIONS, null resourcePath          gate controller/service methods
                    │
            domain-manifest.json

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/relational_mapping/domain/profile.py` | Modify | `OPERATION_NAMES`, `_CRUD_TO_OPERATIONS`, `_READ_OPERATIONS`, `effective_operations()` (~20 lines) |
| `backend/apps/relational_mapping/domain/schema.py` | Modify | `Table.effective_operations` property + import (~4 lines) |
| `backend/apps/domain_manifest/builder/entities.py` | Modify | `_operations(resource_path, names)` filter; suppress `resource_path` when empty (~6 lines) |
| `backend/apps/relational_mapping/tests/test_profile.py` | Modify | Truth-table, determinism and constant-order tests (~70 lines) |
| `backend/apps/relational_mapping/tests/test_schema.py` | Modify | Property delegation + not-a-field test (~12 lines) |
| `backend/apps/domain_manifest/tests/test_manifest.py` | Modify | Invert `:282`; empty-set, read-only, undeclared and anti-drift tests (~50 lines) |
| `openspec/specs/domain-manifest-export/spec.md` (delta) | Modify | MODIFIED `CRUD Operations`; RENAMED+MODIFIED `CRUD Declaration …`; MODIFIED `Declared-Facts-Only Emission` (~90 lines) |
| `openspec/specs/generation-profile/spec.md` (delta) | Modify | ADDED `Effective Operations Derivation` (~28 lines) |
| `docs/ai/DECISIONS_LOG.md`, `docs/ai/CURRENT_STATE.md` | Modify | DD160-DD167, DD147 annotation, slice-2 dependency (~25 lines) |
| `docs/domain-manifest.json`, `frontend/`, `builder/profile.py`, `tests/test_builder_decoupling.py` | Unchanged | Sample declares no profile; guard and emission untouched |

**Size estimate**: ~30 source + ~132 test + ~118 spec + ~25 docs ≈ **305 authored lines**. `400-line budget risk: Medium` (spec deltas dominate).

## Spec Delta Plan

`openspec/changes/crud-restricts-operations/specs/…/spec.md`. A MODIFIED block must restate the whole requirement (header, body, every scenario) because archive compose replaces the block.

**`generation-profile` — ADDED**

`### Requirement: Effective Operations Derivation` — `apps.relational_mapping.domain.profile` MUST expose `OPERATION_NAMES` (the six controller names, in controller order) and a pure `effective_operations(profile: TableProfile | None) -> tuple[str, ...]`; `Table.effective_operations` MUST be a property delegating to it. Scenarios: *Undeclared profile yields all six* (`None`, `TableProfile()`); *Declared crud maps to operation names* (the DD161 mapping); *readOnly intersects the declared crud* (incl. write-only `crud` → `()`); *Declared empty crud yields no operation*; *Order is canonical and deterministic* (declared order irrelevant, two calls equal, members are plain `str`); *Table exposes its effective operations*. The capability Purpose needs no edit: emission stays owned by `domain-manifest-export`.

**`domain-manifest-export`**

1. **MODIFIED `### Requirement: CRUD Operations`** — "exactly these six items" → "exactly the entity's **effective operations** (see *Effective Operations Derivation*), in this canonical order", keeping the six literal rows as the undeclared case; state the biconditional **`resourcePath` is `null` if and only if `operations[]` is empty** (DD164). Scenarios: keep `Six ordered operations` (sample `Customer`, undeclared) and `Inheritance entities have no operations`; add `Restricted entity lists only its effective operations` and `Empty effective set drops the controller and the resource path`.
2. **RENAMED + MODIFIED** — the delta header MUST be exactly:
   `### Requirement: CRUD Declaration Does Not Filter Operations → CRUD Declaration Restricts Operations`
   followed by a `(Reason: DD147 is retired — the declared crud now restricts operations[]; the old heading asserts the opposite of the shipped behaviour.)` line (the archive compose tool accepts renames only in this form). New body: the declared `crud`/`readOnly` MUST restrict `operations[]` through `effective_operations`, MUST NOT reorder it, and MUST still be emitted verbatim under `entity["profile"]`. Scenario `Declaring crud keeps the six operations` → `Declaring crud restricts the operations` (`crud: ["read"]` → `findById, list, count` and `entity["profile"]["crud"] == ["read"]`).
3. **MODIFIED `### Requirement: Declared-Facts-Only Emission`** — the only change is the final clause: drop `crud` filtering of `operations[]` from the deferred-items list (it is no longer deferred), keep `entity` and `aliases`. Everything else, including all seven scenarios, is restated verbatim.

**Grep sweep already done — every other "six" is safe**: `Entity Content` line 65 and `Profile Emission…` line 333 say "all six sample **tables**" (table count, not operations); line 176 "operations in the fixed order above" stays true (order is unchanged, only membership is filtered); `Endpoint Drift Guard`, `Profile Builder Decoupling`, `Manifest Derivation and Purity` and `Entity Content` are **untouched** (DD164/DD165). No other requirement in either spec asserts that `crud` does not filter.

## Testing Strategy (Strict TDD — each row RED → GREEN)

| Layer | What | Where |
|---|---|---|
| Unit | Every DD161 row, parametrized `(crud, read_only, expected)` | `relational_mapping/tests/test_profile.py` |
| Unit | Determinism/order independence: `(DELETE, CREATE, READ)` ≡ canonical; two calls equal; `type(name) is str` | same |
| Unit | `OPERATION_NAMES` equals the controller declaration order | same |
| Unit | `Table(profile=None).effective_operations == OPERATION_NAMES`; property is not a dataclass field (equality/`repr` unchanged; `Table` is unhashable, dict-typed field) | `relational_mapping/tests/test_schema.py` |
| Integration | Invert `test_declaring_crud_does_not_filter_the_operations` (`test_manifest.py:282`) → `test_declaring_crud_restricts_the_operations` | `domain_manifest/tests/test_manifest.py` |
| Integration | Empty effective set (`crud=()`, and `read_only=True, crud=(CREATE,)`) → `operations == []` **and** `resourcePath is None` | same |
| Integration | `read_only=True` keeps only `findById, list, count` with `/api/purchases` paths | same |
| Integration | Undeclared (`TableProfile(auditable=True)`) still yields the six ordered rows | same |
| Anti-drift | `tuple(name for name, *_ in _OPERATIONS) == OPERATION_NAMES` (tests may import both; only `builder/**` is guarded) | same |
| Backward compat | Byte identity for the undeclared case is pinned by the **unedited** tripwires `test_sample_entity_header`, `test_operations_exist_exactly_when_the_entity_has_a_controller`, `test_attributes.py::test_sample_attribute`, `test_determinism.py`, `test_cli.py`, plus `docs/domain-manifest.json` | existing |
| Guard | `tests/test_builder_decoupling.py` passes with **zero edits** | existing |

**Mutation-check candidates**: M1 drop the `read_only` intersection; M2 treat `crud == ()` as undeclared (return all six); M3 iterate `names` instead of `_OPERATIONS` (order mutant); M4 keep `resource_path` when `operations` is empty; M5 drop the `if name in names` filter.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. Pure in-process derivation over an in-memory model.

## Migration / Rollout

No migration. No schema-version bump (`schemaVersion` stays `1`: no key is renamed, removed or retyped — `resourcePath` was already nullable). Rollout is the two-slice chain of the proposal; revert order is slice 2 then slice 1.

## Open Questions

None. D1/D2/D3 are confirmed and DD162 removes the proposal's only open design item (the call site).
