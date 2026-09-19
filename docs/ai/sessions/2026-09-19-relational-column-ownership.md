# Session — Relational column ownership

Date: 2026-09-19

## Summary

Completed and archived SDD change `relational-column-ownership`.

## What changed

- Added `Column.owning_class_id: ElementId | None = None` in `backend/apps/relational_mapping/domain/schema.py`.
- Updated the relational mapper so only UML attribute-derived columns receive their owning UML class id.
- Preserved `owning_class_id is None` for synthetic id, discriminator, relationship FK, and join-table columns.
- Kept Spring generator inheritance/discriminator rejection active; no Java inheritance generation was enabled.
- Composed OpenSpec requirements into:
  - `openspec/specs/relational-mapping/spec.md`
  - `openspec/specs/spring-boot-generation/spec.md`
- Archived the change at `openspec/changes/archive/2026-09-19-relational-column-ownership/`.

## Verification

- Focused suite: `44 passed`.
- Full backend suite: `636 passed`.
- Django check: `System check identified no issues`.
- Native SDD status: `archived`.

## Notes

Verification initially found a weak assertion using `all(...)` over join-table columns. It was fixed by first asserting the exact join-table column names, then checking each concrete column's ownership metadata.

## Next

The inheritance metadata prerequisite is done. Next inheritance work should be a separate SDD cycle to design and implement actual Spring inheritance generation while preserving the current rejection until the design lands.
