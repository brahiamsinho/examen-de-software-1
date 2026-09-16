# Exploration: Relationship kind selection in the web UML canvas (UML 2.5)

## Current State

- **This is a pure frontend gap — backend, domain model, and validation are already fully wired for all 4 UML 2.5 relationship kinds.** `backend/apps/uml_documents/schemas.py`'s `RelationshipIn.kind` is already `Literal["association", "aggregation", "composition", "generalization"]`, `backend/apps/uml_commands/handlers/relationships.py` appends any kind blindly, and validation (`backend/apps/uml_modeling/validation/rules/relationships.py`, wired via `engine.py`) already has a kind-scoped `generalization_cycle` rule and a kind-scoped `self_association` rule, explicitly documented never to overlap. `openspec/specs/uml-domain-model/spec.md`'s Relationship requirement already states the 4-kind enum generically. No backend or domain-model-spec changes needed.
- The frontend hardcodes `"association"` in two independent places that must change together, or TypeScript keeps narrowing the outgoing payload to `"association"` only and silently masks the bug:
  1. `frontend/src/components/workspace/AddRelationshipControl.tsx:93` — `handleSubmit()` builds the `AddRelationship` command literally with `kind: "association"`.
  2. `frontend/src/lib/uml_documents.ts:126` — the `UmlCommandIn` union's `AddRelationship` variant types `kind` as the narrow literal `"association"`. This is distinct from `RelationshipKind` (`uml_documents.ts:69`, already `"association" | "aggregation" | "composition" | "generalization"`), which today is only used for the read-model `Relationship` type, never for the outgoing command.
- **Click-click flow** (`frontend/src/app/(app)/documents/[docId]/page.tsx:75-87`, `handleNodeTap`): first class tap sets `pendingSourceId`, a different second tap sets `pendingTargetId`; a repeat tap on the same class is the cancel gesture (and, per the prior cycle, also the entry point for the explicit "relate to self" affordance). `AddRelationshipControl` renders unconditional source/target multiplicity `<Select>`s (lines 114-146) whenever both ids are set, regardless of kind.
- **Generalization direction is normative in the domain model** (`backend/apps/uml_modeling/domain/elements.py:94-106`): `source` = specific/child, `target` = general/parent. **No equivalent convention exists anywhere — code, tests, or docs — for which endpoint is the "whole" in `aggregation`/`composition`.** This is a genuine open fork, not something to decide unilaterally.
- **Edge rendering** (`frontend/src/components/workspace/DiagramCanvas.tsx`): `toElements()` (lines 175-200) never reads `relationship.kind` — edge `data` carries only `id`, `source`, `target`, `label`, so kind is silently dropped before reaching Cytoscape. The `STYLE` array (lines 104-162) has one generic `edge` selector applying `target-arrow-shape: "triangle"` to every edge unconditionally (plus a separate `edge.self-loop` selector for loop geometry) — there is no per-kind selector and no diamond marker exists today.
- **`RemoveRelationshipControl.tsx:46`** interpolates `r.kind` raw into its option label (`"{sourceName} → {targetName} ({kind})"`) — already kind-agnostic, confirmed zero changes needed there or in its spec section.
- **UML 2.5 notation — verified via research, not assumed:** generalization = solid line, hollow (unfilled) triangular arrowhead at the general/parent end, no multiplicity shown at either end. Aggregation = solid line, hollow (unfilled) diamond at the whole end. Composition = solid line, filled (solid) diamond at the whole end. Association = plain solid line, optional multiplicities and name at either end, no special terminator. This matches the user's own summary.

## Affected Areas

- `frontend/src/lib/uml_documents.ts:126` — widen the `AddRelationship` command's `kind` field to the full `RelationshipKind` union.
- `frontend/src/components/workspace/AddRelationshipControl.tsx:39-165` — add a kind `<Select>`, thread the chosen kind into the submitted command, and conditionally hide the multiplicity selects for `generalization` (per Fork B below).
- `frontend/src/components/workspace/__tests__/AddRelationshipControl.test.tsx` — existing assertions hardcode `kind: "association"`; needs direct updates plus new per-kind cases (Strict TDD: tests first).
- `frontend/src/components/workspace/DiagramCanvas.tsx` — `toElements()` must copy `relationship.kind` into edge `data`; `STYLE` needs per-kind edge selectors (hollow triangle / hollow diamond / filled diamond) replacing today's one-size-fits-all triangle.
- `frontend/src/components/workspace/__tests__/DiagramCanvas.test.tsx` — needs coverage for `kind` propagating into elements and driving the right style class/selector.
- `openspec/specs/web-uml-canvas/spec.md:105-116` (Requirement: Add Relationship Command) — needs a `MODIFIED Requirements` delta; it currently states, verbatim, that click-click "submits one `AddRelationship` command of kind `association`."
- No backend files. `RemoveRelationshipControl.tsx` and its spec section — confirmed no changes.

## Approaches

1. **Add a kind `<Select>` to `AddRelationshipControl`, thread `kind` through the command type, add per-kind Cytoscape style selectors keyed by an edge `kind` data field.** Minimal, localized diff; reuses existing `Select`/`Label` primitives; pure frontend change since backend already supports it. Still requires resolving Fork A below before the diamond-placement style rule can be written correctly. Effort: Low-Medium.
2. **Same as (1), plus an explicit UI-level whole/part convention** — e.g. relabeling "Origen"/"Destino" conditionally for aggregation/composition, or otherwise making the whole/part choice visible in the UI copy rather than silently inheriting raw click order as domain semantics. Self-documents the decision, reduces user confusion about diamond placement, at the cost of more UI copy work. Effort: Medium.

Both converge on the same core code changes.

## Recommendation

Approach 1, with two forks explicitly deferred to the user before drafting the proposal (there is no existing convention in code/tests/docs to resolve either unilaterally):

- **Fork A**: for `aggregation`/`composition`, which endpoint is the "whole" — the first click (`source`) or the second click (`target`)? Generalization already has a normative direction (source=child, target=parent) to mirror for consistency, but aggregation/composition have no equivalent today.
- **Fork B**: for `generalization`, should the multiplicity `<Select>`s be fully hidden (matches UML 2.5 exactly — generalization has no multiplicity — and is cheaper to build), or rendered visibly disabled (extra "doesn't apply here" affordance, slightly more UI work)?

## Risks

- Two independent hardcode sites must change together (`AddRelationshipControl.tsx:93`, `uml_documents.ts:126`) or TypeScript silently keeps the outgoing type narrowed to `"association"` only.
- The current generic `edge` selector already paints every edge with a triangle head (`DiagramCanvas.tsx:127`); scoping it per-kind must not regress plain `association` edges into keeping an errant triangle, and must not break the pinned self-loop geometry (`edge.self-loop`) fixed in the previous cycle.
- Both `AddRelationshipControl.test.tsx` and `DiagramCanvas.test.tsx` need direct updates, not just additions, under Strict TDD Mode.
- Aggregation/composition endpoint semantics are genuinely undecided in the codebase — shipping without an explicit decision risks arbitrary or inconsistent diamond placement across the diagram.

## Open Questions (for the user, before proposal)

1. Fork A — aggregation/composition "whole" endpoint: first click (source) vs. second click (target)?
2. Fork B — generalization multiplicity selects: hidden entirely vs. rendered disabled?

## Scope Decisions (confirmed by user)

1. Fork A: **first click (`source`) = the "whole"** for both `aggregation` and `composition`. The second click (`target`) is the "part". Reads naturally as "A has B" and matches click order, not generalization's source=child convention.
2. Fork B: **hidden completely**. `generalization`'s multiplicity `<Select>`s are not rendered at all, matching UML 2.5 (no multiplicity on generalization) with the least code.

## Ready for Proposal

Yes — both open questions resolved above.
