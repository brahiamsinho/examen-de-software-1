"use client";

import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import fcose from "cytoscape-fcose";
import { useEffect, useRef } from "react";

import { attributeTypeLabel, formatMultiplicity, type UmlModel } from "@/lib/uml_documents";

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

const STYLE: cytoscape.StylesheetStyle[] = [
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
    selector: "edge",
    style: {
      label: "data(label)",
      "curve-style": "bezier",
      "target-arrow-shape": "triangle",
      "line-color": EDGE_LINE,
      "target-arrow-color": EDGE_LINE,
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
export function toElements(model: UmlModel): ElementDefinition[] {
  const nodes: ElementDefinition[] = model.classes.map((c) => {
    const attributeLines = c.attributes.map((a) => `- ${a.name}: ${attributeTypeLabel(a.type)}`);
    const box = classBoxSvgDataUri(c.name, attributeLines);
    return {
      data: { id: c.id, label: "", bgImage: box.uri, width: box.width, height: box.height },
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
        label: `${formatMultiplicity(r.source.multiplicity)} → ${formatMultiplicity(r.target.multiplicity)}`,
      },
    }));

  return [...nodes, ...edges];
}

type DiagramCanvasProps = {
  model: UmlModel;
  revision: number;
  onNodeTap?: (classId: string) => void;
  highlightedClassId?: string | null;
};

/**
 * Hand-rolled Cytoscape seam (design.md's Technical Approach): one mount
 * effect (construct + `destroy`), one revision-keyed update effect, and one
 * highlight-only effect. `model` is deliberately excluded from the update
 * effect's deps (DD4): `revision` is the server's own change marker and
 * `model` gets a fresh identity on every refetch.
 */
export function DiagramCanvas({ model, revision, onNodeTap, highlightedClassId }: DiagramCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onNodeTapRef = useRef(onNodeTap);

  useEffect(() => {
    // Keeps the ref current after every render (not during render, which
    // the `react-hooks/refs` rule forbids as a ref mutation outside an
    // effect/event handler) — same "latest callback" intent as DD9.
    onNodeTapRef.current = onNodeTap;
  });

  useEffect(() => {
    // MOUNT — runs once (DD4). The `tap` handler is bound once here and
    // calls through `onNodeTapRef` for the latest callback (DD9): the `[]`
    // dependency list would otherwise capture the first render's closure.
    const cy = cytoscape({ container: containerRef.current!, elements: [], style: STYLE });
    cy.on("tap", "node", (e) => onNodeTapRef.current?.(e.target.id()));
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, []);

  useEffect(() => {
    // UPDATE — revision-keyed (DD4). `cy.json({elements})` diffs
    // (adds/updates/removes) rather than rebuilding, preserving the
    // instance and its handlers.
    const cy = cyRef.current;
    if (!cy) return;
    cy.json({ elements: toElements(model) });
    // `animate` is an fcose-specific option (`@types/cytoscape-fcose`'s
    // `FcoseLayoutOptions`) not present on cytoscape's generic
    // `BaseLayoutOptions` that `cy.layout()`'s signature is typed against.
    cy.layout({ name: "fcose", animate: false } as cytoscape.LayoutOptions & { animate?: boolean }).run();
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
