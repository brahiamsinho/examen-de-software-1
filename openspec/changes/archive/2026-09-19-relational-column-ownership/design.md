# Technical Design: Relational Column Ownership

This change adds class-ownership metadata to relational columns generated from UML attributes. It keeps the change in `relational_mapping`, preserves frozen deterministic output, and explicitly does not enable Spring inheritance generation.

## Goals

- Add `Column.owning_class_id: ElementId | None = None` to the relational domain model.
- Set `owning_class_id` only on columns derived from `UmlAttribute`.
- Preserve `source_element_id` as the UML attribute id.
- Keep synthetic, discriminator, relationship FK, and join-table columns ownership-free.
- Keep Spring generator discriminator-table rejection unchanged.

## Non-goals

- No Java inheritance generation.
- No change to Spring emit templates.
- No change to DTO, entity, repository, service, controller, or REST generation semantics.
- No database migration or persisted-data change; this is in-memory metadata only.

## Current Architecture

`backend/apps/relational_mapping/mapping/mapper.py` maps a `CanonicalUmlModel` into frozen dataclasses from `backend/apps/relational_mapping/domain/schema.py`.

The mapper pipeline is deterministic and order-preserving:

1. validate dangling relationship endpoints defensively;
2. build hierarchy roots/descendants/parents;
3. map enumerations;
4. map each hierarchy root to a table draft;
5. map relationships into FK columns or join tables;
6. freeze drafts into immutable `Table` and `RelationalModel` values.

Single Table inheritance is already represented by merging descendant attributes into the root table and adding `class_type`. The missing fact is which UML class originally owned each merged attribute column.

## Design Decisions

| ID | Decision | Rationale |
|---|---|---|
| DD1 | Add `owning_class_id` to `Column` after `source_element_id`, defaulting to `None`. | Keeps existing constructors compatible and preserves frozen dataclass usage. |
| DD2 | Treat `source_element_id` and `owning_class_id` as separate facts. | `source_element_id` identifies the UML attribute; `owning_class_id` identifies the UML class that owns that attribute. |
| DD3 | Thread ownership through `_map_attribute_column(...)` with a required keyword-only `owning_class_id`. | Makes ownership explicit at the only mapper point that creates attribute-derived columns. |
| DD4 | Pass the iterated `class_id` from `_map_table_for_root(...)` into `_map_attribute_column(...)`. | Root and descendant attributes retain their original owner even after Single Table flattening. |
| DD5 | Leave non-attribute column constructors unchanged. | Their default `None` enforces the proposal boundary without extra branching. |
| DD6 | Do not touch `spring_generator/emit`. | The existing no-concat guard applies there, and this change only needs rejection regression coverage. |

## Data Model Contract

Update `backend/apps/relational_mapping/domain/schema.py`:

```python
@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType
    nullable: bool = False
    length: int | None = None
    precision: int | None = None
    scale: int | None = None
    enum_type_name: str | None = None
    source_element_id: ElementId | None = None
    owning_class_id: ElementId | None = None
```

Contract rules:

- Attribute-derived columns: `source_element_id == UmlAttribute.id` and `owning_class_id == UmlClass.id`.
- Synthetic `id`: `owning_class_id is None`.
- Single Table discriminator `class_type`: `owning_class_id is None`.
- Relationship FK columns: `owning_class_id is None`.
- Many-to-many join-table columns, including join-table `id`: `owning_class_id is None`.

## Mapper Data Flow

### Attribute columns

Change `_map_attribute_column(...)` to accept ownership explicitly:

```python
def _map_attribute_column(
    attribute: UmlAttribute,
    *,
    nullable: bool,
    owner_class_name: str,
    owning_class_id: ElementId,
    enum_type_name_by_id: dict[ElementId, str],
    taken_names: set[str],
) -> Column:
```

Every `Column(...)` returned from this function sets:

```python
source_element_id=attribute.id,
owning_class_id=owning_class_id,
```

This applies to primitive and enumeration attributes.

### Single Table flattening

In `_map_table_for_root(...)`, `tree_class_ids` already iterates root first, then descendants in deterministic breadth-first order. The mapper should pass the current `class_id`:

```python
for index, class_id in enumerate(tree_class_ids):
    uml_class = class_by_id[class_id]
    nullable = index != 0
    for attribute in uml_class.attributes:
        column = _map_attribute_column(
            attribute,
            nullable=nullable,
            owner_class_name=uml_class.name,
            owning_class_id=class_id,
            enum_type_name_by_id=enum_type_name_by_id,
            taken_names=draft.column_names,
        )
```

Result: a subclass attribute merged into the root table still records the subclass id.

### Non-attribute columns

No ownership argument is passed when constructing:

- `_map_table_for_root(...)` synthetic `id`;
- `_map_table_for_root(...)` `class_type` discriminator;
- `_add_simple_fk(...)` relationship FK columns;
- `_build_join_table(...)` join-table `id` and FK columns.

The `Column` default keeps these values as `None`.

## Spring Generator Boundary

The Spring generator remains unchanged in production code unless an existing factory needs to accept the new optional field for test setup.

The important regression is `backend/apps/spring_generator/emit/errors.py::reject_out_of_scope(...)` behavior:

- a `Table` with `discriminator_column` still raises `InheritanceUnsupportedError`;
- adding a column with `owning_class_id` does not make the table generatable;
- no Java inheritance source is emitted.

Do not modify files under `backend/apps/spring_generator/emit/` for this change. The existing `test_no_concat_guard.py` should continue to pass without new exceptions or template edits.

## File Change Plan

| File | Change |
|---|---|
| `backend/apps/relational_mapping/domain/schema.py` | Add `Column.owning_class_id` defaulting to `None`. |
| `backend/apps/relational_mapping/mapping/mapper.py` | Thread owner class id through attribute-column creation only. |
| `backend/apps/relational_mapping/tests/test_schema.py` | Assert the new column default is `None`. |
| `backend/apps/relational_mapping/tests/test_map_attributes.py` | Assert root attribute ownership and enum/primitive behavior as needed. |
| `backend/apps/relational_mapping/tests/test_map_inheritance.py` | Assert subclass attribute ownership after Single Table flattening; assert `id` and `class_type` remain `None`. |
| `backend/apps/relational_mapping/tests/test_map_relationships.py` | Assert simple FK and join-table columns remain `None`. |
| `backend/apps/spring_generator/tests/factories.py` | Optional: add `source_element_id`/`owning_class_id` parameters to `a_column` only if it reduces test noise. |
| `backend/apps/spring_generator/tests/test_rejections.py` | Add or extend discriminator rejection test with an attribute-derived owned column. |

## Test Plan

Run focused tests first during implementation:

```bash
docker compose exec -T backend pytest -q \
  backend/apps/relational_mapping/tests/test_schema.py \
  backend/apps/relational_mapping/tests/test_map_attributes.py \
  backend/apps/relational_mapping/tests/test_map_inheritance.py \
  backend/apps/relational_mapping/tests/test_map_relationships.py \
  backend/apps/spring_generator/tests/test_rejections.py
```

Then run the strict backend gate:

```bash
docker compose exec -T backend pytest -q
```

Acceptance checks:

- root attribute column has `owning_class_id == root.id`;
- subclass attribute column flattened into root table has `owning_class_id == subclass.id`;
- `source_element_id` remains the attribute id;
- `id`, `class_type`, simple FK, join-table `id`, and join-table FK columns have `owning_class_id is None`;
- discriminator-backed tables still raise `InheritanceUnsupportedError` in Spring generator tests.

## Rollout and Rollback

Rollout is a pure in-memory domain/model change. No migration, generated API contract, generated Java source contract, or runtime deployment step is required.

Rollback is safe by reverting:

1. the `Column.owning_class_id` field;
2. mapper ownership threading;
3. ownership-specific tests.

Because no persisted data or emitted Spring templates change, rollback has no data migration impact.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Developers assume Spring inheritance generation is now supported. | Medium | Keep Spring discriminator rejection tests explicit. |
| Ownership accidentally appears on FK or join-table columns. | Medium | Add direct `None` assertions for relationship-generated columns. |
| Confusion between `source_element_id` and `owning_class_id`. | Medium | Test both values on the same attribute-derived column. |
| Frozen dataclass call sites break. | Low | Use a default value and keyword additions only. |
| Deterministic output changes unexpectedly. | Low | Reuse existing order-preserving loops; add metadata without reordering collections. |
