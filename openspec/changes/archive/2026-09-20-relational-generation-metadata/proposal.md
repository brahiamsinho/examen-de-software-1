# Proposal: Carry Generation Profile Metadata Through Relational Mapping

## Intent

Spec §33 defines a generation profile (`entity, auditable, readOnly, searchable, crud, sortable, defaultSort`) that should drive the Domain Manifest and the generated Spring API. Today `CanonicalUmlModel.generation_metadata` is an unvalidated opaque container that `map_to_relational` never reads, so the information dies at the mapper boundary. DD131 blocked the manifest from emitting these fields because an invented default is indistinguishable from real author intent. This change makes the mapper the first typed carrier: declared profile intent reaches `RelationalModel`, and undeclared stays provably undeclared (`None`), unblocking the manifest slice and the filtering/search slice without guessing.

## Scope

### In Scope

- Frozen, hashable `ColumnProfile` / `TableProfile` value objects in `relational_mapping/domain/`.
- Optional `Column.profile` and `Table.profile`, default `None` (= undeclared).
- Strict parser reading the reserved `"profile"` key of each `generation_metadata[element_id]` entry, with a typed mapper error.
- Mapper wiring: class profile at `_freeze_table` (STI root class only), attribute profile at `_map_attribute_column`.
- Tests for parse, precedence, determinism, and unchanged existing behaviour.

### Out of Scope

- Domain Manifest emission of profile fields (slice 2).
- Spring filtering/search/sorting generation (slice 3).
- Authoring path: commands, schemas, API, UI. Backend carry-through only.
- `required` / `unique` keys — deferred, they overlap derived nullability and `UniqueConstraint`.
- `entity: false` semantics — deferred, it would change generated output.
- Provenance keys already present in fixtures (`source`, `confidence`) stay ignored, not migrated.

## Capabilities

### New Capabilities

- `generation-profile`: the §33 profile vocabulary carried into generation — key set, value types, `None`-means-undeclared semantics, reserved `"profile"` namespace, and strict-parse failure rules.

### Modified Capabilities

- `relational-mapping`: `Column` and `Table` gain an optional `profile`; `map_to_relational` reads `generation_metadata`, applies table-level profile from the STI root class, and raises on malformed profile data.

## Approach

Option A from exploration (typed optional value objects), chosen over opaque passthrough (B — defers validation, breaks hashing, leaks provenance keys) and a sidecar resolver (C — does not carry metadata through the mapper and forces two inputs per consumer).

Resolved decisions recorded here:

| Decision | Resolution |
|---|---|
| `defaultSort` shape | Table-level, single `{attribute, direction}` with `direction ∈ {asc, desc}` |
| `crud` shape | Table-level, subset of `{create, read, update, delete}` |
| `required` / `unique` | Deferred |
| Authoring scope | Backend carry-through only |
| Parsing | Strict: unknown key or ill-typed value inside `profile` raises a typed error; keys outside `profile` ignored; unknown element ids ignored |
| `entity: false` | Deferred |
| STI | Table profile comes from the root class only; subclass entries are attribute-level or ignored |
| Synthetic columns | `id`, discriminator, FK and join-table columns always carry `profile=None` |

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/relational_mapping/domain/schema.py` | Modified | Add `profile` field to `Column` and `Table`, default `None` |
| `backend/apps/relational_mapping/domain/profile.py` | New | `ColumnProfile`, `TableProfile` frozen value objects |
| `backend/apps/relational_mapping/mapping/profile_parser.py` | New | Strict parse of the reserved `"profile"` key + typed error |
| `backend/apps/relational_mapping/mapping/mapper.py` | Modified | Wire parser into `_map_attribute_column` and `_freeze_table` |
| `backend/apps/relational_mapping/tests/` | Modified | New profile tests; `test_schema.py` default assertions |
| `backend/apps/uml_modeling/domain/model.py` | Unchanged | Container shape and `uml-domain-model` spec stay as-is |
| `domain_manifest/`, `spring_generator/` | Unchanged | No consumer reads `profile` in this change |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Oracle or manifest output drifts | Low | Consumers read named attributes only; goldens must stay byte-identical, asserted in tests |
| Hashability/equality regression on frozen dataclasses | Medium | Profiles are frozen and hashable; add explicit hash/equality tests |
| Reviewer reads value types as schema invention | Medium | §33 fixes the key set; value types are documented as this project's own profile in the spec delta |
| Blast radius across 178 construction sites in 30 test files | Medium | New fields default to `None`; no call site is required to change |
| Feature is unusable without an authoring path | Medium | Accepted: slice 1 is enabling work, tested with hand-built `generation_metadata` |

## Rollback Plan

Single PR, additive only. Revert the merge commit: `profile` fields, the profile module and parser disappear, mapper returns to ignoring `generation_metadata`. No data migration, no persisted state, no consumer depends on the new fields, so revert leaves the oracle and the manifest untouched.

## Dependencies

- None external. Slices 2 (manifest fields) and 3 (Spring filtering/search) depend on this change, not the reverse.

## Success Criteria

- [ ] A declared profile in `generation_metadata` is readable on the mapped `Table` / `Column`.
- [ ] Undeclared elements produce `profile=None`; synthetic columns always `None`.
- [ ] Malformed profile data raises a typed mapper error naming the offending element and key.
- [ ] Mapping stays deterministic: repeated mapping of the same model is equal, with equal hashes for columns and table profiles (`Table` was already unhashable).
- [ ] The 41-file Spring oracle and the Domain Manifest output remain byte-identical.
- [ ] Full backend test suite green; Strict TDD followed (failing test before each implementation step).

## Size Estimate

~300–350 authored lines (profiles + parser + error ~70, mapper wiring ~30, tests ~200–250). Within the 800-line review budget; single PR.
