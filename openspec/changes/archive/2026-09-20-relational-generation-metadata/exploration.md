# Exploration: relational-generation-metadata

Read-only exploration. Goal: make the UML -> RelationalModel mapper carry the spec §33 `generation_metadata` so that later changes can enrich the Domain Manifest (DD131 follow-up) and add filtering/search to the generated Spring API.

## 1. Current state of `generation_metadata`

- `backend/apps/uml_modeling/domain/model.py:11-23`: `CanonicalUmlModel` (frozen) has `generation_metadata: Mapping[ElementId, Mapping[str, object]]`, documented as an opaque container keyed by element id. The spec (`openspec/specs/uml-domain-model/spec.md:69-76`) and `tests/test_model.py:80-90` pin that UML elements never gain a metadata field.
- No validation exists: no key rules, no value types, no dangling-id checks. `uml_documents/schemas.py:124` is a raw `dict` passthrough; `codec.py:80/89` is a verbatim JSON round-trip. No command touches it and no UI or API authors it, so real documents carry `{}`.
- The only non-empty fixture (`uml_documents/tests/factories.py:75-78`) holds input-channel provenance (`source`, `confidence`) keyed by class id. That is provenance, not the §33 profile.
- Spec §33 (`product-04-next-django.md:1008-1033`) names the profile concepts `entity, auditable, readOnly, searchable, crud, required, unique, sortable, defaultSort` without value types, and requires documenting UML vs own profile. `aliases` is not in §33.
- DD131 (`docs/ai/DECISIONS_LOG.md:17`): the manifest emits none of these because a default would be indistinguishable from real intent; the mapper must carry the metadata first. `domain_manifest/tests/test_manifest.py:71` pins `EXCLUDED_KEYS`.

## 2. Mapper and blast radius

- `relational_mapping/mapping/mapper.py:520-556` `map_to_relational` never reads `generation_metadata`. Attachment points: `_map_attribute_column` (`:205-238`, has `source_element_id` and `owning_class_id`) for attribute-level data, `_freeze_table` (`:505-517`) for class-level data. Synthetic columns (`id`, `class_type`, FK, join table) get no metadata.
- `Column`, `Table`, `RelationalModel` (`relational_mapping/domain/schema.py`) are frozen dataclasses with structural equality. A `Mapping` field on `Column` would break hashing; prefer hashable value objects.
- Only production caller: `generation_runner/samples/sample_model.py:124`, which never passes metadata. There is no production path from a stored document to generation yet.
- Blast radius if new fields default to `None`: 30 test files construct `Column/Table/RelationalModel` (178 occurrences); `test_schema.py:50-58, 94-106` pin defaults individually (add new default assertions). Spring and manifest consumers read named attributes only. The manifest builder must not import `relational_mapping` (AST guard) and duck-types tables/columns.

## 3. Options

- **A (recommended):** typed optional `ColumnProfile` / `TableProfile` frozen value objects, `Column.profile` and `Table.profile` default `None` (None = undeclared), parsed strictly by the mapper from a reserved `"profile"` key in the per-element mapping. Additive, hashable, deterministic; oracle and manifest stay byte-identical when nothing is declared.
- **B:** opaque passthrough `metadata` mapping. Tiny but defers validation to consumers, leaks provenance keys, breaks hashing.
- **C:** sidecar `resolve_profile(model, relational)` leaving `RelationalModel` untouched. Zero blast radius but does not literally carry metadata through the mapper and forces two inputs per consumer.

## 4. Risks and open questions

- STI: a table covers several classes; table-level flags come from the root class only.
- `required` / `unique` overlap with derived nullability and `UniqueConstraint` (precedence needed).
- No authoring path exists; value is testable only with hand-built JSON.
- §33 gives no value types (shape of `defaultSort`, `crud`): reviewer may see it as schema invention.
- Open decisions: (1) shape of `defaultSort` and `crud`; (2) include `required`/`unique`?; (3) authoring scope; (4) strict vs lenient parsing; (5) `entity: false` semantics.

## 5. Size

Slice 1 (this change): ~300-350 authored lines (profiles + parser + error ~70, mapper wiring ~30, tests ~200-250). Slice 2 (manifest fields) ~150-250; slice 3 (Spring filtering/search) has its own budget. Keep three separate changes.

## Orchestrator resolution of open questions (defaults, to be recorded in the proposal)

1. `defaultSort`: single `{attribute, direction}` (asc|desc), table-level; `crud`: per-operation subset of create/read/update/delete, table-level.
2. `required` and `unique` deferred (they overlap with derived facts).
3. Backend carry-through only; authoring in commands/UI is a separate later change.
4. Strict parsing: unknown keys or ill-typed values inside `profile` raise a typed mapper error; keys outside `profile` are ignored; unknown element ids are ignored.
5. `entity: false` deferred (it would change generated output).
