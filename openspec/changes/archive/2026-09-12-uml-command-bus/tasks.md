# Tasks: UmlCommand + Command Bus

Strict TDD. Test command: `cd backend && pytest apps/uml_commands -q` (verified
convention — `backend/pyproject.toml`'s `[tool.pytest.ini_options]` sets
`DJANGO_SETTINGS_MODULE = "config.settings"` and `testpaths = ["config",
"apps"]`; the prior `uml_modeling` cycle's own tasks.md used the identical
`cd backend && pytest apps/uml_modeling -q` form — no Makefile, no
`manage.py test` usage, no CI workflow found in this repo). Backend-only;
`apps/uml_modeling/` untouched.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~650-750 (5 production files ~195 lines incl. `__init__.py`/`handlers/__init__.py`/`apps.py` shells + 1 `INSTALLED_APPS` line + 10 test files ~470 lines) |
| 800-line budget risk | Low — comfortably under, unlike the two prior cycles' tasks.md (both High/chained) |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |
| Chain strategy | n/a — single PR fits the budget |

Decision needed before apply: No — this estimate fits inside the session's
fixed single-pr/800-line budget with margin (~50-150 lines), unlike
`canonical-uml-model` (~1150-1300, chained across 4 PRs) or
`email-verification-password-reset` (~1400-1800, chained). Scope is smaller
by design (proposal's own framing): 1 new app, 5 production modules
(`commands.py`, `dispatcher.py`, 3 `handlers/*.py`), no persistence, no API,
zero diff to `apps/uml_modeling/`.

## Phase 1: Package Skeleton & Registration

- [x] 1.1 Create `backend/apps/uml_commands/{__init__.py,apps.py}`
  (`UmlCommandsConfig(AppConfig)`, `name = "apps.uml_commands"`, `label =
  "uml_commands"`), `tests/__init__.py`, `handlers/__init__.py`; add
  `"apps.uml_commands"` under the `# Local` marker in `INSTALLED_APPS`
  (`backend/config/settings.py`), alongside `apps.uml_modeling`. Confirm
  `pytest` collects the new package (`testpaths` already covers `apps`, no
  config change needed). [prerequisite for all requirements]
- [x] 1.2 RED: `tests/test_apps.py` — app registers with `label ==
  "uml_commands"` (mirrors `uml_modeling`'s own `test_apps.py`). GREEN:
  implement `apps.py`. [prerequisite]

## Phase 2: Commands (dataclasses)

- [x] 2.1 RED: `tests/test_commands.py` — each of the 7 dataclasses
  constructs with its documented fields; each is frozen (mutating an
  instance raises `dataclasses.FrozenInstanceError`); `typing.get_args()` on
  the `UmlCommand` union covers exactly the 7 types.
- [x] 2.2 GREEN: implement `commands.py` — `AddClass`, `RemoveClass`,
  `RenameClass`, `AddAttribute`, `RemoveAttribute`, `AddRelationship`,
  `RemoveRelationship`, `UmlCommand` union alias. [AddClass, RemoveClass
  with Cascade, RenameClass, AddAttribute, RemoveAttribute, AddRelationship,
  RemoveRelationship — field shapes only; DD1, DD3]

## Phase 3: Dispatcher Skeleton

- [x] 3.1 Create `tests/factories.py` (`a_document`, `a_class`,
  `a_relationship_end`, `a_relationship` helpers wrapping `uml_modeling`'s
  own domain constructors/factories) — reused by every later test module.
- [x] 3.2 RED: `tests/test_dispatcher.py` — using a fake command type
  monkeypatched into `_HANDLERS`, `apply()` returns a `CommandResult`; the
  original `document` and `document.model` objects are unchanged (identity
  check, not just equality); the returned `document.revision == original
  revision + 1`; `validation_result == validate(new_model, rules=RULES)`,
  never `None` or skipped.
- [x] 3.3 GREEN: implement `dispatcher.py` — `CommandResult`, `_HANDLERS:
  dict[type, Handler] = {}` (empty until Phases 4-6 populate it),
  `apply(document, command, *, now)`. [Dispatcher Apply Contract; DD2, DD4]

## Phase 4: Class Handlers

- [x] 4.1 RED: `tests/handlers/test_classes.py` — `add_class` appends a
  `UmlClass` matching the given id/name (N -> N+1 classes); `remove_class`
  removes the matching class and leaves all other classes, enumerations,
  and relationships unchanged; `remove_class` cascade-removes every
  `Relationship` whose `source.class_id`/`target.class_id` equals the
  removed id, and `validate()` on the result reports no
  `INVALID_RELATIONSHIP_ENDPOINT` for it; `remove_class` on an unknown id
  returns the same unchanged `model` object; `rename_class` preserves `id`,
  `attributes`, `operations`, `visibility` and changes only `name`;
  `rename_class` on an unknown id returns the same unchanged `model` object
  (design's Open Question extrapolation — no scenario backs this case, DD6
  pattern applied for consistency).
- [x] 4.2 GREEN: implement `handlers/classes.py` (`add_class`,
  `remove_class`, `rename_class`); wire all three into
  `dispatcher._HANDLERS`. [AddClass, RemoveClass with Cascade, RenameClass,
  Missing-Target No-Op Policy (RemoveClass); DD6]

## Phase 5: Attribute Handlers

- [x] 5.1 RED: `tests/handlers/test_attributes.py` — `add_attribute`
  appends the new `UmlAttribute` preserving existing attributes and their
  order; `add_attribute` on an unknown class id returns the same unchanged
  `model` object; `remove_attribute` removes the matching attribute
  preserving the relative order of the rest; `remove_attribute` on an
  unknown class id or unknown attribute id returns the same unchanged
  `model` object.
- [x] 5.2 GREEN: implement `handlers/attributes.py` (`add_attribute`,
  `remove_attribute`); wire both into `dispatcher._HANDLERS`.
  [AddAttribute, RemoveAttribute, Missing-Target No-Op Policy
  (AddAttribute, RemoveAttribute); DD6]

## Phase 6: Relationship Handlers

- [x] 6.1 RED: `tests/handlers/test_relationships.py` — `add_relationship`
  appends the new `Relationship` referencing its source/target, performing
  no endpoint-existence check itself (blind append — the always-apply
  policy is enforced at the dispatcher/validation level, not the handler);
  `remove_relationship` removes the matching relationship and leaves all
  others unchanged; `remove_relationship` on an unknown id returns the same
  unchanged `model` object.
- [x] 6.2 GREEN: implement `handlers/relationships.py` (`add_relationship`,
  `remove_relationship`); wire both into `dispatcher._HANDLERS`. Confirm
  `_HANDLERS` now has exactly 7 entries (one command type each).
  [AddRelationship, RemoveRelationship, Missing-Target No-Op Policy
  (RemoveRelationship); DD6]

## Phase 7: Dispatcher Policy Scenarios (end-to-end, real handlers)

- [x] 7.1 RED: extend `tests/test_dispatcher.py` — always-apply-diagnostics
  scenario (model with only class A; `AddRelationship` applied with source
  A and a nonexistent target id -> `apply()` returns a `CommandResult`
  whose document contains the new relationship, `validation_result
  .diagnostics` is non-empty and includes an `INVALID_RELATIONSHIP_ENDPOINT`
  diagnostic, no exception is raised); missing-target no-op scenarios
  through the real dispatcher (not fakes) for `RemoveClass`,
  `RemoveAttribute`, `RemoveRelationship`, `AddAttribute` on unknown ids
  (model content unchanged, resulting document's revision exactly one
  greater than the input's, no exception).
- [x] 7.2 GREEN: no new production code expected — Phases 4-6 handlers
  should already satisfy this; if any scenario fails, fix the offending
  handler until green. [Always-Apply Diagnostics Policy, Missing-Target
  No-Op Policy]

## Phase 8: Structural — Import Boundary

- [x] 8.1 Add `tests/test_import_boundary.py` — `ast.parse` each of
  `commands.py`, `dispatcher.py`, `handlers/*.py`; walk `ast.Import`/
  `ast.ImportFrom` nodes; assert every non-stdlib import target (checked
  against `sys.stdlib_module_names`) starts with `apps.uml_modeling`;
  assert no import target starts with `django`, `apps.organizations`, or
  `apps.users`. Expected to pass immediately against the source written in
  Phases 2-6 (a structural regression guard, not a RED-then-GREEN pair —
  nothing left to implement if it fails, only a boundary violation to
  fix). [uml_commands Import Boundary; DD7]

## Phase 9: Integration

- [x] 9.1 RED: `tests/test_integration.py` — one composed scenario applying
  all 7 commands in sequence against a single evolving `ProjectDocument`
  (`AddClass` x2, `AddAttribute`, `AddRelationship`, `RenameClass`,
  `RemoveAttribute`, `RemoveRelationship`, `RemoveClass`); assert the final
  model's shape and that each intermediate `CommandResult.document.revision`
  increments by exactly 1 over the previous step.
- [x] 9.2 GREEN: no new production code expected; fix any handler/dispatcher
  gap the composed scenario surfaces. [Dispatcher Apply Contract —
  end-to-end confirmation]

## Phase 10: Verification

- [x] 10.1 Run `cd backend && pytest apps/uml_commands -q`; confirm all 7
  commands, all 11 requirements' 13 scenarios, and both structural tests
  (`test_apps.py`, `test_import_boundary.py`) pass with zero regression to
  the existing suite (`cd backend && pytest -q`).
- [x] 10.2 Confirm `apps/uml_modeling/` has zero diff: `git diff --stat
  backend/apps/uml_modeling` returns empty.
