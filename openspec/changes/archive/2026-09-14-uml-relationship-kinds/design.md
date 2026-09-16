# Design: UML Relationship Kinds

## Technical Approach

Pure frontend, three files. `RelationshipKind` (already exported,
`uml_documents.ts:69`) replaces the narrow `"association"` literal in the
`AddRelationship` command; `AddRelationshipControl` gains one local
`useState<RelationshipKind>` and a `<Select>`; `toElements` copies
`r.kind` into edge `data` and `STYLE` gains three data-attribute
selectors. `backend/` diff is empty: `RelationshipIn.kind`
(`apps/uml_documents/schemas.py:59`) is already
`Literal["association","aggregation","composition","generalization"]`,
`handlers/relationships.py` appends any kind, and no validation rule
constrains multiplicity by kind — only `generalization_cycle` and
`self_association`, both kind-scoped and non-overlapping.

## Decision Drivers

- **Verified in Cytoscape source, not assumed**: `styfn.getContextStyle`
  (`cytoscape.cjs.js:16090-16117`) merges **every** matching context in
  stylesheet order, assigning `style[prop.name] = prop` — later entry wins
  **per property**, with no CSS-style specificity. So a matched selector
  never replaces an earlier one wholesale; it only overrides the exact keys
  it declares.
- Verified defaults: all four `*-arrow-shape` prefixes default to `'none'`
  and `*-arrow-fill` to `'filled'` (`18669-18688`); `arrowShape` enums
  include `triangle` and `diamond`, `arrowFill` enums are exactly
  `filled|hollow` (`17470-17474`).
- `edge.self-loop` (prior cycle, commit 84248e8) is pinned and must not move.
- `RelationshipEndIn.multiplicity` is a **required** `str` — generalization
  cannot simply omit it.
- Controls keep transient state in `useState` and derive the rest at render
  (prior cycle DD2/DD8); no effects.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | Style per kind with **data-attribute** selectors — `edge[kind = "generalization"]` etc. — after adding `kind: r.kind` to edge `data`. `toElements`' `classes` expression stays byte-identical (`self-loop` or `undefined`) | Append `kind-generalization` to the `classes` string, mirroring `self-loop` | `kind` is a real domain field the proposal already requires in `data`; a class string would duplicate the same fact in two places and invent a stringly-typed name. Decisive: `DiagramCanvas.test.tsx:108` asserts `expect(edge.classes).toBe("self-loop")` with exact equality — attribute selectors leave the prior cycle's pinned self-loop assertion untouched, class-string composition would force an edit to it |
| DD2 | **Delete** `"target-arrow-shape": "triangle"` from the generic `edge` selector; add `"source-arrow-color": EDGE_LINE` beside the existing `target-arrow-color`. Association then gets no terminator from the verified `'none'` default and needs **no selector of its own** | Keep the generic triangle and add `edge[kind="association"] { target-arrow-shape: none }` | The blanket triangle is the bug: every edge paints a head today. Removing it makes "plain line" the floor instead of a per-kind undo, so a future kind can only *add* a terminator. `source-arrow-color` must be set explicitly because a hollow arrow is **stroked** with that color (`cytoscape.cjs.js:30083-30086`) and its default `#999` is not `EDGE_LINE` |
| DD3 | Append the three kind rules at the **end** of `STYLE`, after `edge.self-loop`. Each sets only arrow properties; none sets a loop property | Insert them between `edge` and `edge.self-loop`; one combined rule with mapped values | Per the verified merge order, the kind rules and `edge.self-loop` declare **disjoint** property sets (arrows vs. `loop-direction`/`loop-sweep`/`control-point-step-size`/`text-margin-y`), so a self-referencing generalization gets loop geometry *and* a hollow triangle regardless of their relative order — appending just makes "later wins over the generic `edge`" visually obvious in the file. **No conflict with the prior cycle's fix exists** |
| DD4 | Kind `<Select>` renders **only in the both-ids-set confirm branch**, above the multiplicity grid, labelled `Tipo de relación`. Local `useState<RelationshipKind>("association")`; **no prop change** to `AddRelationshipControlProps` | Render it in the pending-source branch so kind is picked first; lift kind to `page.tsx` beside `pendingSourceId` | The pending-source branch is a transient "pick a target on the canvas" prompt; kind has no effect until submit, and the kind→multiplicity visibility coupling (DD5) only exists in the confirm branch — splitting one coupled group across two render branches buys nothing. Kind is not shared with the canvas highlight, unlike the pending ids, so DD8's lift-to-container rationale does not apply |
| DD5 | `generalization` hides both multiplicity `<Select>`s (confirmed scope decision) and `handleSubmit` sends the **literal** `"1"` for both ends when kind is `generalization`, ignoring the hidden state. Changing kind resets **nothing** | Reset both multiplicities to `"1"` on kind change; send the hidden state values | The payload must be a function of what is visible, or a user who picks `0..*`, then switches to generalization, silently posts `0..*`. Deriving at submit (never resetting) also means switching generalization→association restores their earlier choice instead of discarding it — the prior cycle's "derive, don't effect" shape |
| DD6 | Export `STYLE` from `DiagramCanvas.tsx` | Leave it module-private and test notation only through a Cytoscape mock | Same reasoning that exported `toElements` (DD6, prior cycle): the stylesheet is a plain data structure carrying the UML notation contract, assertable with zero DOM and zero canvas. jsdom has no canvas, so rendered arrowheads are untestable by any other means |

## Data Flow

    AddRelationshipControl                    DiagramCanvas
      kind useState ─┐                          model.relationships[].kind
                     ├─→ AddRelationship          │
      pendingSource/ │   .relationship.kind       ▼
      Target (props) ┘        │              toElements → edge.data.kind
                              ▼                          │ (classes: unchanged)
                     POST /commands                      ▼
                     → getDocument ──────────→ STYLE: edge[kind = "…"]
                                                         │
      generalization → multiplicity selects              ▼
      not rendered; payload forced to "1"/"1"   hollow △ / ◇ / ◆ / plain

## Interfaces / Contracts

```ts
// uml_documents.ts — BEFORE                 // AFTER
relationship: { id: string;                 relationship: { id: string;
  kind: "association";                        kind: RelationshipKind;
  ... }                                       ... }
```

```ts
// DiagramCanvas.tsx — appended to STYLE (DD2/DD3)
{ selector: 'edge[kind = "generalization"]',
  style: { "target-arrow-shape": "triangle", "target-arrow-fill": "hollow", "arrow-scale": 1.6 } },
{ selector: 'edge[kind = "aggregation"]',
  style: { "source-arrow-shape": "diamond", "source-arrow-fill": "hollow", "arrow-scale": 1.6 } },
{ selector: 'edge[kind = "composition"]',
  style: { "source-arrow-shape": "diamond", "source-arrow-fill": "filled", "arrow-scale": 1.6 } },
// association: no rule — inherits the verified `'none'` arrow-shape default.
// Diamonds sit at `source` = first click = the "whole" (confirmed decision).
// `arrow-scale` is edge-level (not per-prefix), so each rule overrides the
// generic `edge`'s `1` for its own edges only. 1.6 is tunable, not load-bearing.
```

UI copy (Spanish, matching every `workspace/*` string): `Tipo de relación` →
`Asociación` / `Agregación` / `Composición` / `Generalización`.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/src/lib/uml_documents.ts` | Modify | `kind: RelationshipKind` in the command union; update the adjacent comment |
| `.../workspace/AddRelationshipControl.tsx` | Modify | Kind select + state (DD4); conditional multiplicities and forced `"1"` payload (DD5) |
| `.../workspace/DiagramCanvas.tsx` | Modify | `kind` into edge `data`; drop the blanket triangle; 3 kind rules; export `STYLE` (DD1/DD2/DD3/DD6) |
| `.../__tests__/AddRelationshipControl.test.tsx` | Modify | 5 new cases; one title/docblock correction |
| `.../__tests__/DiagramCanvas.test.tsx` | Modify | Extend 1 assertion; new `kind`-propagation and `STYLE` suites |
| `docs/ai/DECISIONS_LOG.md`, `docs/ai/CURRENT_STATE.md` | Modify | `config.yaml` `rules.design` dual-documentation of DD1–DD6 |
| `backend/**` | **None** | Zero diff — verified at `schemas.py:59` |

## Testing Strategy

**Correction to the proposal's "High" risk row.** Re-reading both suites,
**no existing assertion actually breaks**, because the default kind stays
`"association"`:

| Existing test | Verdict |
|---|---|
| `AddRelationshipControl.test.tsx:110` (`kind: "association"`) | Passes unchanged — **rename only**, to document it as the *default*-kind case |
| `AddRelationshipControl.test.tsx:50` (both multiplicity selects) | Passes unchanged — it is now the association case; needs a generalization counterpart |
| `DiagramCanvas.test.tsx:65` (`toMatchObject`) | Subset match, passes unchanged — **extend** with `kind: "association"` to pin propagation |
| `DiagramCanvas.test.tsx:108` (`edge.classes === "self-loop"`) | **Untouched by DD1** — the self-loop regression guard stays byte-identical |

RED work is therefore additive. New cases:

| Layer | Case |
|---|---|
| Control | Kind select renders 4 options, defaults to `association` |
| Control | Parametrized over all 4 kinds: choosing kind X → `onSubmit` carries `kind: X` |
| Control | `generalization` → **neither** `Multiplicidad origen` nor `Multiplicidad destino` is in the document |
| Control | `generalization` after choosing `0..*` → payload still `"1"`/`"1"` (DD5) |
| Control | `generalization` → back to `association` → the earlier `0..*` is still selected (no reset) |
| `toElements` | Parametrized: `edge.data.kind` equals each of the 4 kinds |
| `toElements` | Self-referencing **generalization** → `classes === "self-loop"` **and** `data.kind === "generalization"` (DD3 composition guard) |
| `STYLE` | The generic `edge` entry declares **no** `target-arrow-shape` key (association is plain) |
| `STYLE` | Each kind selector declares exactly its terminator shape + fill, and **no** kind selector declares any `loop-*`/`control-point-step-size`/`text-margin-y` key |
| `STYLE` | The `edge.self-loop` entry still carries its four prior-cycle properties, unchanged |
| E2E | Deferred — no Cypress harness (`config.yaml` `testing.e2e`) |

Sequence diagram: N/A — no Channels/realtime flow in this cycle.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file
classification, or process-integration boundary. `kind` is a closed union
validated again by Pydantic on arrival.

## Migration / Rollout

No migration, no flag, no data change. Existing persisted relationships
already carry a real `kind`, so previously-created edges immediately render
their correct notation on first load after deploy. `git revert` of three
files (proposal §Rollback Plan).

## Open Questions

- [ ] A hollow terminator is drawn by punching the shape out with
      `globalCompositeOperation = 'destination-out'` and stroking the
      outline (`cytoscape.cjs.js:30074-30086`) — its interior is
      **transparent**, not white, so it shows the canvas container's
      background. Correct on today's light surface; a future dark canvas
      theme would render hollow triangles/diamonds dark-filled and
      indistinguishable from composition. Out of scope here — flag for
      whichever cycle introduces a dark canvas.
- [ ] `arrow-scale: 1.6` against `width: 1.5` is an eyeballed starting
      value, not a measured one. Worth one visual pass during apply.
