# Exploration: Add operations/methods to a UML class

## Current State

Domain layer is fully built and idle: `UmlOperation`/`UmlParameter`
(`backend/apps/uml_modeling/domain/elements.py`) and `UmlClass.operations`
exist with zero production callers. More surprisingly, the codec
(`backend/apps/uml_documents/codec.py`) ALREADY has `_encode_operation`/
`_decode_operation`/`_encode_parameter`/`_decode_parameter` wired into
`_encode_class`/`_decode_class` (lines 95-101, 133-163) — operations
already round-trip through JSON persistence even though nothing ever
produces a non-empty tuple. Validation also has partial operation support
already: `ElementKind.OPERATION` and `operation_path()` exist
(`diagnostics.py`), and `empty_element_name` (`naming.py`) already
iterates `uml_class.operations` via
`CanonicalUmlModel.iter_named_elements()` (`model.py:37-47`), so empty-name
checking on operations already works today. What's missing is everything
in the write path: no `AddOperation`/`RemoveOperation` command, no
handler, no request schema, no frontend command variant, no form UI, no
canvas rendering, and no duplicate-name rule for operations.

## Affected Areas

- `backend/apps/uml_commands/commands.py` — add `AddOperation`/
  `RemoveOperation` frozen dataclasses (mirror `AddAttribute`/
  `RemoveAttribute`, lines 31-40) and extend the closed `UmlCommand` union
  (lines 53-61).
- `backend/apps/uml_commands/handlers/operations.py` (new file) — mirror
  `handlers/attributes.py` exactly: `add_operation`/`remove_operation`,
  same `class_by_id` short-circuit-to-unchanged-model pattern.
- `backend/apps/uml_commands/dispatcher.py` — import new handlers,
  register in `_HANDLERS` dict (lines 32-40).
- `backend/apps/uml_documents/schemas.py` — add `UmlParameterIn`,
  `UmlOperationIn` (mirror `UmlAttributeIn`, lines 32-37; note
  `return_type: str | dict | None`), `AddOperationIn`/`RemoveOperationIn`
  (mirror lines 39-49), and extend the `CommandIn` discriminated union
  (lines 75-86).
- `backend/apps/uml_modeling/validation/diagnostics.py` — add
  `DiagnosticCode.DUPLICATE_OPERATION_NAME` (the `ElementKind.OPERATION`/
  `operation_path` plumbing already exists).
- `backend/apps/uml_modeling/validation/rules/naming.py` — add
  `duplicate_operation_name`, exact mirror of `duplicate_attribute_name`
  (lines 95-115), scoped per class.
- `backend/apps/uml_modeling/validation/engine.py` — register the new
  rule in `RULES` (currently exactly 10, lines 33-44) — this becomes 11.
- `backend/apps/uml_modeling/tests/test_engine.py:49-50` —
  `test_registry_has_exactly_ten_rules` hard-asserts `len(RULES) == 10`;
  MUST be updated to 11 or the whole rule addition breaks CI. Comment on
  `RULES` ("exactly the 10 fixed rules (uml-validation spec)") also needs
  updating.
- `frontend/src/lib/uml_documents.ts` — extend `UmlCommandIn` union
  (lines 116-136) with `AddOperation`/`RemoveOperation` variants.
  `UmlOperation` type already exists (lines 46-52).
- `frontend/src/components/workspace/AddOperationForm.tsx` (new) — mirror
  `AddAttributeForm.tsx`: class select, name input, return-type select
  (reuse `PRIMITIVE_TYPES`, but must be optional/nullable unlike
  attribute type), visibility, and — pending the open question below — a
  parameter list.
- `frontend/src/components/workspace/RemoveOperationControl.tsx` (new) —
  mirror `RemoveAttributeControl.tsx` exactly (class select → operation
  select → submit).
- `frontend/src/components/workspace/DiagramCanvas.tsx` —
  `classBoxSvgDataUri` (lines 79-108) only accepts `attributeLines:
  string[]` and draws one divider; needs an `operationLines` param, a
  second divider, and height/width math extended for the operations
  compartment. `toElements` (lines 231-243) only builds `attributeLines`
  from `c.attributes`; needs a symmetric `operationLines` built from
  `c.operations`, formatted per real UML notation, e.g.
  `+ crearUsuario(nombre: String): Usuario`.
- Wherever `AddAttributeForm`/`RemoveAttributeControl` are mounted in the
  workspace panel (not yet located — a 1-file grep away) will need the
  new operation components added alongside them.

## Approaches

1. **Full parity v1 (name + return type + visibility + dynamic parameter
   list)** — mirror the domain model's full capability in the UI.
   - Pros: no follow-up cycle needed; UI and domain stay in lockstep;
     parameter list is exercised end-to-end immediately.
   - Cons: meaningfully more UI work — a dynamic add/remove parameter
     sub-form with its own type select per row, more form state, more
     validation surface, more test cases.
   - Effort: Medium-High

2. **Reduced v1 (name + return type + visibility, zero parameters)** —
   ship without a parameter UI; `AddOperationIn`/domain call still passes
   `parameters: ()`.
   - Pros: much smaller form (near-identical clone of
     `AddAttributeForm.tsx`); faster to ship and review; matches the
     existing PR-size discipline in this repo.
   - Cons: UML notation for a method with no params looks limited
     (`+ crearUsuario(): Usuario` is valid UML but incomplete); parameters
     remain unreachable from the UI despite already being modeled and
     persisted; needs a clearly flagged follow-up cycle.
   - Effort: Low-Medium

3. **Reduced v1 with a single flat parameter string** (e.g. one text
   input parsed as `"nombre: String, edad: Integer"`) — compromise
   between the two.
   - Pros: parameters reachable without a dynamic-rows UI.
   - Cons: fragile parsing, poor UX/error surface, doesn't match the
     typed `UmlParameter{name,type}` shape cleanly, likely needs
     throwaway parsing code that a later "real" parameter UI would
     replace anyway.
   - Effort: Low-Medium, but arguably wasted effort

## Recommendation

Approach 2 (reduced v1, defer the parameter list). It mirrors the
existing `AddAttribute` pattern almost verbatim, keeps the PR inside the
repo's review-workload guard, and the domain/codec/validation layers
already support `parameters` losslessly — adding a parameter-rows UI
later is additive, not a rework. This is a judgment call for the user,
not a decision to make silently.

## Risks

- `test_registry_has_exactly_ten_rules` will fail the moment
  `duplicate_operation_name` is added to `RULES`; must be updated in the
  same change, not forgotten.
- `UmlCommand`/`CommandIn`/`UmlCommandIn` are three independently-
  maintained closed unions (Python dataclass union, Pydantic
  discriminated union, TS union) that must all move together — the same
  triple-touch-point pattern the attribute feature already established,
  but easy to miss one side.
- `classBoxSvgDataUri`'s width/height math is hand-rolled pixel
  arithmetic (`estimateTextWidth`, `PADDING_X/Y`, `ATTR_LINE_HEIGHT`,
  etc.) — adding an operations compartment risks subtly breaking existing
  attribute-only layout/tests (`DiagramCanvas.test.tsx`) if not done
  carefully; visual regression is easy to introduce here without a human
  looking at the render.
- `return_type` is nullable (`AttributeType | None`) unlike attribute
  `type` (never null) — every layer (schema, codec, form, canvas
  formatting) must handle the "no return type" (void-like) case
  distinctly from attributes' always-present type.
- Not yet located: where `AddAttributeForm`/`RemoveAttributeControl` are
  actually mounted in the workspace panel component tree — needed to wire
  up the new operation controls; should be a quick follow-up grep, not a
  blocker to this exploration.

## Open Questions (for the user, before proposal)

1. **Parameter list scope for v1**: ship operations with zero
   UI-reachable parameters now (matches existing `AddAttribute`
   complexity, fast, defer a dynamic parameter-rows UI to a later cycle),
   or build the full dynamic add/remove parameter list in this same
   change (more complete, meaningfully more UI/test surface)?
2. Should `duplicate_operation_name` be scoped per-class only (mirroring
   `duplicate_attribute_name`), or should it also consider overload-style
   same-name-different-signature operations as non-duplicate — real UML
   permits overloading? The current attribute rule has no such nuance to
   mirror.

## Scope Decisions (confirmed by user)

1. **Parameters**: deferred. v1 ships operations with name + return type
   (nullable) + visibility only — `parameters` stays `()` from the UI's
   command payload. The domain/codec already support a non-empty
   `parameters` tuple losslessly, so a later cycle adding a dynamic
   parameter-rows UI is additive, not a rework.
2. **Duplicate names**: operation name MUST be unique per class,
   regardless of signature — no overload support. `duplicate_operation_name`
   mirrors `duplicate_attribute_name` exactly (name-only comparison,
   scoped per class), no signature-comparison logic needed.

## Ready for Proposal

Yes — both open questions resolved above.
