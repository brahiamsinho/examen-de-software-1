"use client";

import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import fcose from "cytoscape-fcose";
import { useEffect, useRef, type RefObject } from "react";

import {
  attributeTypeLabel,
  formatMultiplicity,
  type DiagramLayout,
  type UmlModel,
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
function classBoxSvgDataUri(name: string, attributeLines: string[]): { uri: string; width: number; height: number } {
  const nameWidth = estimateTextWidth(name, NAME_FONT_SIZE, 0.58);
  const attrWidths = attributeLines.map((line) => estimateTextWidth(line, ATTR_FONT_SIZE, 0.62));
  const width = Math.max(MIN_BOX_WIDTH, PADDING_X * 2 + Math.max(nameWidth, ...attrWidths, 0));

  const attrAreaHeight =
    attributeLines.length > 0 ? attributeLines.length * ATTR_LINE_HEIGHT : ATTR_LINE_HEIGHT * 0.6;
  const height = PADDING_Y * 2 + NAME_LINE_HEIGHT + DIVIDER_MARGIN * 2 + attrAreaHeight;

  const dividerY = PADDING_Y + NAME_LINE_HEIGHT + DIVIDER_MARGIN;
  const nameBaselineY = PADDING_Y + NAME_LINE_HEIGHT * 0.68;
  const attrStartY = dividerY + DIVIDER_MARGIN;

  const attrText = attributeLines
    .map(
      (line, i) =>
        `<text x="${PADDING_X}" y="${attrStartY + i * ATTR_LINE_HEIGHT + ATTR_LINE_HEIGHT * 0.72}" font-family="${MONO_FONT_STACK}" font-size="${ATTR_FONT_SIZE}" fill="${ATTR_TEXT}">${escapeXml(line)}</text>`,
    )
    .join("");

  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">` +
    `<rect x="0.75" y="0.75" width="${width - 1.5}" height="${height - 1.5}" fill="${CARD_BG}" stroke="${STRUCTURE_BORDER}" stroke-width="1.5"/>` +
    `<text x="${width / 2}" y="${nameBaselineY}" font-family="${SANS_FONT_STACK}" font-size="${NAME_FONT_SIZE}" font-weight="700" fill="${INK}" text-anchor="middle">${escapeXml(name)}</text>` +
    `<line x1="0" y1="${dividerY}" x2="${width}" y2="${dividerY}" stroke="${STRUCTURE_BORDER}" stroke-width="1.5"/>` +
    attrText +
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
    const box = classBoxSvgDataUri(c.name, attributeLines);
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
        label:
          r.kind === "generalization"
            ? ""
            : `${formatMultiplicity(r.source.multiplicity)} → ${formatMultiplicity(r.target.multiplicity)}`,
      },
      // Recursive/reflexive relationship (a class related to itself):
      // needs explicit loop geometry, see the `edge.self-loop` selector.
      classes: r.source.class_id === r.target.class_id ? "self-loop" : undefined,
    }));

  return [...nodes, ...edges];
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
  highlightedClassId?: string | null;
  onClaim?: (classId: string) => void;
  onLivePosition?: (classId: string, x: number, y: number) => void;
  onRelease?: (classId: string, x: number, y: number) => void;
};

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
  highlightedClassId,
  onClaim,
  onLivePosition,
  onRelease,
}: DiagramCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onNodeTapRef = useRef(onNodeTap);
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

  useEffect(() => {
    // Keeps the refs current after every render (not during render, which
    // the `react-hooks/refs` rule forbids as a ref mutation outside an
    // effect/event handler) — same "latest callback" intent as DD9.
    onNodeTapRef.current = onNodeTap;
    onClaimRef.current = onClaim;
    onLivePositionRef.current = onLivePosition;
    onReleaseRef.current = onRelease;
  });

  // Ungrabifies + tags every foreign-held node (DD12): `ungrabify()` is
  // what actually PREVENTS a local drag (no `grab` event fires at all),
  // never merely rejects one after the fact. `mine: true` and "not in
  // `locks` at all" share the same grabify/untag branch — both mean this
  // connection may freely start a drag on that node.
  const applyLocks = (cy: Core) => {
    cy.nodes().forEach((node) => {
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
    cy.on("tap", "node", (e) => onNodeTapRef.current?.(e.target.id()));
    cy.on("grab", "node", (e) => {
      draggingRef.current = true;
      const node = e.target;
      const classId = node.id();
      grabStartPosRef.current[classId] = { ...node.position() };
      onClaimRef.current?.(classId);
    });
    cy.on("drag", "node", (e) => {
      const node = e.target;
      const pos = node.position();
      onLivePositionRef.current?.(node.id(), pos.x, pos.y);
    });
    cy.on("free", "node", (e) => {
      draggingRef.current = false;
      const node = e.target;
      const pos = node.position();
      onReleaseRef.current?.(node.id(), pos.x, pos.y);
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
    // Highlight only — no re-layout.
    cyRef.current?.nodes().removeClass("selected-source");
    if (highlightedClassId) {
      cyRef.current?.getElementById(highlightedClassId).addClass("selected-source");
    }
  }, [highlightedClassId]);

  return <div ref={containerRef} className="h-full w-full" />;
}
