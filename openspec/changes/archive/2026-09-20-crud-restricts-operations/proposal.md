# Proposal: CRUD Declaration Restricts Operations (Slice 1 — shared function + Domain Manifest)

## Intent

DD147 is recorded tech debt: `TableProfile.crud` and `TableProfile.read_only` are parsed, carried by the mapper and emitted in the manifest `profile` object, but **nothing consumes them**. The Domain Manifest lists six operations for every entity with a controller, and the Spring generator emits six endpoints, regardless of what the model declares. A user who authors "read only" in the generation-profile panel (`GenerationProfilePanel.tsx:56-60`, which maps tri-state false to `crud: []`) gets a full write API. Declared authoring intent must become generated behaviour.

This change is **slice 1 of two**, landing back to back:

| Slice | Change | Content |
|---|---|---|
| 1 (this) | `crud-restricts-operations` | Shared `effective_operations()` + Domain Manifest filtering + spec deltas |
| 2 (next) | `spring-generator-crud-restriction` | Controller/service gating, conditional imports, generated-project tests |

Slicing keeps each PR inside the 400-line review budget; both must land before a release so the manifest and the generator agree.

## Scope

### In Scope

- One pure function `effective_operations(profile) -> tuple[str, ...]` in `backend/apps/relational_mapping/domain/profile.py`, returning operation names in canonical controller order (`create, findById, update, delete, list, count`).
- Domain Manifest: `builder/entities.py` filters `operations[]` through that function, and sets `resourcePath` to `null` when the effective set is empty.
- Spec deltas for `generation-profile` (ADDED requirement) and `domain-manifest-export` (MODIFIED + replaced requirements).
- Tests: the inverted `test_declaring_crud_does_not_filter_the_operations`, new per-declaration cases, and a backward-compatibility test pinning byte-identical output when nothing is declared.
- `docs/ai/DECISIONS_LOG.md`: close DD147 for the manifest, record the transient divergence and the three confirmed decisions.

### Out of Scope

- **Spring generator gating** — controller/service templates, conditional imports, the 41-file oracle: slice 2.
- **Parser validation** — no rejection of `readOnly: true` combined with a write `crud` (D3: silent fail-closed intersection; rejecting would break panel-authored models, DD133 "never invent").
- **UI warnings** in the generation-profile panel; the frontend is unaffected by this change.
- Per-operation DTOs, new profile keys, and any authoring path (commands, schemas, API).
- Postman export: it derives from the springdoc document, so it follows the generator and needs no code change in either slice.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `generation-profile`: **ADDED** requirement — `effective_operations()` is the single pure derivation from `TableProfile` to the operation-name tuple (mapping, `readOnly` intersection, undeclared = all six, empty set, determinism). It lives in `domain/profile.py`, the capability's own home; the Purpose's "out of scope" list stays accurate because emission is still owned by the manifest capability.
- `domain-manifest-export`:
  - **MODIFIED** `CRUD Operations` — "exactly these six items" becomes "the effective operations, in this canonical order", keeping the six literal rows as the undeclared-profile case; the inheritance scenario (`operations[] == []`, `resourcePath is null`) is generalized to any empty effective set.
  - **MODIFIED/REPLACED** `CRUD Declaration Does Not Filter Operations` — this requirement asserts the exact opposite of the new behaviour. It is rewritten in place (same heading is misleading; sdd-spec SHOULD rename it to `CRUD Declaration Restricts Operations` via `RENAMED` + `MODIFIED`, so the DD147 tech-debt note is retired rather than silently dropped).
  - **Check during spec**: there is no standalone "`resourcePath` is null iff `operations[]` is empty" requirement today. The coupling lives in the `CRUD Operations` inheritance scenario plus `Entity Content` (line 39, which states `resourcePath` (`/api/<segment>`) with no null case) and the `Manifest Derivation and Purity` scenario at line 25. The delta MUST make the null case explicit in exactly one place and keep the other two consistent.
  - `Endpoint Drift Guard` and `Profile Emission Determinism and Sample Neutrality` are **unchanged**: the sample model declares no profile.

## Approach

Derivation table (D1/D2/D3 confirmed):

| Declared | Effective operations |
|---|---|
| `crud is None` and `read_only in (None, False)` | all six (`create, findById, update, delete, list, count`) |
| `Table.profile is None` or `TableProfile()` | all six (identical to above) |
| `crud` declared | `create`→`create`; `read`→`findById`, `list`, `count`; `update`→`update`; `delete`→`delete` |
| `read_only=True` | intersect: remove `create`, `update`, `delete` (D1) |
| `crud: []`, or `read_only=True` with `crud=[create]` | `()` — empty (D2) |
| `read_only=True` + write `crud` | silent intersection, no parse error (D3) |

An empty effective set means **no controller and no service at all** (D2), the same shape inheritance tables already have (DD126): entity + repository only, manifest `resourcePath: null` and `operations: []`. In slice 1 only the manifest side of that is implemented.

The function is pure, has no Django or `apps.*` import, and is consumed by both the manifest builder and (in slice 2) the Spring context builders, so the two cannot drift. Note the decoupling constraint: `builder/profile.py` MUST NOT import `apps.relational_mapping` (`Profile Builder Decoupling`, DD146). The manifest already receives mapped `Table` objects in `builder/entities.py`, which is outside that guarded module set — sdd-design MUST confirm `entities.py` is not covered by `tests/test_builder_decoupling.py`'s `builder/**` glob before choosing the call site; if it is, the alternative is to pass the effective tuple in from the caller instead of importing the function.

Strict TDD: each behaviour lands RED → GREEN, starting with the inversion of the existing tripwire test.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/apps/relational_mapping/domain/profile.py` | Modified | Add pure `effective_operations()` and the canonical operation-name constant |
| `backend/apps/domain_manifest/builder/entities.py` | Modified | `_OPERATIONS`/`_operations()` filtered by the effective set; `resourcePath` null when empty |
| `backend/apps/domain_manifest/tests/test_manifest.py` | Modified | Invert `test_declaring_crud_does_not_filter_the_operations`; keep `OPERATIONS` and the drift guard |
| `backend/apps/relational_mapping/tests/` | New | Unit tests for `effective_operations()` (table above, determinism, purity) |
| `openspec/specs/generation-profile/`, `openspec/specs/domain-manifest-export/` | Modified | Delta specs per Capabilities |
| `docs/ai/DECISIONS_LOG.md`, `docs/ai/CURRENT_STATE.md` | Modified | Close DD147 (manifest side), record the slice-2 dependency |
| `docs/domain-manifest.json`, `frontend/` | Unchanged | Sample declares no profile; frontend is not involved |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| **Transient manifest/generator divergence**: between slice 1 and slice 2 a profile-restricted model yields a manifest with fewer operations than the generator's still-six endpoints | High (by construction) | Land the two changes back to back; the `Endpoint Drift Guard` stays honest because it is derived from the **sample model, which declares no profile** — its path sets remain the same six per entity on both sides, so it neither passes falsely nor fails spuriously. The divergence is recorded in `DECISIONS_LOG.md` as a time-boxed, single-release debt, and slice 2 removes it. No committed fixture (`api-docs.json`, Postman, boot-smoke `Customer`) uses a restricted model. |
| **Behaviour change for existing models** that already declared `crud`/`readOnly` (previously ignored) — their manifests shrink | Medium | Intended and confirmed (D1/D2/D3). Undeclared profiles are byte-identical, pinned by a dedicated backward-compatibility test following the filtering/search precedent (`test_filtering_backward_compatibility.py`). |
| Exact-count requirements ("exactly these six items") elsewhere in the specs silently contradict the new behaviour | Medium | The Capabilities section names the three places to reconcile; sdd-spec MUST grep the specs for "six" before writing the delta. |
| Decoupling guard breaks if the effective-set import lands in a guarded `builder/**` module | Low | Call-site decision is an explicit sdd-design item (see Approach); fallback is caller-injection. |
| `resourcePath: null` surprises a downstream consumer | Low | The manifest already emits `null` for inheritance entities, so no consumer contract is new. |

## Rollback Plan

Single-commit revert. The change is additive plus one filter call:

1. `git revert <commit>` restores `_OPERATIONS`/`_operations(resource_path)` and the original tripwire test; `effective_operations()` disappears with it, and nothing else imports it while slice 2 is unlanded.
2. Re-run `cd backend && pytest` — the 41-file oracle, `docs/domain-manifest.json` and the drift guard are untouched by this slice, so a revert needs no golden regeneration and no gate run.
3. If slice 2 has already landed, revert slice 2 **first** (it depends on `effective_operations`).
4. Reopen DD147 in `docs/ai/DECISIONS_LOG.md`.

## Dependencies

- None external. Slice 2 (`spring-generator-crud-restriction`) depends on **this** change, not the reverse.
- Confirmed product decisions D1, D2, D3 (pre-proposal handoff) — no open questions for the spec phase.

## Success Criteria

- [ ] `effective_operations(profile)` exists in `relational_mapping/domain/profile.py`, is pure (no Django/`apps.*`/driver imports, per the existing import-purity scenario) and deterministic.
- [ ] Every row of the derivation table is covered by a passing test, including `readOnly=True` + write `crud` (silent intersection) and the two empty-set paths.
- [ ] Undeclared profile (`crud is None`, `read_only` in `(None, False)`, `Table.profile is None`, `TableProfile()`) produces a **byte-identical** manifest and a byte-identical `docs/domain-manifest.json`, with no expected value edited in `test_manifest.py::test_sample_entity_header`, `test_attributes.py::test_sample_attribute` or `test_determinism.py`.
- [ ] An empty effective set yields `operations: []` **and** `resourcePath: null` for that entity.
- [ ] `test_declaring_crud_does_not_filter_the_operations` is inverted and green; `tests/test_builder_decoupling.py` passes unchanged.
- [ ] Spec deltas exist for `generation-profile` and `domain-manifest-export`, and no surviving main-spec requirement still asserts that `crud` does not filter operations.
- [ ] `cd backend && pytest` is green offline; authored diff stays under the 400-line review budget.
- [ ] DD147 closed for the manifest in `docs/ai/DECISIONS_LOG.md`, with the slice-2 dependency and the transient divergence recorded.
