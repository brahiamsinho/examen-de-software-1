# Design: Inheritance Subclass Java Class Naming

## Technical Approach

One behavioural line in `inheritance_context.py` moves the subclass Java class name from the UML **element id** to the UML **class name**, which the mapper already stores verbatim in `Table.discriminator_values` (`mapper.py:275`). Everything else is realignment: fixtures currently encode screaming-snake discriminator values (`CAR`) that the mapper never produces, and readable ids (`car`) that made the defect invisible. Strict TDD: uuid-id RED test first.

## Architecture Decisions

### DD87 — Read the class name from `discriminator_values`, inline

| Option | Tradeoff | Decision |
|---|---|---|
| `class_name=pascal_case(table.discriminator_values[class_id])` inline at `:169` | 1 line; mirrors the root's `pascal_case(table.name)` shape two blocks above | **Chosen** |
| New `_subclass_class_name(table, class_id)` helper | A named indirection over one expression; no second caller | Rejected — premature |
| Carry the UML name on `Column.owning_class_name` / a new `Table` field | Schema change + mapper change; data already exists | Rejected — out of scope |

`discriminator_values` is guaranteed present for every generated hierarchy class id by the requirement at `spec.md:392`, so `[class_id]` (not `.get`) keeps a missing value a loud `KeyError` rather than a silent fallback.

### DD88 — Fixtures adopt verbatim UML class names as discriminator values

Fixtures move `VEHICLE/CAR/TRUCK/PICKUP_TRUCK` → `Vehicle/Car/Truck/PickupTruck`. This is not cosmetic: `mapper.py:275` assigns `class_by_id[class_id].name`, so the screaming-snake values were unreachable fixtures. Emitted file names stay `Car.java`/`Truck.java`; only `@DiscriminatorValue("CAR")` → `@DiscriminatorValue("Car")` assertions change.

### DD89 — Discriminating coverage lives in new tests, not in the old fixtures

With readable ids **and** class-name values, `pascal_case("car") == pascal_case("Car")` — the realigned fixtures still cannot tell id from value. Existing fixtures therefore keep readable ids (`owning_class_id="car"` stays legible) and separation is proven by three **new** RED tests (DD90) rather than by weakening or rewriting every fixture.

### DD90 — `sample_model.py` uses frozen uuid4-hex literals, not live `new_id()`

| Option | Tradeoff | Decision |
|---|---|---|
| Module-level uuid-hex **literal** constants, ≥1 digit-leading per hierarchy class | Deterministic across processes; guarantees the defect shape every run | **Chosen** |
| `new_id()` at import time | Same process determinism only; digit-leading is probabilistic → flaky gate evidence | Rejected |
| `new_id()` inside `build_sample_model()` | Breaks `build_sample_model() == build_sample_model()` (`test_sample_model.py:36`) | Rejected |

Only **class** ids change; attribute/relationship/enumeration ids stay readable (they never reach `pascal_case`). Post-fix, generated output is id-independent, so the 41-file count and byte-identity assertions hold unchanged.

### DD91 — The compile gate is the end-to-end regression evidence

`bash scripts/verify-generated-project.sh` is re-run after the sample-model switch. With uuid class ids it now exercises the exact failure path end-to-end (Gradle compile of `Car.java`/`Truck.java`), replacing the docstring workaround as the guard.

## Data Flow

    UmlClass.name ──mapper:275──→ Table.discriminator_values[class_id]
                                        │
                        ┌───────────────┴───────────────┐
                        ▼                               ▼
          pascal_case(...) → class_name        verbatim → @DiscriminatorValue
          (NEW — was pascal_case(class_id))    (unchanged)

Root naming (`pascal_case(table.name)`, `:137`) is untouched.

## File Changes

| File | Action | Lines |
|---|---|---|
| `emit/inheritance_context.py` | Modify `:169` | 1 |
| `tests/test_inheritance_context.py` | Values → class names; rename `test_subclass_class_names_use_pascal_case_class_id_order` → `..._discriminator_value_in_class_id_order`; **add** uuid-id + id-independence + `"Sports Car"` tests | ~45 |
| `tests/test_inheritance_rendering.py` | `:20` values; `@DiscriminatorValue` literals `:60,:82,:89` | ~6 |
| `tests/test_model_sources.py` | `:48` values | ~1 |
| `tests/test_project_sources.py` | `:37` values; **add** uuid hierarchy through `generate_project_sources` | ~20 |
| `tests/test_inheritance_backward_compatibility.py` | **Unchanged** — byte-identical SHA-256 gate | 0 |
| `samples/sample_model.py` | uuid-hex class-id constants; drop defect docstring | ~20 |
| `generation_runner/tests/test_sample_model.py` | Replace `:86` readable-id test with uuid-hex + digit-leading assertion; delete `:95` docstring test | ~12 |
| `openspec/specs/.../spec.md` (delta) | `:392` naming rule; `:415-426` values | ~25 |
| `docs/ai/*` | Continuity | ~40 |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit (RED first) | uuid digit-leading ids → class names from values | `build_inheritance_hierarchy_context`; RED = `InvalidJavaIdentifierError` |
| Unit | Id-independence | Same table, two id sets, identical contexts/output |
| Unit | Limitation pinned | `discriminator_values={...: "Sports Car"}` → `pytest.raises(InvalidJavaIdentifierError)`, assert `source_name` |
| Integration | uuid hierarchy through `generate_project_sources` / `generate_model_sources` | Assert exact paths `domain/Car.java`, `domain/Truck.java` |
| Snapshot | Non-discriminator SHA-256 | Must not change; any diff = regression |
| E2E | `bash scripts/verify-generated-project.sh` | Gradle compile of the uuid-id sample |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration code changes. `verify-generated-project.sh` is an unchanged pre-existing developer script invoked manually as evidence.

## Migration / Rollout

No migration. No persisted state, no checked-in generated artifacts.

## Open Questions

None blocking. Confirm at apply: (1) exact frozen uuid-hex literals (≥1 digit-leading per `vehicle`/`car`/`truck`); (2) the snapshot in `test_inheritance_backward_compatibility.py` stays byte-identical; (3) `docs/ai/NEXT_STEPS.md` known-defect entry removed.
