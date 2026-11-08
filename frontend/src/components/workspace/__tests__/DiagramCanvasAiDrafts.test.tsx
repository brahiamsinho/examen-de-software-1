import { describe, expect, it, vi } from "vitest";

import type { AiDrafts } from "@/lib/ai_proposals";

vi.mock("cytoscape", () => {
  const cytoscapeFn = vi.fn();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (cytoscapeFn as any).use = vi.fn();
  return { default: cytoscapeFn };
});
vi.mock("cytoscape-fcose", () => ({ default: {} }));

const drafts: AiDrafts = {
  classes: [
    { id: "ai-draft:p1:pedido", name: "Pedido", attributes: ["- total: FLOAT"], operations: ["+ calcular()"], proposalId: "p1" },
    { id: "ai-draft:p1:item", name: "Item", attributes: [], operations: [], proposalId: "p1" },
  ],
  relationships: [
    {
      id: "ai-draft-edge:p1:2",
      source: "c-persona",
      target: "ai-draft:p1:pedido",
      kind: "association",
      name: "realiza",
      sourceMultiplicity: "1",
      targetMultiplicity: "0..*",
      proposalId: "p1",
    },
  ],
};

describe("DiagramCanvas — aiDraftElements (pure)", () => {
  it("builds one dashed, synthetic box per draft class and one synthetic edge per draft relationship", async () => {
    const { aiDraftElements } = await import("@/components/workspace/DiagramCanvas");

    const elements = aiDraftElements(drafts, { x: 500, y: 100 });

    const nodes = elements.filter((element) => element.classes === "ai-draft");
    const edges = elements.filter((element) => element.classes === "ai-draft-edge");
    expect(nodes.map((node) => node.data.id)).toEqual(["ai-draft:p1:pedido", "ai-draft:p1:item"]);
    expect(nodes.every((node) => node.data.synthetic === true)).toBe(true);
    expect(String(nodes[0]!.data.bgImage)).toContain("data:image/svg+xml");
    expect(edges).toHaveLength(1);
    expect(edges[0]!.data).toMatchObject({
      id: "ai-draft-edge:p1:2",
      source: "c-persona",
      target: "ai-draft:p1:pedido",
      synthetic: true,
    });
  });

  it("labels a draft edge with its name and the multiplicity at each end, like a real relationship", async () => {
    const { aiDraftElements } = await import("@/components/workspace/DiagramCanvas");

    const edge = aiDraftElements(drafts, { x: 0, y: 0 }).find((element) => element.classes === "ai-draft-edge");

    expect(edge!.data).toMatchObject({ label: "realiza", sourceLabel: "1", targetLabel: "0..*" });
  });

  it("uses the same label fields the real edges use, so one style draws both", async () => {
    const { STYLE } = await import("@/components/workspace/DiagramCanvas");

    const edge = STYLE.find((entry) => entry.selector === "edge");

    expect(edge?.style).toMatchObject({ "source-label": "data(sourceLabel)", "target-label": "data(targetLabel)" });
  });

  it("stacks the draft boxes below the anchor so they never overlap each other", async () => {
    const { aiDraftElements } = await import("@/components/workspace/DiagramCanvas");

    const [first, second] = aiDraftElements(drafts, { x: 500, y: 100 }).filter(
      (element) => element.classes === "ai-draft",
    );

    expect(first!.position).toEqual({ x: 500, y: 100 });
    expect(second!.position!.x).toBe(500);
    expect(second!.position!.y).toBeGreaterThan(first!.position!.y);
  });

  it("honours a position the user dragged a draft to", async () => {
    const { aiDraftElements } = await import("@/components/workspace/DiagramCanvas");

    const elements = aiDraftElements(drafts, { x: 500, y: 100 }, (id) =>
      id === "ai-draft:p1:item" ? { x: 9, y: 8 } : null,
    );

    const item = elements.find((element) => element.data.id === "ai-draft:p1:item");
    expect(item!.position).toEqual({ x: 9, y: 8 });
  });

  it("returns nothing when no proposal is pending", async () => {
    const { aiDraftElements } = await import("@/components/workspace/DiagramCanvas");

    expect(aiDraftElements({ classes: [], relationships: [] }, { x: 0, y: 0 })).toEqual([]);
  });

  it("styles drafts as dashed and violet, distinct from locks and join-table hints", async () => {
    const { STYLE } = await import("@/components/workspace/DiagramCanvas");

    const node = STYLE.find((entry) => entry.selector === "node.ai-draft");
    const edge = STYLE.find((entry) => entry.selector === "edge.ai-draft-edge");

    expect(node?.style).toMatchObject({ "border-style": "dashed", "border-color": "#7C3AED" });
    expect(edge?.style).toMatchObject({ "line-style": "dashed", "line-color": "#7C3AED" });
  });
});
