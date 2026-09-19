# Session — Spring generator inheritance apply

Date: 2026-09-19

## Goal

Implement SDD change `2026-09-19-spring-boot-generator-inheritance` as one explicitly accepted `size:exception` PR slice.

## Scope implemented

- Added typed malformed-inheritance validation for discriminator-backed `Table` inputs.
- Added inheritance hierarchy context construction and ownership-based field partitioning.
- Added JPA Single Table root/subclass entity rendering plus exactly one root repository.
- Preserved byte-identical six-file output for non-discriminator tables through a SHA-256 snapshot regression.

## Boundaries preserved

- No inheritance DTOs, services, controllers, or subclass repositories.
- No Java compilation tooling.
- No config, OpenAPI, Postman, Domain Manifest, frontend, mobile, or infrastructure changes.
- Discriminator columns render only as JPA metadata, not normal Java fields.

## Evidence

- `docker compose exec -T backend pytest apps/spring_generator/tests/test_rejections.py -q` → 19 passed.
- `docker compose exec -T backend pytest apps/spring_generator/tests/test_inheritance_context.py apps/spring_generator/tests/test_rejections.py apps/spring_generator/tests/test_no_concat_guard.py -q` → 26 passed.
- `docker compose exec -T backend pytest apps/spring_generator/tests/test_inheritance_rendering.py apps/spring_generator/tests/test_inheritance_context.py apps/spring_generator/tests/test_rejections.py apps/spring_generator/tests/test_no_concat_guard.py -q` → 33 passed.
- `docker compose exec -T backend pytest apps/spring_generator/tests/test_inheritance_backward_compatibility.py apps/spring_generator/tests/test_determinism.py -q` → 9 passed.
- `docker compose exec -T backend pytest apps/spring_generator/tests -q` → 208 passed.
- `docker compose exec -T backend pytest -q` → 655 passed.

## Relevant files

- `backend/apps/spring_generator/emit/errors.py`
- `backend/apps/spring_generator/emit/inheritance_context.py`
- `backend/apps/spring_generator/emit/renderer.py`
- `backend/apps/spring_generator/emit/templates/InheritanceEntity.java.j2`
- `backend/apps/spring_generator/tests/test_rejections.py`
- `backend/apps/spring_generator/tests/test_inheritance_context.py`
- `backend/apps/spring_generator/tests/test_inheritance_rendering.py`
- `backend/apps/spring_generator/tests/test_inheritance_backward_compatibility.py`
- `openspec/changes/2026-09-19-spring-boot-generator-inheritance/tasks.md`
- `openspec/changes/2026-09-19-spring-boot-generator-inheritance/apply-progress.md`
