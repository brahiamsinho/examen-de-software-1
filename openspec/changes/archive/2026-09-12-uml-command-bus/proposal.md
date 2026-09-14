# Proposal: UmlCommand + Command Bus

## Intent

`uml_modeling` (Cycle 1) is a pure, immutable domain with zero mutation
methods beyond `ProjectDocument.with_model`/`with_layout` (whole-object
replace). Any diagram edit today requires hand-building an entire new
`CanonicalUmlModel`, which is unsafe, unauditable, and not reusable across
future callers (HTTP API, assistant, XMI import). This cycle introduces
`UmlCommand` plus a thin dispatcher so structural edits (add/remove/rename
class, attribute, relationship) become named, validated, testable
operations — the mutation contract every future editor UI or API endpoint
will call, without yet building that UI, API, or persistence.

## Scope

### In Scope

- `UmlCommand`: plain-Python (no Django) immutable command objects, one per
  supported mutation.
- A thin in-process dispatcher (registry mapping command type to handler),
  mirroring the existing `validate()`/`Rule` pattern in `validation/engine.py`.
- Handlers produce a new `CanonicalUmlModel`/`ProjectDocument` via existing
  constructors/`with_model` — never in-place mutation.
- Handlers auto-invoke `validate(model, rules=RULES)` after applying; the
  apply result surfaces the resulting `ValidationResult` (never silently
  skipped).
- New sibling Django app `backend/apps/uml_commands/`, depending on
  `apps.uml_modeling` (settles prior D7: intra-backend imports permitted
  uml_commands → uml_modeling, one-directional).

### Out of Scope

- Diagram/`ProjectDocument` persistence (Django model, migration) — deferred.
- Undo/redo, command history/log, command stack — deferred.
- Any change to `apps/uml_modeling/` itself — stays frozen/pure.
- API endpoints, canvas UI — no consumer exists yet.

## Capabilities

### New Capabilities

- `uml-command-bus`: `UmlCommand` types, the dispatcher, per-command
  handlers, and the post-apply validation contract.

### Modified Capabilities

None.

## Approach

New app `apps/uml_commands/`: `commands.py` (dataclasses), `dispatcher.py`
(`apply(document, command) -> CommandResult`, registry keyed by command
type), `handlers/` (one module per element kind). `CommandResult` carries
the new `ProjectDocument` and the post-apply `ValidationResult`.

First-cut command set, chosen from what `UmlClass`/`Enumeration`/
`Relationship` already support constructing:

| Command | Targets |
|---|---|
| `AddClass`, `RemoveClass`, `RenameClass` | `UmlClass` |
| `AddAttribute`, `RemoveAttribute` | `UmlAttribute` on a class |
| `AddRelationship`, `RemoveRelationship` | `Relationship` |

Operations/enumerations follow the same pattern later; omitted now to keep
this cycle's reviewable surface small.

## Affected Areas

| Area | Impact |
|---|---|
| `backend/apps/uml_commands/` | New |
| `backend/config/settings.py` | Modified (`INSTALLED_APPS`) |
| `backend/apps/uml_modeling/` | Untouched |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `RemoveClass` leaves dangling relationships | Medium | Flagged for sdd-spec: cascade-remove vs. rely on `INVALID_RELATIONSHIP_ENDPOINT` |
| Apply-vs-reject-on-invalid policy underspecified | Medium | Flagged for sdd-spec: always apply + report diagnostics, chosen as default (matches "never silently skip") |

## Rollback Plan

Self-contained new app, one `INSTALLED_APPS` line, no migrations, no
consumers. Revert via `git revert` or delete the app + settings line.

## Dependencies

None new (stdlib `dataclasses` only, reuses `uml_modeling` public API).

## Success Criteria

- [ ] Each of the 7 commands applies via the dispatcher and produces a new
      immutable `ProjectDocument`/`CanonicalUmlModel`.
- [ ] Every apply auto-runs `validate()` and returns diagnostics.
- [ ] `apps/uml_modeling/` has zero diff.
- [ ] `uml_commands` imports only `apps.uml_modeling` + stdlib.

## Proposal question round

Scope was already fixed via 4 confirmed decisions (Engram
`sdd/uml-command-bus/scope-decisions`, obs #506). Two smaller design
choices remain genuinely open and are flagged above for `sdd-spec`/
`sdd-design` rather than decided unilaterally here:

1. Should `RemoveClass` cascade-remove relationships that reference it, or
   leave them dangling for validation to flag?
2. Should an invalid post-apply model still be returned (diagnostics-only,
   current default assumption), or should some commands reject/refuse to
   apply when they'd produce an invalid model?
