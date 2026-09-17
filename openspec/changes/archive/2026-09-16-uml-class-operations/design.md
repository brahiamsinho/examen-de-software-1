# Design: UML Class Operations

## Technical Approach

Clone the attribute vertical slice (proposal §Approach). Every layer has a
working sibling; the only new logic is nullable `return_type` and the SVG
second compartment. Verified against source: the codec already round-trips
operations (`codec.py:133-162`, **zero changes**), and
`ElementKind.OPERATION` / `operation_path` already exist
(`diagnostics.py:38,80`). `RULES` is exactly 10 today (`engine.py:33-44`).

## Architecture Decisions

### DD1 — Command dataclasses

`commands.py`: import `UmlOperation`, add two frozen dataclasses carrying a
constructed domain object (same shape as `AddAttribute`):
`AddOperation(class_id, operation: UmlOperation)` and
`RemoveOperation(class_id, operation_id)`. The closed `UmlCommand` union
(lines 53-61) grows 7 → 9.

**Rejected**: flattened `name`/`return_type` fields — violates the module's
stated "already-constructed domain value objects (DD3)" convention.

### DD2 — `handlers/operations.py` (new)

Verbatim mirror of `handlers/attributes.py`, substituting
`attributes=` → `operations=` and `attribute` → `operation`. Keeps both
short-circuits: `class_by_id(...) is None → return model`, and in
`remove_operation`, `not any(o.id == command.operation_id ...) → return
model`. No handler raises (Missing-Target No-Op Policy).

### DD3 — Dispatcher

`dispatcher.py`: import `AddOperation`/`RemoveOperation` and
`add_operation`/`remove_operation`; add two `_HANDLERS` entries after the
attribute pair (lines 36-37). Lookup is exact-type, so registration is the
whole wiring.

### DD4 — Wire schema and the nullable `return_type`

`schemas.py`:

```python
class UmlOperationIn(Schema):
    id: str
    name: str
    return_type: str | dict | None = None   # decoded via codec._decode_attribute_type
    visibility: Literal["public","private","protected","package"] = "public"

class AddOperationIn(Schema):    type: Literal["AddOperation"];  class_id: str; operation: UmlOperationIn
class RemoveOperationIn(Schema): type: Literal["RemoveOperation"]; class_id: str; operation_id: str
```

Add both to the `CommandIn` discriminated union (lines 75-86).

| Wire option | Verdict |
|---|---|
| **JSON `null`, field omittable (default `None`)** | **Chosen** |
| Omitted-only | Rejected — can't distinguish from a client bug; spec pins `return_type: null` |
| `""` sentinel | Rejected — `AttributeType` has no empty member; `_decode_attribute_type("")` raises `ValueError` |

`""` therefore stays an *error* (→ `InvalidCommandPayloadError` → 422 via
`command_from_payload`), not a synonym for void. `None` maps straight to
`UmlOperation.return_type: AttributeType | None`. No `parameters` field
exists on `UmlOperationIn` at all — the mapper always passes `()`.

**`services.py` also changes** (missing from the proposal's Affected Areas
table): two `isinstance` branches in `_command_from_payload` (after line
208) plus `_operation_from_schema`, mirroring `_attribute_from_schema`
(lines 216-222) with `return_type=codec._decode_attribute_type(x)
if x is not None else None` and `parameters=()`.

### DD5 — `duplicate_operation_name`

`diagnostics.py`: add `DUPLICATE_OPERATION_NAME = "DUPLICATE_OPERATION_NAME"`
after `DUPLICATE_ATTRIBUTE_NAME`. `naming.py`: copy
`duplicate_attribute_name` (lines 95-115), iterating `uml_class.operations`
with a per-class `seen: set[str]`, emitting `operation_path(uml_class.id,
operation.id)` and `ElementKind.OPERATION`. Name-only comparison — no
signature logic (confirmed scope: no overloads). `engine.py`: import it and
insert at index 3, immediately after `duplicate_attribute_name`, keeping
naming rules grouped; `RULES` becomes 11.

### DD6 — Rule-count test

`test_engine.py:49-50`: rename `test_registry_has_exactly_ten_rules` →
`test_registry_has_exactly_eleven_rules`, assertion `assert len(RULES) ==
11`. Also update the stale prose in `engine.py:7` ("exactly 10 rules") and
the `RULES` comment (lines 30-32).

### DD7 — TS union

`uml_documents.ts`: add to `UmlCommandIn` (lines 116-136):

```ts
| { type: "AddOperation"; class_id: string;
    operation: { id: string; name: string; return_type: AttributeType | null; visibility?: Visibility } }
| { type: "RemoveOperation"; class_id: string; operation_id: string }
```

Update the block comment ("Six of the seven…" → eight of the nine; only
`RenameClass` stays unwired). `UmlOperation`/`UmlClass.operations` already
exist (lines 46-60).

### DD8 — Forms and mount points

`AddOperationForm.tsx` — mirror of `AddAttributeForm.tsx` including the
`resolvedClassId` re-derivation guard (its documented production-bug fix).
Props `{ classes, onSubmit, disabled }`. Fields: class select, name input,
return-type select whose **first option is `<option value="">Sin tipo de
retorno</option>`** followed by `PRIMITIVE_TYPES`, and a visibility select
defaulting to `public` (the domain default). Submits `return_type:
type === "" ? null : type`, `id: crypto.randomUUID()`.

`RemoveOperationControl.tsx` — mirror of `RemoveAttributeControl.tsx`, both
ids derived fresh per render, no confirmation branch.

Mount points in `frontend/src/app/(app)/documents/[docId]/page.tsx`
(confirmed): an `<Card><CardTitle>Operación</CardTitle>` after the "Atributo"
card (closes line 200, before `AddRelationshipControl`) under "Agregar", and
after the "Atributo" card (closes line 241, before the "Relación" card) under
"Eliminar". Same `classes`/`onSubmit`/`disabled` props.

### DD9 — Operations compartment in `classBoxSvgDataUri`

Signature becomes `(name, attributeLines, operationLines: string[] = [])`.
Additive-only arithmetic, so **zero operations renders byte-identically**:

| Quantity | Change |
|---|---|
| `width` | `Math.max(nameWidth, ...attrWidths, ...opWidths, 0)` — empty spread contributes nothing |
| `opAreaHeight` | `operationLines.length > 0 ? DIVIDER_MARGIN * 2 + n * ATTR_LINE_HEIGHT : 0` |
| `height` | existing expression `+ opAreaHeight` |
| `opDividerY` | `attrStartY + attrAreaHeight + DIVIDER_MARGIN` (symmetric with the name divider) |
| `opStartY` | `opDividerY + DIVIDER_MARGIN`, lines reuse `ATTR_LINE_HEIGHT`/`ATTR_FONT_SIZE`/mono stack |
| second `<line>` + `opText` | emitted only when `operationLines.length > 0`; empty string otherwise |

`attrAreaHeight`'s empty-state (`ATTR_LINE_HEIGHT * 0.6`) is untouched. With
`operationLines = []` every term is `0`/`""`, so the SVG string, `width` and
`height` are identical to today's output — satisfying the spec scenario "A
class with zero operations renders exactly as before".

### DD10 — Visibility symbol (asymmetry, deliberate)

**Finding**: there is no existing symbol convention. `toElements`
(`DiagramCanvas.tsx:236`) hardcodes `- ${a.name}: ...` and ignores
`a.visibility` entirely. Operations *do* collect visibility, so add
`VISIBILITY_SYMBOL: Record<Visibility, string> = { public: "+", private: "-",
protected: "#", package: "~" }` and use it for operation lines only:

```ts
const operationLines = c.operations.map((o) =>
  `${VISIBILITY_SYMBOL[o.visibility]} ${o.name}(${o.parameters
     .map((p) => `${p.name}: ${attributeTypeLabel(p.type)}`).join(", ")})` +
  (o.return_type === null ? "" : `: ${attributeTypeLabel(o.return_type)}`));
```

Renders `+ crearUsuario(): Usuario` and `+ guardar()`. Parameters are mapped
(always empty in v1) so the deferred parameter cycle needs no canvas edit.
The attribute line is **left untouched** — retrofitting it would change
existing `DiagramCanvas.test.tsx` expectations and is out of scope. Flag as
a follow-up.

## Data Flow

    AddOperationForm ─→ submitCommand ─→ POST /commands
         │                                     │
         │                        schemas.CommandIn (discriminated)
         │                                     ↓
         │                    services._command_from_payload → AddOperation
         │                                     ↓
         │                    dispatcher.apply → handlers.add_operation
         │                                     ↓
         │                    validate(RULES=11) + codec.to_json + broadcast
         ↓                                     ↓
    DiagramCanvas.toElements ←──── useDocument ←── WS document.update

## File Changes

| File | Action |
|---|---|
| `backend/apps/uml_commands/commands.py` | Modify — 2 dataclasses, union 7→9 |
| `backend/apps/uml_commands/handlers/operations.py` | **Create** |
| `backend/apps/uml_commands/dispatcher.py` | Modify — imports + 2 `_HANDLERS` |
| `backend/apps/uml_documents/schemas.py` | Modify — 3 schemas + union |
| `backend/apps/uml_documents/services.py` | Modify — 2 branches + `_operation_from_schema` (**not in proposal table**) |
| `backend/apps/uml_modeling/validation/diagnostics.py` | Modify — 1 code |
| `backend/apps/uml_modeling/validation/rules/naming.py` | Modify — 1 rule |
| `backend/apps/uml_modeling/validation/engine.py` | Modify — `RULES` 10→11, stale comments |
| `backend/apps/uml_modeling/tests/test_engine.py` | Modify — DD6 |
| `frontend/src/lib/uml_documents.ts` | Modify — 2 union variants |
| `frontend/src/components/workspace/AddOperationForm.tsx` | **Create** |
| `frontend/src/components/workspace/RemoveOperationControl.tsx` | **Create** |
| `frontend/src/components/workspace/DiagramCanvas.tsx` | Modify — DD9, DD10 |
| `frontend/src/app/(app)/documents/[docId]/page.tsx` | Modify — 2 cards |
| `backend/apps/uml_documents/codec.py` | **None — already complete** |

## Testing Strategy (DD11)

| Spec scenario | Test file / case |
|---|---|
| Operation is appended; no-return-type accepted | `uml_commands/tests/handlers/test_operations.py` (new, mirrors `test_attributes.py`) |
| Remove; unknown class/operation id no-ops | same file |
| Union membership (9 variants) | `uml_commands/tests/test_commands.py` |
| `AddOperationIn`/`RemoveOperationIn` discrimination, `return_type` null & omitted, `""` → 422 | `uml_documents/tests/test_schemas.py`, `test_services.py` |
| `DUPLICATE_OPERATION_NAME` within a class; same name across classes is clean | `uml_modeling/tests/test_rules_naming.py` |
| `EMPTY_ELEMENT_NAME` still applies to operations | `test_rules_naming.py` (existing rule, add case) |
| Registry has 11 rules | `test_engine.py` (DD6) |
| End-to-end apply + persist | `uml_documents/tests/test_services.py` |
| Form fields, "no return type" option, no parameter input | `__tests__/AddOperationForm.test.tsx` (new) |
| Class→operation scoping, immediate submit | `__tests__/RemoveOperationControl.test.tsx` (new) |
| Operations compartment, void-like line, **zero-ops byte-identical SVG/width/height** | `__tests__/DiagramCanvas.test.tsx` |

Round-trip/broadcast scenarios are covered by the existing WS suite plus a
manual two-client check (no new E2E harness this cycle).

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary.

## Migration / Rollout

No migration. Purely additive; persisted documents already carry an
`operations` array (`codec._encode_class`).

## Docs Updates (DD11b)

- `docs/ai/DECISIONS_LOG.md` — append a `## 2026-09-16 — Cycle 14 apply`
  entry (matches the existing per-cycle heading convention), recording DD4
  (`null` wire form), DD9 (zero-ops parity math) and DD10 (symbol asymmetry).
- `docs/ai/CURRENT_STATE.md` — rule registry 10 → 11; operations reachable
  end to end; parameters still UI-unreachable.

## Open Questions

- [ ] None blocking. Deferred to a later cycle: UI-reachable parameters, and
      retrofitting `VISIBILITY_SYMBOL` onto attribute lines (DD10).
