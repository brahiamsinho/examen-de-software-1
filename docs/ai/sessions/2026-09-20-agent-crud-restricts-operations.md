# Session 2026-09-20 — agent — crud restricts operations (manifest slice)

Change: `crud-restricts-operations` (slice 1 of 2; DD160-DD167). Status: verified (PASS WITH WARNINGS, 0 critical) and archived, uncommitted; archived to `openspec/changes/archive/2026-09-20-crud-restricts-operations/`. Last commit at the time: `20bf71c feat(spring-generator): add filtering/search, sort validation and defaultSort`.

## What was done

- New pure `effective_operations(profile)` plus `OPERATION_NAMES` in `backend/apps/relational_mapping/domain/profile.py` (DD160/DD161 truth table).
- New non-field `Table.effective_operations` property in `domain/schema.py` (DD162), so `apps/domain_manifest` reads it duck-typed and `tests/test_builder_decoupling.py` stays unedited.
- `apps/domain_manifest/builder/entities.py` filters `_OPERATIONS` in declared order and nulls `resourcePath` when the effective set is empty, after computing the segment (DD163/DD164).
- Strict TDD, RED first for each phase; backend 1214 -> 1267 passed (`apps/relational_mapping` 170, `apps/domain_manifest` 146, 24/24 tasks, ~570 authored lines, no `size:exception`); mutations M1-M5 killed and reverted byte-identical.
- Docs: DD160-DD167 in `DECISIONS_LOG.md` (parity with `design.md`), DD147 annotated as retired in place, stale "uncommitted / verify pending" lines for the three committed changes fixed.

## Things to remember

- The manifest and the generator diverge for restricted models until slice 2 `spring-generator-crud-restriction` (DD166); nothing committed uses a restricted model.
- Mutation M3 (iterate `names`) is equivalent through `build_entity`; a direct `_operations` order test kills it.
- Task 9.1 closed at archive: the delta spec wording was corrected (`Table` is unhashable, so equal tables compare `==` with equal fields and `repr` rather than "hash equal"), `generation-profile` went 9 -> 10 requirements and `domain-manifest-export` stayed at 15 (rename + 3 modified). Accepted warnings: M3 equivalent mutant covered by a direct test; no safety-net column in apply-progress; private `_OPERATIONS` / `_operations` imported by tests.
- Untouched: `apps/spring_generator`, `frontend/`, `docker-compose.yml`, `scripts/`, `apps/uml_*`, `.pi/`.

## Next

Slice 2 `spring-generator-crud-restriction`: gate the Spring controller/service/imports with the same `effective_operations`, no controller/service when the set is empty, undeclared output byte-identical. Then inheritance API, relation navigation endpoints, Undo/Redo + Presence verification, Flutter.
