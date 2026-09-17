# Proposal: UML Class Operations

## Intent

A UML class diagram without methods is half a diagram. The domain already
models them — `UmlOperation`/`UmlParameter` and `UmlClass.operations` exist,
the codec round-trips operations losslessly, and `empty_element_name` already
validates them — yet every one of those paths has zero production callers
because nothing can ever *create* an operation. This cycle opens the write
path end to end: command, handler, schema, form, canvas compartment, so users
can declare `+ crearUsuario(): Usuario` on a class and see it converge live.

## Scope

### In Scope

- `AddOperation`/`RemoveOperation` frozen dataclasses + handlers, mirroring
  `AddAttribute`/`RemoveAttribute` verbatim; the closed `UmlCommand` union
  grows 7 → 9 variants and `_HANDLERS` gains two entries.
- Pydantic `AddOperationIn`/`RemoveOperationIn` in the `CommandIn`
  discriminated union; matching TS variants in `UmlCommandIn`.
- New `duplicate_operation_name` rule (name-only, scoped per class);
  `RULES` grows 10 → 11 and `test_registry_has_exactly_ten_rules` is
  updated in the same change.
- `AddOperationForm.tsx` / `RemoveOperationControl.tsx`, mounted alongside
  the existing attribute controls.
- An operations compartment in the generated class-box SVG, in real UML
  notation, with a second divider and extended layout math.

### Out of Scope

- **UI-reachable parameters.** v1 sends `parameters: ()`. Domain, codec and
  persistence already carry a non-empty tuple losslessly, so a dynamic
  parameter-rows UI is a purely additive later cycle, not a rework.
- Operation overloading — same name twice in one class is a duplicate,
  regardless of signature.
- `static`/`abstract` modifiers; codec, persistence, and locking changes.

## Capabilities

### New Capabilities

None — this extends existing capabilities.

### Modified Capabilities

- `uml-command-bus`: two new command variants and their handlers join the
  closed union and dispatcher.
- `uml-validation`: adds `duplicate_operation_name`; the fixed rule registry
  becomes 11 rules.
- `web-uml-canvas`: operations are creatable/removable from the workspace
  panel and rendered in a dedicated class-box compartment.

`uml-domain-model` is **unchanged** — its spec already requires an ordered
`operations` list on a class.

## Approach

Exploration's **Approach 2**: clone the attribute vertical slice. Every layer
already has a working, tested sibling to mirror, so the change is mechanical
and its review surface stays small. The only genuinely new logic is the
nullable `return_type` (unlike an attribute's always-present `type`), which
each layer must render as a void-like operation, and the SVG second
compartment.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/uml_commands/commands.py` | Modified | Two dataclasses; union 7 → 9 |
| `backend/apps/uml_commands/handlers/operations.py` | New | Mirror of `attributes.py` |
| `backend/apps/uml_commands/dispatcher.py` | Modified | Two `_HANDLERS` entries |
| `backend/apps/uml_documents/schemas.py` | Modified | `UmlOperationIn`, `Add/RemoveOperationIn`, union |
| `backend/apps/uml_modeling/validation/diagnostics.py` | Modified | `DUPLICATE_OPERATION_NAME` code |
| `backend/apps/uml_modeling/validation/rules/naming.py` | Modified | New rule |
| `backend/apps/uml_modeling/validation/engine.py` | Modified | `RULES` 10 → 11 |
| `backend/apps/uml_modeling/tests/test_engine.py` | Modified | Rule-count assertion |
| `frontend/src/lib/uml_documents.ts` | Modified | `UmlCommandIn` variants |
| `frontend/src/components/workspace/AddOperationForm.tsx` | New | Mirror of `AddAttributeForm` |
| `frontend/src/components/workspace/RemoveOperationControl.tsx` | New | Mirror of `RemoveAttributeControl` |
| `frontend/src/components/workspace/DiagramCanvas.tsx` | Modified | `operationLines`, second divider, layout math |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `test_registry_has_exactly_ten_rules` breaks CI | High | Rename + retarget to 11 in the same change; update the `RULES` comment |
| Three closed unions (Python / Pydantic / TS) drift | Med | Treat the triple touch point as one work unit; a missing side fails typecheck or request validation |
| Hand-rolled SVG layout math regresses attribute-only rendering | Med | Keep `attributeLines` behaviour byte-identical when `operationLines` is empty; existing `DiagramCanvas.test.tsx` guards it; human visual check |
| Nullable `return_type` mishandled as `""` vs `null` | Med | One explicit void-like rendering decision applied uniformly across schema, form, and canvas |
| Deferred parameters read as missing scope | Low | Out-of-scope is explicit, and the tuple already persists losslessly |

## Rollback Plan

`git revert`. The two commands are additive: reverting shrinks the unions
back to 7 and `RULES` to 10, and the canvas drops the second compartment.
Documents persisted with non-empty `operations` stay valid JSON — the codec
keeps decoding them — they simply become unreachable again, exactly the
pre-change state. No migration, no data loss.

## Dependencies

- Archived and stable: `uml-domain-model`, `uml-command-bus`,
  `uml-validation`, `web-uml-canvas`, `realtime-document-sync`.
- No new packages.

## Success Criteria

- [ ] A user adds an operation with a name, optional return type, and
      visibility; it appears in the class box in UML notation.
- [ ] An operation with no return type renders distinctly from one with a
      return type.
- [ ] Removing an operation removes it from the diagram and persists.
- [ ] A duplicate operation name in one class raises
      `duplicate_operation_name`; the same name in a different class does not.
- [ ] An empty operation name still raises `empty_element_name`.
- [ ] Operations round-trip through save/reload and broadcast live to a
      second collaborator.
- [ ] Classes with zero operations render exactly as they do today.
- [ ] Full backend and frontend suites pass, with the rule registry at 11.
