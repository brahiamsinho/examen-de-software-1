"use client";

import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import fcose from "cytoscape-fcose";
import { useEffect, useRef } from "react";

import { attributeTypeLabel, formatMultiplicity, type UmlModel } from "@/lib/uml_documents";

// Module scope, guarded by nothing (design.md DD5): `cytoscape.use` on an
// already-registered extension warns, and module scope runs once per bundle.
cytoscape.use(fcose);

const STYLE: cytoscape.Stylesheet[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-wrap": "wrap",
      "text-valign": "center",
      shape: "round-rectangle",
    },
  },
  {
    selector: "node.selected-source",
    style: { "border-width": 2, "border-color": "#2563eb" },
  },
  {
    selector: "edge",
    style: { label: "data(label)", "curve-style": "bezier", "target-arrow-shape": "triangle" },
  },
];

/**
 * Pure, exported (design.md DD6): carries all the domain knowledge for
 * turning a `UmlModel` into Cytoscape elements, testable with zero DOM and
 * zero Cytoscape mock. Attributes render inside the class node's own
 * multi-line label (DD7) instead of child nodes, so a tapped node always
 * means "pick a class" (DD9's invariant). An edge whose endpoint class is
 * missing from `model.classes` is dropped rather than crashing Cytoscape.
 */
export function toElements(model: UmlModel): ElementDefinition[] {
  const nodes: ElementDefinition[] = model.classes.map((c) => ({
    data: {
      id: c.id,
      label: [
        c.name,
        "──────",
        ...c.attributes.map((a) => `- ${a.name}: ${attributeTypeLabel(a.type)}`),
      ].join("\n"),
    },
  }));

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
    cy.layout({ name: "fcose", animate: false }).run();
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
