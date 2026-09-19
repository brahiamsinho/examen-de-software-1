# Proposal: Relational column ownership metadata

## Intent

Add relational metadata so columns generated from UML attributes preserve the identity of the UML class that originally owns the attribute. This is a relational-mapping-first change: it prepares the `RelationalModel` for a later, safer Spring inheritance-generation cycle without enabling Java inheritance generation now.

Today, `backend/apps/relational_mapping/mapping/mapper.py` maps UML generalization with Single Table inheritance: descendant attributes are merged into the root table and made nullable. `Column` already records `source_element_id`, but `backend/apps/relational_mapping/domain/schema.py` does not record which UML class owned that attribute. That makes future generator logic unable to distinguish root-owned fields from subclass-owned fields when a Single Table contains attributes from multiple UML classes.

## Scope

### In Scope

- Extend `backend/apps/relational_mapping/domain/schema.py::Column` with `owning_class_id: ElementId | None`.
- Populate `owning_class_id` only for columns created from UML attributes.
- Thread the owning UML class id through `backend/apps/relational_mapping/mapping/mapper.py` when mapping root and descendant attributes into table columns.
- Add or update mapper/domain tests documenting:
  - root attribute columns carry the root UML class id;
  - subclass attribute columns carry the subclass UML class id even when merged into the root Single Table;
  - non-attribute columns keep `owning_class_id is None`.
- Preserve the existing Spring generator inheritance rejection behavior.

### Out of Scope

- Generating Java inheritance classes or changing `spring_generator` to support discriminator-backed tables.
- Removing or weakening `InheritanceUnsupportedError` / discriminator rejection in `backend/apps/spring_generator`.
- Changing generated DTO, service, controller, repository, or REST behavior.
- Whole-model generator orchestration.
- Generated `config/` layer.
- OpenAPI, Postman, Domain Manifest, frontend generation, or mobile generation.

## User decision encoded

`owning_class_id` applies only to columns generated from UML attributes.

The following columns keep `owning_class_id = None` in this cycle:

- synthetic `id` columns;
- Single Table discriminator `class_type` columns;
- relationship foreign-key columns;
- many-to-many join-table columns.

## Affected Areas

| Area | Impact | Notes |
|---|---|---|
| `backend/apps/relational_mapping/domain/schema.py` | Modified | Add optional ownership metadata to `Column`. |
| `backend/apps/relational_mapping/mapping/mapper.py` | Modified | Pass the current UML class id when converting attributes to columns. |
| `backend/apps/relational_mapping/tests/` | Modified | Add ownership and `None` semantics coverage. |
| `backend/apps/spring_generator/` | Guarded unchanged | Existing discriminator/inheritance rejection remains the active behavior. |

## Approach

1. Add `owning_class_id: ElementId | None = None` to the frozen `Column` dataclass, defaulting to `None` to keep existing column construction call sites low-risk.
2. Update `_map_attribute_column(...)` to accept the owning class id and set it on every returned attribute-derived `Column`.
3. In `_map_table_for_root(...)`, pass the `class_id` currently being iterated over, so root and descendant attributes preserve their original UML class ownership after Single Table flattening.
4. Leave all non-attribute column constructors unchanged so their default `None` ownership documents the current cycle boundary.
5. Add focused tests before implementation where possible:
   - one Single Table hierarchy test proving root/subclass ownership on attribute columns;
   - one test proving synthetic id and discriminator columns have `None` ownership;
   - one relationship/join-table test proving FK and join-table columns have `None` ownership;
   - one Spring generator regression test or existing assertion confirming discriminator tables are still rejected.

## Risks

| Risk | Likelihood | Mitigation |
|---|---:|---|
| Future developers may infer generator inheritance is now supported. | Medium | Proposal and tests explicitly keep Spring discriminator rejection unchanged. |
| Column factories/tests may need default updates. | Low | Default `None` keeps most existing constructors compatible. |
| Ambiguity between `source_element_id` and `owning_class_id`. | Medium | Tests document that `source_element_id` identifies the UML attribute, while `owning_class_id` identifies the UML class that owns that attribute. |
| Metadata could be accidentally set on relationship-generated columns. | Medium | Add explicit `None` tests for FK and join-table columns. |

## Rollback Plan

Revert the `Column.owning_class_id` field, mapper threading, and related tests. No database migrations, persisted data, Java output, API contracts, or frontend behavior are affected because `relational_mapping` remains a pure in-memory mapping module.

## Success Criteria

- [ ] Attribute-derived relational columns expose both `source_element_id` and `owning_class_id`.
- [ ] In a Single Table hierarchy, root attribute columns point to the root UML class id and subclass attribute columns point to the subclass UML class id.
- [ ] Synthetic `id`, discriminator `class_type`, relationship FK columns, and join-table columns all keep `owning_class_id is None`.
- [ ] `spring_generator` still rejects discriminator/inheritance tables via `InheritanceUnsupportedError`.
- [ ] Backend pytest remains green from the parent baseline of `631 passed`.

## Non-goal confirmation

This proposal intentionally stops at relational metadata. A later generator-design cycle must decide how Java inheritance classes, discriminator values, DTO shape, services, repositories, and compilation verification should work. This cycle only preserves the missing ownership fact needed to make that future decision safe.
