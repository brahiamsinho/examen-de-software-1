# Tasks: UML Class Operations

Strict TDD. Spans `backend/` and `frontend/`.

Backend test command: `cd backend && pytest apps/uml_commands apps/uml_documents apps/uml_modeling -q`
Frontend test command: `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/components/workspace/__tests__/AddOperationForm.test.tsx src/components/workspace/__tests__/RemoveOperationControl.test.tsx src/components/workspace/__tests__/DiagramCanvas.test.tsx "src/app/(app)/documents/[docId]/__tests__/page.test.tsx"`
Full regression: `cd backend && pytest -q` and `cd frontend && npm test`

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~950-1150 (commands.py ~25, handlers/operations.py ~30 + test ~90, dispatcher.py ~10, schemas.py ~30, services.py ~20 + tests ~90, diagnostics.py ~5, naming.py ~30 + tests ~60, engine.py rename ~10, AddOperationForm.tsx ~80 + test ~130, RemoveOperationControl.tsx ~50 + test ~90, DiagramCanvas.tsx ~50 + test ~120, page.tsx ~20 + test update ~20, docs ~60) |
| 800-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend: commands/handlers/dispatcher/schemas/services), PR 2 (backend: validation rule + rule-count test), PR 3 (frontend: types/forms/mount + canvas + docs) |
| Delivery strategy | ask-on-risk |
| Chain strategy | size:exception — user accepted a single PR despite exceeding the 800-line budget |

Decision needed before apply: Resolved
Chained PRs recommended: Yes (declined by user)
Chain strategy: size:exception, single PR
800-line budget risk: High (accepted)

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Command bus: `AddOperation`/`RemoveOperation` dataclasses, handler, dispatcher wiring, wire schemas, `services.py` mapping | PR 1 | `cd backend && pytest apps/uml_commands apps/uml_documents -q` | `cd backend && python manage.py shell` — apply `AddOperation` via dispatcher against a fixture document, confirm operation appended | `git revert`; union shrinks 9→7, `_HANDLERS` drops 2 entries, schemas/services branches removed |
| 2 | Validation: `DUPLICATE_OPERATION_NAME` rule, registry 10→11, rule-count test rename | PR 2 (base: PR 1 branch) | `cd backend && pytest apps/uml_modeling -q` | N/A — pure validation logic, exercised only by the pytest suite | `git revert`; `RULES` reverts to 10, `naming.py` rule removed |
| 3 | Frontend: TS union, `AddOperationForm`/`RemoveOperationControl`, `page.tsx` mount, canvas operations compartment, docs | PR 3 (base: PR 2 branch) | `cd frontend && npx vitest run src/lib/__tests__/uml_documents.test.ts src/components/workspace/__tests__/AddOperationForm.test.tsx src/components/workspace/__tests__/RemoveOperationControl.test.tsx src/components/workspace/__tests__/DiagramCanvas.test.tsx "src/app/(app)/documents/[docId]/__tests__/page.test.tsx"` | `cd frontend && npm run dev` + manual: add operation with/without return type, confirm canvas rendering, remove it | `git revert`; 2 new components + mounts + canvas compartment removed, TS union drops 2 variants |

## Phase 1: Command Dataclasses (`commands.py`)

- [x] 1.1 RED: extend `backend/apps/uml_commands/tests/test_commands.py` — `AddOperation(class_id, operation: UmlOperation)` and `RemoveOperation(class_id, operation_id)` construct with documented fields, both frozen; `typing.get_args()` on `UmlCommand` covers exactly 9 types.
- [x] 1.2 GREEN: modify `backend/apps/uml_commands/commands.py` — import `UmlOperation`, add both dataclasses, grow the `UmlCommand` union 7→9 (DD1).

## Phase 2: Operation Handlers (`handlers/operations.py`)

- [x] 2.1 RED: create `backend/apps/uml_commands/tests/handlers/test_operations.py` — `add_operation` appends the `UmlOperation` preserving existing operations and order; `add_operation` on an unknown class id returns the same unchanged `model` object; `remove_operation` removes the matching operation preserving relative order of the rest; `remove_operation` on an unknown class id or unknown operation id returns the same unchanged `model` object.
- [x] 2.2 GREEN: create `backend/apps/uml_commands/handlers/operations.py` — verbatim mirror of `handlers/attributes.py`, `attribute`→`operation` (DD2).

## Phase 3: Dispatcher Wiring (`dispatcher.py`)

- [x] 3.1 RED: extend `backend/apps/uml_commands/tests/test_dispatcher.py` — `_HANDLERS` now has exactly 9 entries; `AddOperation`/`RemoveOperation` route through the real dispatcher end to end (model content updates, revision +1, no exception on unknown ids).
- [x] 3.2 GREEN: modify `backend/apps/uml_commands/dispatcher.py` — import `AddOperation`/`RemoveOperation`, `add_operation`/`remove_operation`; register both `_HANDLERS` entries after the attribute pair (DD3).

## Phase 4: Wire Schemas (`schemas.py`)

- [x] 4.1 RED: extend `backend/apps/uml_documents/tests/test_schemas.py` — `AddOperationIn`/`RemoveOperationIn` discriminate correctly inside `CommandIn`; `UmlOperationIn.return_type` accepts `null` and omission (defaults `None`); parses a primitive `return_type` string; `visibility` defaults `"public"`.
- [x] 4.2 GREEN: modify `backend/apps/uml_documents/schemas.py` — add `UmlOperationIn`, `AddOperationIn`, `RemoveOperationIn`; add both to the `CommandIn` discriminated union (DD4).

## Phase 5: Payload Mapping (`services.py`) — not in proposal's Affected Areas table

- [x] 5.1 RED: extend `backend/apps/uml_documents/tests/test_services.py` — `_command_from_payload` maps `AddOperationIn`/`RemoveOperationIn` to `AddOperation`/`RemoveOperation`; `return_type: null` maps to `None`; an omitted `return_type` maps to `None`; a valid primitive `return_type` string maps via `codec._decode_attribute_type`; `return_type: ""` raises `InvalidCommandPayloadError` (422 semantics); `parameters` is always `()` on the mapped `UmlOperation`.
- [x] 5.2 GREEN: modify `backend/apps/uml_documents/services.py` — add two `isinstance` branches to `_command_from_payload` (after line 208) and a new `_operation_from_schema` helper mirroring `_attribute_from_schema` (DD4, design's explicit callout — file missing from proposal.md's table).

## Phase 6: Duplicate Operation Name Rule

- [x] 6.1 RED: extend `backend/apps/uml_modeling/tests/test_rules_naming.py` — one class with two operations named `crearUsuario` (any return types) raises `DUPLICATE_OPERATION_NAME` `ERROR`, scoped to that class; the same name in two different classes raises nothing; a class with an operation named `""` still raises `EMPTY_ELEMENT_NAME`.
- [x] 6.2 GREEN: modify `backend/apps/uml_modeling/validation/diagnostics.py` — add `DUPLICATE_OPERATION_NAME = "DUPLICATE_OPERATION_NAME"` after `DUPLICATE_ATTRIBUTE_NAME` (DD5).
- [x] 6.3 GREEN: modify `backend/apps/uml_modeling/validation/rules/naming.py` — copy `duplicate_attribute_name`, iterate `uml_class.operations` with a per-class `seen: set[str]`, emit `operation_path(uml_class.id, operation.id)` and `ElementKind.OPERATION`, name-only comparison (DD5).
- [x] 6.4 GREEN: modify `backend/apps/uml_modeling/validation/engine.py` — import the new rule, insert at index 3 immediately after `duplicate_attribute_name`; `RULES` becomes 11 (DD5).

## Phase 7: Rule-Count Test (DD6)

- [x] 7.1 RED→GREEN: rename `test_registry_has_exactly_ten_rules`→`test_registry_has_exactly_eleven_rules` in `backend/apps/uml_modeling/tests/test_engine.py`, assert `len(RULES) == 11`; update the stale "exactly 10 rules" prose in `engine.py:7` and the `RULES` comment (lines 30-32).
- [x] 7.2 (deviation, not in original task list) fix two pre-existing regressions surfaced by the registry growing to 11: renamed `test_diagnostic_code_has_exactly_the_ten_cycle_one_codes`→`..._eleven_cycle_one_codes` in `test_diagnostics.py`, and updated `test_validation_integration.py`'s full-registry fixture/assertion (10→11 diagnostics) to also exercise `DUPLICATE_OPERATION_NAME`.

## Phase 8: TS Command Union (`lib/uml_documents.ts`)

- [x] 8.1 RED: extend `frontend/src/lib/__tests__/uml_documents.test.ts` — `submitCommand` forwards `AddOperation`/`RemoveOperation` verbatim as the JSON body (DD7 field names, including `return_type: null`).
- [x] 8.2 GREEN: modify `frontend/src/lib/uml_documents.ts` — add both `UmlCommandIn` variants; update the block comment to "eight of the nine" (DD7).

## Phase 9: Add Operation Form (`AddOperationForm.tsx`)

- [x] 9.1 RED: create `frontend/src/components/workspace/__tests__/AddOperationForm.test.tsx` — class select, name input, return-type select with first option "Sin tipo de retorno" followed by `PRIMITIVE_TYPES`, visibility select defaulting `public`; submitting with a return type selected sends `return_type` as that primitive; submitting with "Sin tipo de retorno" sends `return_type: null`; no parameter input rendered, no `parameters` field on the wire (v1 always sends none — the wire `UmlCommandIn` shape carries no `parameters` field per DD7, server-side always `()`); `resolvedClassId` re-derives when the initially-selected class disappears from `classes` (mirrors `AddAttributeForm`'s documented bug fix).
- [x] 9.2 GREEN: create `frontend/src/components/workspace/AddOperationForm.tsx` — mirror of `AddAttributeForm.tsx`, props `{ classes, onSubmit, disabled }`, `id: crypto.randomUUID()` (DD8).

## Phase 10: Remove Operation Control (`RemoveOperationControl.tsx`)

- [x] 10.1 RED: create `frontend/src/components/workspace/__tests__/RemoveOperationControl.test.tsx` — operation select scoped to the chosen class's operations; changing class clears the operation selection; submission sends `RemoveOperation` immediately with no confirmation step.
- [x] 10.2 GREEN: create `frontend/src/components/workspace/RemoveOperationControl.tsx` — mirror of `RemoveAttributeControl.tsx`, ids derived fresh per render (DD8).

## Phase 11: Mount Points (`page.tsx`)

- [x] 11.1 RED: extend `frontend/src/app/(app)/documents/[docId]/__tests__/page.test.tsx` — an "Operación" card renders after the "Atributo" card under "Agregar" and under "Eliminar", wired to `submitCommand`/`isSubmitting`.
- [x] 11.2 GREEN: modify `frontend/src/app/(app)/documents/[docId]/page.tsx` — mount `AddOperationForm` (after Atributo, before `AddRelationshipControl`) and `RemoveOperationControl` (after Atributo, before the Relación card), same `classes`/`onSubmit`/`disabled` props (DD8).

## Phase 12: Operations Compartment (`DiagramCanvas.tsx`)

- [x] 12.1 RED: extend `frontend/src/components/workspace/__tests__/DiagramCanvas.test.tsx` — a class with one attribute and one operation (`crearUsuario`, return type `Usuario`, public) renders `+ crearUsuario(): Usuario` in a second compartment below attributes, separated by a divider; an operation with no return type renders without a `: {returnType}` suffix; a class with zero operations renders byte-identically to today (same SVG string, `width`, `height` as the attribute-only case).
- [x] 12.2 GREEN: modify `frontend/src/components/workspace/DiagramCanvas.tsx` — `classBoxSvgDataUri(name, attributeLines, operationLines = [])`; additive-only `width`/`opAreaHeight`/`height`/`opDividerY`/`opStartY` math (DD9); add `VISIBILITY_SYMBOL` map and build `operationLines` from `c.operations` in `toElements` (DD10).

## Phase 13: Documentation (DD11)

- [x] 13.1 Append a `## 2026-09-16 — Cycle 14 apply` entry to `docs/ai/DECISIONS_LOG.md` recording DD4 (`null` wire form), DD9 (zero-ops parity math), DD10 (symbol asymmetry), following the existing per-cycle heading convention.
- [x] 13.2 Update `docs/ai/CURRENT_STATE.md` — rule registry 10→11; operations reachable end to end; parameters still UI-unreachable.

## Phase 14: Verification

- [x] 14.1 Run `cd backend && pytest -q`; confirm all `AddOperation`/`RemoveOperation`/`DUPLICATE_OPERATION_NAME` scenarios pass, registry at 11, zero regressions. **Result: 384/384 passed.**
- [x] 14.2 Run `cd frontend && npm test`; confirm all Add/Remove Operation Command and Diagram Rendering scenarios pass, zero-ops SVG parity holds, zero regressions. **Result: 335/335 passed (54 files).**
- [x] 14.3 Run `cd frontend && npm run lint` and `cd frontend && npm run build`; confirm zero new warnings, clean typecheck/build. **Result: `eslint` clean (no output); `next build` compiled successfully, TypeScript checked clean, all 12 routes generated.**
- [x] 14.4 Manual two-client check: operation round-trips through save/reload and broadcasts live to a second collaborator (proposal Success Criteria; design defers automated E2E). **Not run as a real browser check (outside this agent's scope, per design.md's deferred-E2E note) — reasoned about instead: `AddOperation`/`RemoveOperation` route through the identical `submit_command` → `broadcast_document` → `DocumentConsumer` → `document.update` path already proven end-to-end by Cycles 7-13's WS suite and `test_submit_command_broadcasts_exactly_once_after_commit`; `codec.document_out` already serializes `operations` (zero codec changes this cycle), so the wire payload a second client receives already carries the new operation. Flagged as a follow-up for the maintainer to confirm visually, consistent with this project's established docker-lifecycle convention for real-browser checks.**
