# Design: UmlCommand + Command Bus

## Technical Approach

New sibling Django app `backend/apps/uml_commands/` (registration shell only,
no `models.py`/migrations), depending one-directionally on `apps.uml_modeling`
(settles D7). Commands are plain-Python immutable dataclasses; a thin
dict-keyed dispatcher looks up a handler by exact command type, the handler
performs a pure `CanonicalUmlModel -> CanonicalUmlModel` transform via
`dataclasses.replace`/tuple rebuilding (never in-place mutation), and
`apply()` wraps the result through `document.with_model(...)` and always
runs `validate(new_model, rules=RULES)`. `apps/uml_modeling/` requires zero
changes — every primitive this design needs (`class_by_id`, `with_model`,
`validate`, `RULES`, frozen dataclasses with tuple fields) already exists.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | `UmlCommand` is a **closed `Union` type alias** (`AddClass \| RemoveClass \| ... \| RemoveRelationship`), each command its own frozen dataclass | ABC/Protocol base class; single tagged dataclass with a `kind` discriminator | Mirrors the project's own closed-union convention (`domain/types.py::AttributeType = PrimitiveType \| EnumerationRef`). No ABC/Protocol exists anywhere in the codebase. A tagged dataclass would force optional/`Any` fields for the union of all 7 shapes, losing static typing per command |
| DD2 | Registry is a static **`dict[type, Handler]`** module constant in `dispatcher.py` | `RULES`-style tuple (like `validation/engine.py`) | `validate()`'s tuple is an aggregation ("run every rule"); dispatch is an exact-key lookup ("run the one handler for this type"), so `dict` is the correct shape for the access pattern. Still an explicit static structure, no decorator auto-registry, no hidden mutable state — keeps the spirit of the prior cycle's DD4 |
| DD3 | Commands carry **already-constructed domain value objects** (`AddAttribute.attribute: UmlAttribute`, `AddRelationship.relationship: Relationship`) rather than flattened constructor fields | Flatten `UmlAttribute`'s/`Relationship`'s fields directly onto the command | Avoids duplicating `UmlAttribute`/`Relationship` field lists on the command; caller builds the value object with existing domain constructors (per proposal: "via existing constructors"); no drift risk when those dataclasses gain fields |
| DD4 | `apply()` takes an explicit `now: datetime.datetime` keyword-only argument, forwarded to `with_model` | Handler/dispatcher calls `datetime.now()` internally | Matches prior cycle's DD8 clock-injection convention; `uml_commands` stays deterministic/testable, no freezegun needed |
| DD5 | Handlers organized **one module per element kind** under `handlers/` (`classes.py`, `attributes.py`, `relationships.py`) | One handler module per command; one flat `handlers.py` | Matches the proposal's own stated approach; groups handlers by the domain concept they touch, mirrors `validation/rules/relationships.py` grouping several relationship rules in one file |
| DD6 | Missing-target no-op implemented as an early `class_by_id`/id-scan check returning **the same unchanged `model` object**, before any `replace()` | Raise then catch; return a fresh but content-equal model | Reuses `CanonicalUmlModel.class_by_id`'s existing None-returning convention exactly as the spec instructs; returning the same object (not a rebuilt copy) makes "content identical" trivially true and cheap |
| DD7 | Import-boundary AST test scopes to `commands.py`, `dispatcher.py`, `handlers/**.py` only — **excludes** `apps.py`/`__init__.py` and `tests/` | Check every file under `apps/uml_commands/` including `apps.py` | `apps.py` MUST import `django.apps.AppConfig` to register as a Django app — `uml_modeling`'s own `apps.py` does the same and is not considered a purity violation. The spec's "plain-Python (no Django)" intent (proposal's own wording) targets the command/dispatch/handler surface, not the mandatory registration shell every app in this project has. `tests/` legitimately imports `pytest` (third-party, not stdlib/uml_modeling) |

## Data Flow

```
caller
  │  apply(document, command, now=...)
  ▼
dispatcher.apply
  │  handler = _HANDLERS[type(command)]
  │  new_model = handler(document.model, command)   ── pure transform, no mutation
  │  new_document = document.with_model(new_model, now=now)   ── revision + 1
  │  validation_result = validate(new_document.model, rules=RULES)   ── always runs
  ▼
CommandResult(document=new_document, validation_result=validation_result)
```

Each handler is `(CanonicalUmlModel, <specific command>) -> CanonicalUmlModel`.
No handler raises; a missing target short-circuits to the unchanged model.

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/uml_commands/__init__.py` | Create | Empty, matches `uml_modeling` convention |
| `backend/apps/uml_commands/apps.py` | Create | `UmlCommandsConfig(AppConfig)`, `name = "apps.uml_commands"`, `label = "uml_commands"` |
| `backend/apps/uml_commands/commands.py` | Create | 7 frozen dataclasses + `UmlCommand` union alias |
| `backend/apps/uml_commands/dispatcher.py` | Create | `CommandResult`, `_HANDLERS` dict, `apply()` |
| `backend/apps/uml_commands/handlers/{__init__,classes,attributes,relationships}.py` | Create | Pure handler functions |
| `backend/apps/uml_commands/tests/**` | Create | One test module per unit + `test_apps.py` + `test_import_boundary.py` |
| `backend/config/settings.py` | Modify | Add `"apps.uml_commands"` to `INSTALLED_APPS` (Local section, alongside `apps.uml_modeling`) |
| `backend/apps/uml_modeling/**` | **None** | Zero diff — confirmed achievable (see below) |

## Interfaces / Contracts

```python
# commands.py
from dataclasses import dataclass
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.elements import UmlAttribute, Relationship

@dataclass(frozen=True)
class AddClass: class_id: ElementId; name: str

@dataclass(frozen=True)
class RemoveClass: class_id: ElementId

@dataclass(frozen=True)
class RenameClass: class_id: ElementId; new_name: str

@dataclass(frozen=True)
class AddAttribute: class_id: ElementId; attribute: UmlAttribute

@dataclass(frozen=True)
class RemoveAttribute: class_id: ElementId; attribute_id: ElementId

@dataclass(frozen=True)
class AddRelationship: relationship: Relationship

@dataclass(frozen=True)
class RemoveRelationship: relationship_id: ElementId

UmlCommand = (
    AddClass | RemoveClass | RenameClass | AddAttribute
    | RemoveAttribute | AddRelationship | RemoveRelationship
)

# dispatcher.py
import datetime
from dataclasses import dataclass
from apps.uml_modeling.documents import ProjectDocument
from apps.uml_modeling.validation.diagnostics import ValidationResult
from apps.uml_modeling.validation.engine import RULES, validate

@dataclass(frozen=True)
class CommandResult:
    document: ProjectDocument
    validation_result: ValidationResult

def apply(document: ProjectDocument, command: UmlCommand, *, now: datetime.datetime) -> CommandResult:
    handler = _HANDLERS[type(command)]
    new_model = handler(document.model, command)
    new_document = document.with_model(new_model, now=now)
    return CommandResult(
        document=new_document,
        validation_result=validate(new_document.model, rules=RULES),
    )
```

**Cascade removal** (`handlers/classes.py::remove_class`): `class_by_id` check
first (no-op if `None`); else rebuild `classes` by filtering out the match,
and rebuild `relationships` by filtering out every `Relationship` whose
`source.class_id` or `target.class_id` equals the removed id (field name
confirmed in `domain/elements.py::RelationshipEnd.class_id`), then
`dataclasses.replace(model, classes=..., relationships=...)`.

**No-op pattern** (`RemoveClass`, `RemoveAttribute`, `RemoveRelationship`,
`AddAttribute`): each handler's first statement is a lookup identical in
shape to `class_by_id` (`class_by_id`/id-membership scan); if the target is
absent, `return model` unchanged before constructing anything.

**Import-boundary test** (`test_import_boundary.py`): `ast.parse` each of
`commands.py`, `dispatcher.py`, `handlers/*.py`; walk `ast.Import`/
`ast.ImportFrom` nodes; assert every non-stdlib module name (checked against
`sys.stdlib_module_names`) starts with `apps.uml_modeling`, and assert no
name starts with `django`, `apps.organizations`, or `apps.users`.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit — commands | Dataclass shapes are frozen, `UmlCommand` union covers all 7 | Plain `pytest`, literal construction |
| Unit — handlers | One module per handler group (classes/attributes/relationships) covering append/remove/rename + all 4 no-op cases | Minimal model fixtures via `tests/factories.py` (mirrors `uml_modeling`'s factory pattern) |
| Unit — dispatcher | Revision +1, original document/model untouched (identity check), validation always populated, invalid-result-still-applies scenario | `apply()` against fixed fixtures; fake handler injected for one isolated dispatch test |
| Structural | App registers (`test_apps.py`, mirrors `uml_modeling`'s); import boundary (`test_import_boundary.py`) | Direct assertions, no mocking |
| Integration | End-to-end: apply all 7 commands in sequence against one evolving document, assert final model shape | One composed scenario test |
| E2E | N/A | No API/consumer this cycle |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. Pure in-process dataclasses
and functions, no I/O.

## Migration / Rollout

No migration required. No models, no DB tables. Rollback = delete
`backend/apps/uml_commands/` and the single `INSTALLED_APPS` line.

## Scenario Coverage Check (self-verification against the 13 scenarios)

All 13 scenarios in `specs/uml-command-bus/spec.md` are satisfiable by this
design: dispatcher-identity/revision (1–2) by `apply()`'s structure; append
scenarios (3, 7, 9) by tuple concatenation; removal scenarios (4, 8, 10) by
tuple filtering; cascade (5) by the dual-filter in `remove_class`; rename (6)
by `dataclasses.replace` on `name` only; always-apply-diagnostics (11) by
`add_relationship` never checking endpoint existence, only `validate()`
flagging it after; no-op (12) by the pre-`replace` short-circuit (DD6); import
boundary (13) by the scoped AST test (DD7). No scenario forced a design
choice beyond DD1–DD7 above; DD7's `apps.py` exclusion is the one place this
design had to *interpret* the spec's "package source" wording rather than
apply it literally, and it does so consistently with `uml_modeling`'s own
existing precedent.

## Open Questions

- [ ] `RenameClass` on a missing `class_id`: not one of the 4 commands the
  spec's Missing-Target No-Op requirement names, and none of the 13 scenarios
  exercise it. This design applies the same no-op pattern to it for
  consistency (DD6's pattern, not a literal spec requirement) — flagged so
  `sdd-tasks`/`sdd-verify` know this specific behavior is a design-time
  extrapolation, not a scenario-backed requirement.

> Size note: exceeds the skill's 800-word soft budget for the same reason the
> prior cycle's design did — the task explicitly required field-level
> dataclass/signature detail sufficient for `sdd-tasks` to slice
> implementable units without re-deriving them from the domain source.
