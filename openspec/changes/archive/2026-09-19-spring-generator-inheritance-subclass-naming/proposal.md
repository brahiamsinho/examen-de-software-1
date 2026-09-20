# Proposal: Inheritance Subclass Java Class Naming

## Intent

Every hierarchy subclass Java class name is derived from the UML **element id** instead of the UML **class name**. Real ids come from `new_id()` (uuid4 hex; ~10 of 16 start with a digit), so `pascal_case` raises `InvalidJavaIdentifierError` and `generate_model_sources` / `generate_project_sources` fail for **any** real model containing inheritance. Success: a hierarchy whose class ids are real uuids generates `Car.java` from UML class `Car`.

## Evidence

| Fact | Location |
|---|---|
| Subclass name read from the id | `backend/apps/spring_generator/emit/inheritance_context.py:169` — `class_name=pascal_case(class_id)` |
| Correct source is the UML class name | `backend/apps/relational_mapping/mapping/mapper.py:275` — `discriminator_values[class_id] = class_by_id[class_id].name` |
| Root naming (stays unchanged) | `inheritance_context.py:137` — `pascal_case(table.name)` |
| Identifier guard that rejects digit-leading ids | `backend/apps/spring_generator/emit/naming.py:52-65` |
| Defect hidden by readable fixture ids | `tests/test_inheritance_rendering.py:20`, `tests/test_model_sources.py:48`, `tests/test_project_sources.py:37` (`vehicle/car/truck` → `VEHICLE/CAR/TRUCK`) |
| Documented workaround to remove | `backend/apps/generation_runner/samples/sample_model.py:7-13`, `:75-77` |
| Spec couples the id to the file name | `openspec/specs/spring-boot-generation/spec.md:399`, `:415-426`, `:455` |
| SHA-256 snapshot guards the **non-discriminator** `product` table only | `tests/test_inheritance_backward_compatibility.py:32-62` → **no snapshot regeneration needed** |

## Scope

### In Scope

- `inheritance_context.py:169` → `class_name=pascal_case(table.discriminator_values[class_id])`.
- Failing-first regression test: inheritance hierarchy with `new_id()` uuid ids driven through `generate_project_sources`.
- Realign inheritance fixture discriminator values to UML class names (`Vehicle`/`Car`/`Truck`) so emitted files stay `Vehicle.java`/`Car.java`/`Truck.java`.
- Delta spec for the affected scenarios.
- `sample_model.py`: restore `new_id()`-style ids, drop the workaround docstring — the compile gate becomes the regression guard.
- `docs/ai/` continuity updates.

### Out of Scope

- Inheritance DTOs / services / controllers / subclass repositories.
- Subclass name-collision handling.
- **Known limitation (possible follow-up, not scoped):** a UML class name that is not a valid Java identifier after `pascal_case` (e.g. `"Sports Car"`) keeps raising the existing typed `InvalidJavaIdentifierError`. No new sanitizing behavior.
- Relational mapper changes; generated-project boot smoke test (slice 3).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `spring-boot-generation` — two requirements:
  - *Discriminator-Backed Single Table Domain Generation* (`spec.md:390`): add the explicit rule that a subclass entity Java class name is `pascal_case` of that class id's discriminator value (the verbatim UML class name), never the class id.
  - *Root and Subclass JPA Inheritance Annotations* (`spec.md:409`): scenarios at `:415-426` restated with discriminator values `Vehicle` / `Car` instead of `VEHICLE` / `CAR`, so `Car.java` remains `Car.java` and `@DiscriminatorValue` stays verbatim.

## Approach

One-line source change; the surrounding work is fixture and spec realignment, because the current fixtures encode `CAR` while asserting `Car.java` — a coupling only the readable ids made consistent. Discriminator values keep being emitted verbatim in `@DiscriminatorValue`; root entity naming is untouched. Strict TDD: uuid-id test first (red = `InvalidJavaIdentifierError`), then the fix, then fixture/spec realignment.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/spring_generator/emit/inheritance_context.py` | Modified | Line 169 — the whole behavioural fix |
| `backend/apps/spring_generator/tests/test_inheritance_context.py` | Modified | Fixture discriminator values → class names |
| `.../tests/test_inheritance_rendering.py`, `test_model_sources.py`, `test_project_sources.py` | Modified | Same realignment; assertions on `@DiscriminatorValue` literals |
| `.../tests/` (new test) | New | uuid-id hierarchy through `generate_project_sources` |
| `.../tests/test_inheritance_backward_compatibility.py` | Unchanged | Non-discriminator snapshot — must stay byte-identical |
| `backend/apps/generation_runner/samples/sample_model.py` | Modified | `new_id()` ids; workaround docstring removed |
| `backend/apps/generation_runner/tests/test_sample_model.py` | Modified | Drop the readable-id assertion/comment (`:88`) |
| `openspec/specs/spring-boot-generation/spec.md` | Modified (via delta) | `:390`, `:409-426` |
| `docs/ai/CURRENT_STATE.md`, `NEXT_STEPS.md`, `DECISIONS_LOG.md`, `HANDOFF_LATEST.md`, `sessions/` | Modified | Remove the known defect; record the decision |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Spec/fixture coupling: changing the source silently renames files to `CAR.java` | High | Realign fixture discriminator values **and** the spec delta in the same change; assert exact emitted paths |
| Snapshot churn | Low | Verified: the SHA-256 snapshot covers the non-discriminator `product` table only; **any** change to it means an unintended regression, not expected churn |
| Class names with spaces/punctuation now reach `pascal_case` | Medium | Explicitly out of scope; existing typed `InvalidJavaIdentifierError` still fires. Add a test pinning that behaviour so it is a documented contract, not a surprise |
| `sample_model.py` uuid switch destabilises the compile gate | Low | That is the point — it becomes the end-to-end regression guard; revert the sample independently if it flakes |

## Rollback Plan

Revert the single commit. The behavioural surface is one line in `inheritance_context.py`; fixtures, spec delta, sample model, and docs revert with it. No migration, no persisted state, no generated artifact checked into the repo.

## Dependencies

None. No new packages, no mapper changes, no infra.

## Success Criteria

- [ ] A hierarchy whose class ids are `new_id()` uuids generates successfully through `generate_project_sources`.
- [ ] Emitted subclass files are `Car.java` / `Truck.java`, derived from the UML class names.
- [ ] `@DiscriminatorValue` still emits the discriminator value verbatim.
- [ ] Root entity naming and the non-discriminator SHA-256 snapshot are byte-identical.
- [ ] `sample_model.py` uses `new_id()`-style ids and the compile gate passes.
- [ ] `backend` pytest suite green; the known defect is removed from `docs/ai/NEXT_STEPS.md`.

## Review Workload Forecast

Preliminary (authoritative forecast is owned by `sdd-tasks`):

- Source: ~1 line. Tests: ~60-90 lines (one new regression test plus fixture value edits). Spec delta: ~25 lines. Sample/docs: ~40 lines.
- Estimated total: **~150-200 changed lines**, well inside the 400-line budget.

```
Decision needed before apply: No
Chained PRs recommended: No
400-line budget risk: Low
```

Delivery: `single-pr`.
