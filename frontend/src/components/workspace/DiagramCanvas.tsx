"use client";

import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import fcose from "cytoscape-fcose";
import { useEffect, useRef, type RefObject } from "react";

import { type JoinTableHint } from "@/lib/join_tables";
import {
  attributeTypeLabel,
  formatMultiplicity,
  type DiagramLayout,
  type UmlModel,
  type Visibility,
} from "@/lib/uml_documents";

// Module scope, guarded by nothing (design.md DD5): `cytoscape.use` on an
// already-registered extension warns, and module scope runs once per bundle.
cytoscape.use(fcose);

// Literal hex values mirroring this project's `globals.css` design tokens
// (Cytoscape's canvas renderer needs resolved colors/fonts, not CSS custom
// properties or `var(--font-*)` — those never reach `ctx.font`/fillStyle).
// `--card`/`--foreground`/`--border` are near-achromatic in oklch, so these
// are their sRGB equivalents; `STRUCTURE_BORDER` is a deliberately distinct,
// slightly cooler gray from the plain UI `--border` token — form fields get
// a neutral hairline, but a class box needs a boundary the eye can pick out
// against a canvas full of other boxes.
const CARD_BG = "#FFFFFF";
const INK = "#1A1A1A";
const STRUCTURE_BORDER = "#D8DBE0";
const ATTR_TEXT = "#3A3A3A";
const EDGE_LINE = "#9CA3AF";
const EDGE_TEXT = "#4B4B4B";
const SELECTED_BORDER = "#3454D1"; // --primary
const LOCKED_REMOTE_BORDER = "#D97706"; // amber-600, distinct from SELECTED_BORDER's blue

const SANS_FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
const MONO_FONT_STACK = "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";

const NAME_FONT_SIZE = 15;
const ATTR_FONT_SIZE = 12;
const NAME_LINE_HEIGHT = 24;
const ATTR_LINE_HEIGHT = 18;
const DIVIDER_MARGIN = 8;
const PADDING_X = 14;
const PADDING_Y = 10;
const MIN_BOX_WIDTH = 150;

// No existing symbol convention: `toElements`'s attribute line below still
// hardcodes `- ${a.name}: ...` and ignores `a.visibility` entirely
// (deliberately left untouched — see DD10 in design.md). Operations DO
// collect visibility, so this map is used for operation lines only.
const VISIBILITY_SYMBOL: Record<Visibility, string> = {
  public: "+",
  private: "-",
  protected: "#",
  package: "~",
};

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/**
 * `toElements` has no DOM/canvas access (DD6, kept from the prior cycle), so
 * text width can't be measured with `measureText` — this is a documented
 * approximation (average em-width per character), good enough to size a box
 * without clipping typical class/attribute names, not pixel-exact.
 */
function estimateTextWidth(text: string, fontSize: number, emWidth: number): number {
  return text.length * fontSize * emWidth;
}

/**
 * Renders one class as a self-contained SVG data URI: a real UML class box
 * (name compartment / divider / attribute compartment), the way
 * StarUML/Enterprise Architect/draw.io draw one — not a single flat
 * Cytoscape text label. Cytoscape has no per-side border property and no
 * per-line font styling within one label (confirmed against
 * `node_modules/cytoscape/index.d.ts`'s `Css.Node`/`Labels` interfaces), so
 * a hand-built SVG background image is the deterministic way to get a bold
 * name row, a real divider rule, and monospaced attribute rows in one box —
 * compound child nodes were the other option, but force-directed layouts
 * (fcose) don't guarantee unconnected siblings stack vertically, which this
 * approach sidesteps entirely.
 */
function classBoxSvgDataUri(
  name: string,
  attributeLines: string[],
  operationLines: string[] = [],
): { uri: string; width: number; height: number } {
  const nameWidth = estimateTextWidth(name, NAME_FONT_SIZE, 0.58);
  const attrWidths = attributeLines.map((line) => estimateTextWidth(line, ATTR_FONT_SIZE, 0.62));
  const opWidths = operationLines.map((line) => estimateTextWidth(line, ATTR_FONT_SIZE, 0.62));
  const width = Math.max(MIN_BOX_WIDTH, PADDING_X * 2 + Math.max(nameWidth, ...attrWidths, ...opWidths, 0));

  const attrAreaHeight =
    attributeLines.length > 0 ? attributeLines.length * ATTR_LINE_HEIGHT : ATTR_LINE_HEIGHT * 0.6;
  // Additive-only (DD9): zero operations contributes exactly 0, so `height`
  // is untouched from the pre-operations-cycle expression below.
  const opAreaHeight =
    operationLines.length > 0 ? DIVIDER_MARGIN * 2 + operationLines.length * ATTR_LINE_HEIGHT : 0;
  const height = PADDING_Y * 2 + NAME_LINE_HEIGHT + DIVIDER_MARGIN * 2 + attrAreaHeight + opAreaHeight;

  const dividerY = PADDING_Y + NAME_LINE_HEIGHT + DIVIDER_MARGIN;
  const nameBaselineY = PADDING_Y + NAME_LINE_HEIGHT * 0.68;
  const attrStartY = dividerY + DIVIDER_MARGIN;
  // Symmetric with the name divider's own margin above/below it.
  const opDividerY = attrStartY + attrAreaHeight + DIVIDER_MARGIN;
  const opStartY = opDividerY + DIVIDER_MARGIN;

  const attrText = attributeLines
    .map(
      (line, i) =>
        `<text x="${PADDING_X}" y="${attrStartY + i * ATTR_LINE_HEIGHT + ATTR_LINE_HEIGHT * 0.72}" font-family="${MONO_FONT_STACK}" font-size="${ATTR_FONT_SIZE}" fill="${ATTR_TEXT}">${escapeXml(line)}</text>`,
    )
    .join("");

  // Emitted only when there is at least one operation (DD9): an empty
  // `operationLines` contributes an empty string, so the SVG for a
  // zero-operations class is byte-identical to before this cycle.
  const opDivider =
    operationLines.length > 0
      ? `<line x1="0" y1="${opDividerY}" x2="${width}" y2="${opDividerY}" stroke="${STRUCTURE_BORDER}" stroke-width="1.5"/>`
      : "";
  const opText = operationLines
    .map(
      (line, i) =>
        `<text x="${PADDING_X}" y="${opStartY + i * ATTR_LINE_HEIGHT + ATTR_LINE_HEIGHT * 0.72}" font-family="${MONO_FONT_STACK}" font-size="${ATTR_FONT_SIZE}" fill="${ATTR_TEXT}">${escapeXml(line)}</text>`,
    )
    .join("");

  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">` +
    `<rect x="0.75" y="0.75" width="${width - 1.5}" height="${height - 1.5}" fill="${CARD_BG}" stroke="${STRUCTURE_BORDER}" stroke-width="1.5"/>` +
    `<text x="${width / 2}" y="${nameBaselineY}" font-family="${SANS_FONT_STACK}" font-size="${NAME_FONT_SIZE}" font-weight="700" fill="${INK}" text-anchor="middle">${escapeXml(name)}</text>` +
    `<line x1="0" y1="${dividerY}" x2="${width}" y2="${dividerY}" stroke="${STRUCTURE_BORDER}" stroke-width="1.5"/>` +
    attrText +
    opDivider +
    opText +
    `</svg>`;

  return { uri: `data:image/svg+xml,${encodeURIComponent(svg)}`, width, height };
}

export const STYLE: cytoscape.StylesheetStyle[] = [
  {
    selector: "node",
    style: {
      label: "",
      shape: "rectangle",
      "background-color": CARD_BG,
      "background-image": "data(bgImage)",
      "background-fit": "cover",
      "border-width": 0,
      width: "data(width)",
      height: "data(height)",
    },
  },
  {
    selector: "node.selected-source",
    style: { "border-width": 3, "border-color": SELECTED_BORDER, "border-style": "solid" },
  },
  {
    // A join-table hint (design.md DD177): not a real class, just a
    // preview of the intermediate table a both-ends-many association
    // implies — dashed border reads as "derived", never confusable with a
    // solid-bordered, editable class box. Draggable (design.md DD178) so
    // the user can move it clear of other boxes; still never claims a
    // collaboration lock (see `applyLocks`).
    selector: "node.join-table-hint",
    style: { "border-width": 1.5, "border-color": EDGE_LINE, "border-style": "dashed" },
  },
  {
    // Foreign-held node (design.md DD12): `ungrabify()` on the same node
    // is what actually prevents a local drag (no `grab` event fires at
    // all) — this class is purely the visual affordance identifying it as
    // locked, dashed and amber so it reads distinctly from the solid blue
    // `selected-source` border above.
    selector: "node.locked-remote",
    style: { "border-width": 2, "border-color": LOCKED_REMOTE_BORDER, "border-style": "dashed" },
  },
  {
    selector: "edge",
    style: {
      label: "data(label)",
      // The relationship name sits at the middle of the line; each end's
      // multiplicity is drawn next to its own class (UML 2.5 notation).
      "source-label": "data(sourceLabel)",
      "target-label": "data(targetLabel)",
      "source-text-offset": 28,
      "target-text-offset": 28,
      "curve-style": "bezier",
      "line-color": EDGE_LINE,
      "target-arrow-color": EDGE_LINE,
      // A hollow arrow/diamond is stroked with this color (verified in
      // `cytoscape.cjs.js:30083-30086`); its default `#999` is not
      // `EDGE_LINE`, so it must be set explicitly even though nothing on
      // this generic selector uses `source-arrow-shape` (DD2).
      "source-arrow-color": EDGE_LINE,
      width: 1.5,
      "arrow-scale": 1,
      "font-family": MONO_FONT_STACK,
      "font-size": 11,
      color: EDGE_TEXT,
      // Lets a tap on the name/multiplicity labels count as a tap on the edge.
      "text-events": "yes",
      "text-background-color": CARD_BG,
      "text-background-opacity": 1,
      "text-background-padding": "3px",
      "text-background-shape": "roundrectangle",
    },
    // No `target-arrow-shape`/`source-arrow-shape` here (DD2): both
    // prefixes default to `'none'`, so a plain `association` edge needs no
    // selector of its own — "no terminator" is the floor, and each kind
    // rule below can only *add* one for its own edges.
  },
  {
    // Two thin connector lines from a both-ends-many association's two
    // endpoint classes to its join-table hint (design.md DD178): dashed,
    // no terminator, no label of their own — the real association edge
    // (with its own name/multiplicities, still double-tap-editable) is the
    // only line that carries a label. These exist purely so the hint reads
    // as "attached to" the relationship it came from, the way the source
    // asked for, instead of floating unconnected.
    selector: "edge.join-table-edge",
    style: { "line-style": "dashed", "line-color": EDGE_LINE, width: 1, "curve-style": "bezier" },
  },
  {
    // A recursive/reflexive relationship (source === target, tagged in
    // toElements) needs explicit loop geometry. Per Cytoscape's own docs,
    // `loop-direction` is measured from 12 o'clock, clockwise (default
    // `-45deg`); `loop-sweep` is the angle between the leaving/returning
    // edges (default `-90deg`). `0deg` here points the loop straight up,
    // clear of the wide rectangular box (unlike the small circular nodes
    // Cytoscape's own examples assume), and `control-point-step-size` is
    // enlarged so the arc is unmistakably visible. The main `edge`
    // selector's default label placement sits at the edge's geometric
    // midpoint, which for a self-loop can land back on the node itself —
    // `text-margin-y` pushes the multiplicity label up into the loop's
    // open arc instead.
    selector: "edge.self-loop",
    style: {
      "loop-direction": "0deg",
      "loop-sweep": "-90deg",
      "control-point-step-size": 100,
      "text-margin-y": -28,
    },
  },
  // Per-kind UML 2.5 terminators (DD1/DD3), keyed off `edge.data.kind`
  // (set in `toElements`). Appended after `edge.self-loop`: per Cytoscape's
  // `styfn.getContextStyle` merge order, later entries win per-property
  // over earlier matches, and these rules declare only arrow properties —
  // disjoint from `edge.self-loop`'s loop-geometry properties — so a
  // self-referencing generalization gets both the loop shape and its
  // hollow triangle regardless of relative order.
  {
    selector: 'edge[kind = "generalization"]',
    style: {
      "target-arrow-shape": "triangle",
      "target-arrow-fill": "hollow",
      "arrow-scale": 1.6,
    },
  },
  {
    // Diamonds sit at `source` = first click = the "whole" (confirmed
    // scope decision).
    selector: 'edge[kind = "aggregation"]',
    style: {
      "source-arrow-shape": "diamond",
      "source-arrow-fill": "hollow",
      "arrow-scale": 1.6,
    },
  },
  {
    selector: 'edge[kind = "composition"]',
    style: {
      "source-arrow-shape": "diamond",
      "source-arrow-fill": "filled",
      "arrow-scale": 1.6,
    },
  },
];

/**
 * Pure, exported (design.md DD6): carries all the domain knowledge for
 * turning a `UmlModel` into Cytoscape elements, testable with zero DOM and
 * zero Cytoscape mock. Each class becomes one node whose entire visual
 * chrome (box, divider, name/attribute typography) is a generated SVG
 * background image (see `classBoxSvgDataUri`) — Cytoscape's own `label`
 * stays empty, so node identity/tap targeting is unchanged (still the real
 * class id, still one node, no compound children). An edge whose endpoint
 * class is missing from `model.classes` is dropped rather than crashing
 * Cytoscape.
 */
export function toElements(
  model: UmlModel,
  layout: DiagramLayout = { positions: {} },
): ElementDefinition[] {
  const nodes: ElementDefinition[] = model.classes.map((c) => {
    const attributeLines = c.attributes.map((a) => `- ${a.name}: ${attributeTypeLabel(a.type)}`);
    const operationLines = c.operations.map((o) => {
      const params = o.parameters
        .map((p) => `${p.name}: ${attributeTypeLabel(p.type)}`)
        .join(", ");
      const returnSuffix = o.return_type === null ? "" : `: ${attributeTypeLabel(o.return_type)}`;
      return `${VISIBILITY_SYMBOL[o.visibility]} ${o.name}(${params})${returnSuffix}`;
    });
    const box = classBoxSvgDataUri(c.name, attributeLines, operationLines);
    const position = layout.positions[c.id];
    return {
      data: { id: c.id, label: "", bgImage: box.uri, width: box.width, height: box.height },
      ...(position ? { position: { x: position.x, y: position.y } } : {}),
    };
  });

  const known = new Set(model.classes.map((c) => c.id));
  const edges: ElementDefinition[] = model.relationships
    .filter((r) => known.has(r.source.class_id) && known.has(r.target.class_id))
    .map((r) => ({
      data: {
        id: r.id,
        source: r.source.class_id,
        target: r.target.class_id,
        kind: r.kind,
        // UML 2.5 defines no multiplicity on generalization; the submit
        // side already forces "1"/"1" as a required-field placeholder
        // (AddRelationshipControl's DD5), but that placeholder must not
        // leak onto the canvas as a rendered label.
        // The relationship's own name (e.g. "Name A" from an Enterprise
        // Architect import) is the centered label; multiplicities go at the ends.
        label: r.name?.trim() ?? "",
        sourceLabel: r.kind === "generalization" ? "" : formatMultiplicity(r.source.multiplicity),
        targetLabel: r.kind === "generalization" ? "" : formatMultiplicity(r.target.multiplicity),
      },
      // Recursive/reflexive relationship (a class related to itself):
      // needs explicit loop geometry, see the `edge.self-loop` selector.
      classes: r.source.class_id === r.target.class_id ? "self-loop" : undefined,
    }));

  return [...nodes, ...edges];
}

const JOIN_TABLE_ROW_PREFIX = "  "; // visually sets each column apart from the table name, like an attribute line

/**
 * Builds (or repositions) one visual-only box per join-table hint, plus two
 * connector edges from its relationship's endpoint classes to that box
 * (design.md DD178). Default position is the midpoint between the two
 * endpoint classes, nudged perpendicular so it never sits directly on top
 * of the relationship's own line/label — but `overridePositionOf` wins
 * when the user has manually dragged this hint (see `syncJoinTableHints`),
 * so a drag survives the next resync instead of snapping back. Never added
 * to `toElements`'s output (design.md DD177): fcose would otherwise treat
 * the hint as a real node to place, and its position only makes sense once
 * the two real classes already have one — computed here from Cytoscape's
 * OWN current positions, not from the persisted layout, so it still works
 * before either class has ever been dragged (fcose's auto-placement is
 * available even when nothing was saved yet).
 */
export function joinTableHintElements(
  model: UmlModel,
  hints: JoinTableHint[],
  positionOf: (classId: string) => { x: number; y: number } | null,
  overridePositionOf: (hintId: string) => { x: number; y: number } | null = () => null,
): ElementDefinition[] {
  const relationshipById = new Map(model.relationships.map((r) => [r.id, r]));
  const elements: ElementDefinition[] = [];

  for (const hint of hints) {
    const relationship = relationshipById.get(hint.relationship_id);
    if (!relationship) continue;
    const sourcePos = positionOf(relationship.source.class_id);
    const targetPos = positionOf(relationship.target.class_id);
    if (!sourcePos || !targetPos) continue;

    const hintId = `join-table:${hint.relationship_id}`;
    const override = overridePositionOf(hintId);
    let hintPosition: { x: number; y: number };
    if (override) {
      hintPosition = override;
    } else {
      const midX = (sourcePos.x + targetPos.x) / 2;
      const midY = (sourcePos.y + targetPos.y) / 2;
      // Perpendicular to the source->target line, so the hint sits beside
      // the relationship's line/labels instead of on top of them.
      const dx = targetPos.x - sourcePos.x;
      const dy = targetPos.y - sourcePos.y;
      const length = Math.hypot(dx, dy) || 1;
      const offset = 70;
      const offsetX = (-dy / length) * offset;
      const offsetY = (dx / length) * offset;
      hintPosition = { x: midX + offsetX, y: midY + offsetY };
    }

    const box = classBoxSvgDataUri(
      hint.table_name,
      hint.columns.map((c) => `${JOIN_TABLE_ROW_PREFIX}${c}`),
    );
    elements.push({
      data: { id: hintId, label: "", bgImage: box.uri, width: box.width, height: box.height, synthetic: true },
      position: hintPosition,
      classes: "join-table-hint",
    } as ElementDefinition);
    // Two connector edges (design.md DD178), source-class -> hint and
    // hint -> target-class, so the hint reads as attached to its
    // relationship instead of floating unconnected. For a recursive
    // relationship (source === target) these become a visual loop through
    // the hint, which Cytoscape auto-bends apart as parallel edges.
    elements.push({
      data: { id: `join-table-edge:${hint.relationship_id}:source`, source: relationship.source.class_id, target: hintId, synthetic: true },
      classes: "join-table-edge",
    } as ElementDefinition);
    elements.push({
      data: { id: `join-table-edge:${hint.relationship_id}:target`, source: hintId, target: relationship.target.class_id, synthetic: true },
      classes: "join-table-edge",
    } as ElementDefinition);
  }

  return elements;
}

type LockState = { ownerLabel: string; mine: boolean };

type DiagramCanvasProps = {
  model: UmlModel;
  revision: number;
  layout?: DiagramLayout;
  locks?: Record<string, LockState>;
  positionListenerRef?: RefObject<((classId: string, x: number, y: number) => void) | null>;
  claimRejectedListenerRef?: RefObject<((classId: string) => void) | null>;
  onNodeTap?: (classId: string) => void;
  /** Double-tap on an edge (or one of its labels); the container owns the editing UI. */
  onEdgeEdit?: (relationshipId: string) => void;
  highlightedClassId?: string | null;
  onClaim?: (classId: string) => void;
  onLivePosition?: (classId: string, x: number, y: number) => void;
  onRelease?: (classId: string, x: number, y: number) => void;
  /** Visual-only preview of the join tables both-ends-many associations imply. */
  joinTableHints?: JoinTableHint[];
};

const EMPTY_JOIN_TABLE_HINTS: JoinTableHint[] = [];

const EDGE_DOUBLE_TAP_MS = 400;

const EMPTY_LAYOUT: DiagramLayout = { positions: {} };
const EMPTY_LOCKS: Record<string, LockState> = {};

/**
 * Hand-rolled Cytoscape seam (design.md's Technical Approach): one mount
 * effect (construct + `destroy`), one revision-keyed update effect, and one
 * highlight-only effect. `model` is deliberately excluded from the update
 * effect's deps (DD4): `revision` is the server's own change marker and
 * `model` gets a fresh identity on every refetch.
 */
export function DiagramCanvas({
  model,
  revision,
  layout = EMPTY_LAYOUT,
  locks = EMPTY_LOCKS,
  positionListenerRef,
  claimRejectedListenerRef,
  onNodeTap,
  onEdgeEdit,
  highlightedClassId,
  onClaim,
  onLivePosition,
  onRelease,
  joinTableHints = EMPTY_JOIN_TABLE_HINTS,
}: DiagramCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onNodeTapRef = useRef(onNodeTap);
  const onEdgeEditRef = useRef(onEdgeEdit);
  // Cytoscape has no double-tap event: the last edge tap (id + time) is kept
  // so a second tap on the same edge within EDGE_DOUBLE_TAP_MS counts as one.
  const lastEdgeTapRef = useRef<{ id: string; at: number } | null>(null);
  const onClaimRef = useRef(onClaim);
  const onLivePositionRef = useRef(onLivePosition);
  const onReleaseRef = useRef(onRelease);
  // Latest `locks` for `applyLocks` below (DD12) — read through a ref, not
  // closed over directly, since `applyLocks` also runs inside the
  // revision-keyed update effect whose closure is NOT recreated on every
  // `locks` change.
  const locksRef = useRef(locks);
  // Stashes each node's position at the moment it was grabbed (DD12), so a
  // lost claim race can snap it back exactly where the drag started.
  const grabStartPosRef = useRef<Record<string, { x: number; y: number }>>({});
  // Tracks which class ids already had a position from a prior layout run,
  // so only genuinely new classes get laid out on each update — a full
  // fcose re-layout on every mutation (add attribute, remove element, …)
  // was rearranging the whole diagram on every edit (reported UX bug).
  // Seeded from `layout.positions` on mount (DD13) instead of the empty
  // set: a persisted class flows straight into the existing
  // `fixedNodeConstraint` branch below, and only a genuinely unplaced
  // class counts as "new" — an empty `layout` (or the default) leaves this
  // identical to the pre-DD13 empty-set seed.
  const laidOutClassIdsRef = useRef<Set<string>>(new Set(Object.keys(layout.positions)));
  // Drag guard (design.md DD12): a remote update mid-drag must not
  // re-layout under the user's cursor. `draggingRef` gates the update
  // effect below; `pendingUpdateRef` remembers a sync was skipped so the
  // `free` handler can flush it exactly once. `syncModelRef` always points
  // at the update effect's LATEST closure (over the current `model`), so
  // the mount-bound `free` handler never syncs stale data.
  const draggingRef = useRef(false);
  const pendingUpdateRef = useRef(false);
  const syncModelRef = useRef<() => void>(() => {});
  // `model`/`joinTableHints` read through refs, same reason as every other
  // "latest callback" ref here: `syncJoinTableHints` runs from the `free`
  // handler (bound once at mount) and from its own hints-keyed effect,
  // neither of which may capture a stale closure.
  const modelRef = useRef(model);
  const joinTableHintsRef = useRef(joinTableHints);
  // Session-only (design.md DD178): a join-table hint the user manually
  // dragged, keyed by its `join-table:<relationshipId>` id. Consulted by
  // `syncJoinTableHints` so a later resync (a class move, a model edit)
  // doesn't snap the hint back to the auto-computed midpoint. Never
  // persisted or broadcast — lost on reload/remount, and not shared with
  // other collaborators, same as any other purely-visual preview.
  const hintPositionOverridesRef = useRef<Record<string, { x: number; y: number }>>({});

  useEffect(() => {
    // Keeps the refs current after every render (not during render, which
    // the `react-hooks/refs` rule forbids as a ref mutation outside an
    // effect/event handler) — same "latest callback" intent as DD9.
    onNodeTapRef.current = onNodeTap;
    onEdgeEditRef.current = onEdgeEdit;
    onClaimRef.current = onClaim;
    onLivePositionRef.current = onLivePosition;
    onReleaseRef.current = onRelease;
    modelRef.current = model;
    joinTableHintsRef.current = joinTableHints;
  });

  // Adds/repositions/removes the join-table hint nodes from the CURRENT
  // rendered positions of their two endpoint classes (never from `layout`
  // directly — see `joinTableHintElements`'s own doc comment). Safe to call
  // any time the graph exists: reads `modelRef`/`joinTableHintsRef`, so it
  // always reflects the latest props regardless of which effect/handler
  // triggered it.
  const syncJoinTableHints = (cy: Core) => {
    cy.$(".join-table-hint, .join-table-edge").remove();
    const elements = joinTableHintElements(
      modelRef.current,
      joinTableHintsRef.current,
      (classId) => {
        const node = cy.getElementById(classId);
        return node.length > 0 ? node.position() : null;
      },
      (hintId) => hintPositionOverridesRef.current[hintId] ?? null,
    );
    if (elements.length > 0) cy.add(elements);
  };

  // Ungrabifies + tags every foreign-held node (DD12): `ungrabify()` is
  // what actually PREVENTS a local drag (no `grab` event fires at all),
  // never merely rejects one after the fact. `mine: true` and "not in
  // `locks` at all" share the same grabify/untag branch — both mean this
  // connection may freely start a drag on that node.
  const applyLocks = (cy: Core) => {
    cy.nodes().forEach((node) => {
      if (node.data("synthetic")) return; // a join-table hint: locally draggable (DD178), no lock of its own
      const lock = locksRef.current[node.id()];
      if (lock && !lock.mine) {
        node.ungrabify();
        node.addClass("locked-remote");
      } else {
        node.grabify();
        node.removeClass("locked-remote");
      }
    });
  };

  useEffect(() => {
    // Runs on every `locks` change (join snapshot, a fresh claim
    // broadcast, a release) — independent of `revision`, since a lock
    // change never touches `model`/`layout`.
    locksRef.current = locks;
    const cy = cyRef.current;
    if (cy) applyLocks(cy);
  }, [locks]);

  useEffect(() => {
    // Live positions bypass React state entirely (DD11): writes this
    // mount's imperative apply-handler into the caller's ref so
    // `useDocument`'s `node.position` socket handler can move a node
    // directly, with zero re-render and zero `cy.json`.
    if (!positionListenerRef) return;
    positionListenerRef.current = (classId, x, y) => {
      cyRef.current?.getElementById(classId).position({ x, y });
    };
    return () => {
      positionListenerRef.current = null;
    };
  }, [positionListenerRef]);

  useEffect(() => {
    // Same ref-as-latest-handler idiom, for the rare claim-rejected path
    // (DD12): snaps the node back to exactly where its drag started.
    if (!claimRejectedListenerRef) return;
    claimRejectedListenerRef.current = (classId) => {
      const cy = cyRef.current;
      const stashed = grabStartPosRef.current[classId];
      if (cy && stashed) {
        cy.getElementById(classId).position(stashed);
      }
    };
    return () => {
      claimRejectedListenerRef.current = null;
    };
  }, [claimRejectedListenerRef]);

  useEffect(() => {
    // MOUNT — runs once (DD4). The `tap` handler is bound once here and
    // calls through `onNodeTapRef` for the latest callback (DD9): the `[]`
    // dependency list would otherwise capture the first render's closure.
    // `grab`/`drag`/`free` (DD11/DD12) stash/flush through refs for the
    // same reason.
    const cy = cytoscape({ container: containerRef.current!, elements: [], style: STYLE });
    cy.on("tap", "node", (e) => {
      if (e.target.data("synthetic")) return; // a join-table hint, not a class
      onNodeTapRef.current?.(e.target.id());
    });
    cy.on("tap", "edge", (e) => {
      if (e.target.data("synthetic")) return; // a join-table hint's connector line, not a real relationship
      const id: string = e.target.id();
      const now = Date.now();
      const last = lastEdgeTapRef.current;
      if (last !== null && last.id === id && now - last.at <= EDGE_DOUBLE_TAP_MS) {
        lastEdgeTapRef.current = null;
        onEdgeEditRef.current?.(id);
      } else {
        lastEdgeTapRef.current = { id, at: now };
      }
    });
    cy.on("grab", "node", (e) => {
      // A join-table hint is locally draggable (design.md DD178) but never
      // claims a collaboration lock — it isn't a real class in the model.
      if (e.target.data("synthetic")) return;
      draggingRef.current = true;
      const node = e.target;
      const classId = node.id();
      grabStartPosRef.current[classId] = { ...node.position() };
      onClaimRef.current?.(classId);
    });
    cy.on("drag", "node", (e) => {
      if (e.target.data("synthetic")) return; // no live-position broadcast for a local-only hint
      const node = e.target;
      const pos = node.position();
      onLivePositionRef.current?.(node.id(), pos.x, pos.y);
    });
    cy.on("free", "node", (e) => {
      const node = e.target;
      if (node.data("synthetic")) {
        // Manually repositioned join-table hint (design.md DD178): keep it
        // so a later resync (a class move, a model edit) doesn't snap it
        // back to the auto-computed midpoint. No `syncJoinTableHints` call
        // here — the hint/edges are already exactly where the user put them.
        hintPositionOverridesRef.current[node.id()] = { ...node.position() };
        return;
      }
      draggingRef.current = false;
      const pos = node.position();
      onReleaseRef.current?.(node.id(), pos.x, pos.y);
      // A dropped class may be a join-table hint's endpoint: snap the hint
      // to its new midpoint right away, without waiting for a server round
      // trip to bump `revision`.
      syncJoinTableHints(cy);
      if (pendingUpdateRef.current) {
        pendingUpdateRef.current = false;
        syncModelRef.current();
      }
    });
    cyRef.current = cy;
    applyLocks(cy);
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  useEffect(() => {
    // UPDATE — revision-keyed (DD4). `cy.json({elements})` diffs
    // (adds/updates/removes) rather than rebuilding, preserving the
    // instance, its handlers, AND every existing node's position.
    const cy = cyRef.current;
    if (!cy) return;

    const syncModel = () => {
      const currentClassIds = model.classes.map((c) => c.id);
      const previouslyLaidOut = laidOutClassIdsRef.current;
      const isFirstLayout = previouslyLaidOut.size === 0;
      const newClassIds = currentClassIds.filter((id) => !previouslyLaidOut.has(id));

      // Capture already-placed classes' current positions BEFORE syncing
      // new elements in, so fcose can pin them (`fixedNodeConstraint`) and
      // only find a spot for whatever is actually new.
      const fixedNodeConstraint = isFirstLayout
        ? undefined
        : currentClassIds
            .filter((id) => previouslyLaidOut.has(id) && cy.getElementById(id).length > 0)
            .map((id) => ({ nodeId: id, position: cy.getElementById(id).position() }));

      cy.json({ elements: toElements(model, layout) });

      // Only re-layout when there's something new to place. A pure
      // attribute/relationship/removal edit touches zero new classes, so
      // the diagram's existing positions are left completely undisturbed.
      if (isFirstLayout || newClassIds.length > 0) {
        // `animate`/`nodeSeparation`/`padding`/`randomize`/`fixedNodeConstraint`
        // are fcose-specific options (`@types/cytoscape-fcose`'s
        // `FcoseLayoutOptions`) not present on cytoscape's generic
        // `BaseLayoutOptions` that `cy.layout()`'s signature is typed
        // against. `nodeSeparation`/`padding` widen fcose's tightly-packed
        // default spacing; `randomize: false` plus `fixedNodeConstraint`
        // keeps every already-placed class exactly where it is.
        cy.layout({
          name: "fcose",
          animate: false,
          nodeSeparation: 160,
          padding: 80,
          randomize: isFirstLayout,
          fixedNodeConstraint,
        } as cytoscape.LayoutOptions & {
          animate?: boolean;
          nodeSeparation?: number;
          padding?: number;
          randomize?: boolean;
          fixedNodeConstraint?: { nodeId: string; position: cytoscape.Position }[];
        }).run();
      }

      laidOutClassIdsRef.current = new Set(currentClassIds);
      // Newly-synced nodes default to grabbable — reapply the current
      // lock snapshot so a class that arrives already foreign-held (e.g.
      // added by another client while locked) starts ungrabified too.
      applyLocks(cy);
      // Real nodes are in their final positions now (including any fcose
      // placement that just ran) — safe to (re)place the join-table hints.
      syncJoinTableHints(cy);
    };

    // Always point the ref at THIS run's closure (over the current
    // `model`), so a `free` event firing later flushes fresh data — never
    // whatever `model` was current the last time dragging started.
    syncModelRef.current = syncModel;

    if (draggingRef.current) {
      // DD12: a remote update mid-drag must not re-layout under the
      // user's cursor. Defer the sync until the `free` handler flushes it.
      pendingUpdateRef.current = true;
      return;
    }

    syncModel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revision]);

  useEffect(() => {
    // `joinTableHints` arrives from a separate fetch (the container's own
    // request), so it can land after `revision`'s sync already ran — this
    // effect covers that race without forcing a full re-layout.
    const cy = cyRef.current;
    if (cy) syncJoinTableHints(cy);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [joinTableHints]);

  useEffect(() => {
    // Highlight only — no re-layout.
    cyRef.current?.nodes().removeClass("selected-source");
    if (highlightedClassId) {
      cyRef.current?.getElementById(highlightedClassId).addClass("selected-source");
    }
  }, [highlightedClassId]);

  return <div ref={containerRef} className="h-full w-full" />;
}
