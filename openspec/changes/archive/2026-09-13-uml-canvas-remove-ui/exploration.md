# Exploration: UML canvas "remove" UI (class, attribute, relationship)

## Current State

- **Backend/API is already fully wired for all 3 remove commands — this is a pure frontend cycle, correcting the initial framing.** `backend/apps/uml_documents/schemas.py`'s `CommandIn` discriminated union already includes `RemoveClassIn`, `RemoveAttributeIn`, `RemoveRelationshipIn`, and `services.py::_command_from_payload` already maps all 7 payload types to real domain commands, covered by passing tests. The "only 3 of 7 wired" description applies only to the **frontend** TS union (`UmlCommandIn` in `frontend/src/lib/uml_documents.ts`), whose own comment says so explicitly. No backend/API changes are needed.
- `RemoveClass` (`backend/apps/uml_commands/handlers/classes.py::remove_class`) **cascades**: it drops the class AND every relationship referencing it as source or target, silently, in one command application. No-op on unknown id. `CommandResultOut` still returns only `{revision, validation}` — it never reports how many relationships got cascade-removed.
- `RemoveAttribute`/`RemoveRelationship` are simple filters, also no-ops on unknown ids.
- **Frontend interaction surface today**: `DiagramCanvas.tsx` binds only `cy.on("tap", "node", ...)`. There is no edge tap handler at all (edges have zero interactivity today) and no right-click/`cxttap` handler. Node tap already drives the add-relationship click-click state machine in `page.tsx` (`pendingSourceId`/`pendingTargetId`). Any new node-tap-based removal trigger collides with this existing flow.
- Attributes are baked into each class node's multi-line label (DD7 from the prior cycle) — not separate Cytoscape elements, so there's no per-attribute tap target today. Removing one attribute needs either a list-based UI outside the canvas, or a change to the pinned/tested `toElements` rendering contract.

## Affected Areas

- `frontend/src/lib/uml_documents.ts` — extend `UmlCommandIn` with 3 remove-command shapes; update stale doc comment.
- `frontend/src/app/(app)/documents/[docId]/page.tsx` — new state for removal selection; wiring for 3 new components.
- New components, following the existing `onSubmit`-prop presentational convention (`AddAttributeForm.tsx`, `AddRelationshipControl.tsx`).
- No backend files affected.

## Approaches — removal interaction model

1. **Right-click/context-menu (`cxttap`)** on canvas nodes/edges — Pros: no collision with the existing left-`tap` relationship flow, same gesture for class+relationship. Cons: no touch/mobile equivalent, low discoverability, attribute removal still needs a separate list UI regardless (2 paradigms coexist). Effort: Medium.
2. **"Remove mode" toggle** repurposing left-`tap`. Pros: works on touch, single gesture. Cons: mode-tracking risk (accidental deletion while adding a relationship), complicates `handleNodeTap`, still needs a list UI for attributes. Effort: Medium-High.
3. **Selection-list UI outside the canvas** (mirrors `AddAttributeForm`'s `<select>` pattern) for all 3 types. Pros: zero collision with the existing click-click flow, unifies all 3 removal types under one paradigm — attribute removal forces a list UI regardless, so reusing it everywhere avoids mixing two paradigms, reuses proven form conventions. Cons: doesn't use the canvas directly as the removal surface. Effort: Low-Medium.

## Recommendation

Approach 3 (selection-list UI). Attribute removal has no viable canvas-gesture option under the current DD7 label-rendering contract, so a list UI is unavoidable for at least one of the three types either way — standardizing on it avoids mixing two interaction paradigms in one cycle.

## Risks

- Cascading class removal has no server-side signal of what else was removed; a pre-removal warning must be computed client-side from the already-loaded `document.model.relationships` (same pattern as `page.tsx`'s existing `danglingRelationshipCount`).
- No edge interaction exists today at all — relationship removal is new interaction surface regardless of approach.
- Attribute label rendering is a tested, pinned contract (`DiagramCanvas.test.tsx`'s fixture) — making attributes individually tappable would be a materially bigger, riskier change than an outside-canvas list.

## Open Questions (for the user, before proposal)

1. Removal interaction model: selection-list UI outside the canvas (Approach 3) vs. right-click context-menu vs. a remove-mode toggle.
2. Whether cascading class removal needs a confirmation dialog warning how many relationships will also be removed.
3. Whether single-element removal (one attribute, one relationship) needs a confirmation step, or removes immediately on click.

## Scope Decisions (confirmed by user)

1. Removal interaction model: **selection-list UI** outside the canvas (Approach 3), mirroring `AddAttributeForm`'s `<select>` pattern.
2. Cascading class removal: **confirmation dialog required**, showing how many relationships will also be removed (computed client-side from `document.model.relationships`).
3. Single-element removal (one attribute, one relationship): **no confirmation**, removes immediately — non-blocking, same spirit as the rest of this cycle.

## Ready for Proposal

Yes — all open questions resolved above.
