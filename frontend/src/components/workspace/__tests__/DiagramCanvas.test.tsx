import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { UmlModel } from "@/lib/uml_documents";

/**
 * `toElements` is a pure exported function (design.md DD6) testable with
 * zero DOM and zero Cytoscape mock — the whole point of pulling it out of
 * the effect. The lifecycle section below mocks `cytoscape` because jsdom
 * has no canvas (design.md's Decision Drivers).
 */
describe("DiagramCanvas — toElements (pure)", () => {
  it("maps classes to nodes with attribute lines in the label, and relationships to edges with a multiplicity label", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [
        {
          id: "c1",
          name: "Cliente",
          visibility: "public",
          attributes: [{ id: "a1", name: "nombre", type: "String", visibility: "private" }],
          operations: [],
        },
        { id: "c2", name: "Pedido", visibility: "public", attributes: [], operations: [] },
      ],
      enumerations: [],
      relationships: [
        {
          id: "r1",
          kind: "association",
          source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
          target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
          name: null,
        },
      ],
      generation_metadata: {},
    };

    const elements = toElements(model);

    const nodes = elements.filter((el) => !("source" in el.data));
    expect(nodes).toHaveLength(2);
    const clienteNode = nodes.find((n) => n.data.id === "c1")!;
    // The node itself carries no Cytoscape `label` text (empty string) — its
    // entire visual chrome is a generated SVG background image, the way a
    // real UML class box (name / divider / attributes) is drawn. Decoding
    // the data URI proves the box actually contains this class's content.
    expect(clienteNode.data.label).toBe("");
    expect(typeof clienteNode.data.width).toBe("number");
    expect(typeof clienteNode.data.height).toBe("number");
    const svg = decodeURIComponent((clienteNode.data.bgImage as string).replace("data:image/svg+xml,", ""));
    expect(svg).toContain("Cliente");
    expect(svg).toContain("nombre: String");

    const pedidoNode = nodes.find((n) => n.data.id === "c2")!;
    const pedidoSvg = decodeURIComponent((pedidoNode.data.bgImage as string).replace("data:image/svg+xml,", ""));
    // A class with zero attributes still renders a complete, valid box
    // (name + divider), not a broken/empty shell.
    expect(pedidoSvg).toContain("Pedido");
    expect(pedidoSvg).toContain("<line");

    const edges = elements.filter((el) => "source" in el.data);
    expect(edges).toHaveLength(1);
    expect(edges[0]!.data).toMatchObject({ id: "r1", source: "c1", target: "c2", kind: "association" });
    expect(edges[0]!.data.label).toBe("1 → 0..*");
  });

  it("escapes a class name containing SVG-significant characters instead of breaking the box markup", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [
        { id: "c1", name: `<Weird> & "Name"`, visibility: "public", attributes: [], operations: [] },
      ],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };

    const elements = toElements(model);
    const node = elements[0]!;
    const svg = decodeURIComponent((node.data.bgImage as string).replace("data:image/svg+xml,", ""));
    expect(svg).toContain("&lt;Weird&gt; &amp; &quot;Name&quot;");
    expect(svg).not.toContain(`<Weird>`);
  });

  it("tags a recursive relationship (source === target) with the self-loop class for loop geometry", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [{ id: "c1", name: "Nodo", visibility: "public", attributes: [], operations: [] }],
      enumerations: [],
      relationships: [
        {
          id: "r1",
          kind: "association",
          source: { class_id: "c1", multiplicity: { lower: 0, upper: 1 }, role: null },
          target: { class_id: "c1", multiplicity: { lower: 0, upper: 1 }, role: null },
          name: null,
        },
      ],
      generation_metadata: {},
    };

    const elements = toElements(model);
    const edge = elements.find((el) => "source" in el.data)!;
    expect(edge.classes).toBe("self-loop");
  });

  it.each(["association", "aggregation", "composition", "generalization"] as const)(
    "propagates relationship kind %s into edge.data.kind",
    async (kind) => {
      const { toElements } = await import("@/components/workspace/DiagramCanvas");

      const model: UmlModel = {
        classes: [
          { id: "c1", name: "A", visibility: "public", attributes: [], operations: [] },
          { id: "c2", name: "B", visibility: "public", attributes: [], operations: [] },
        ],
        enumerations: [],
        relationships: [
          {
            id: "r1",
            kind,
            source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
            target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
            name: null,
          },
        ],
        generation_metadata: {},
      };

      const elements = toElements(model);
      const edge = elements.find((el) => "source" in el.data)!;
      expect(edge.data.kind).toBe(kind);
    },
  );

  it("omits the multiplicity label for a generalization edge (UML 2.5 defines none)", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [
        { id: "c1", name: "Perro", visibility: "public", attributes: [], operations: [] },
        { id: "c2", name: "Animal", visibility: "public", attributes: [], operations: [] },
      ],
      enumerations: [],
      relationships: [
        {
          id: "r1",
          kind: "generalization",
          source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
          target: { class_id: "c2", multiplicity: { lower: 1, upper: 1 }, role: null },
          name: null,
        },
      ],
      generation_metadata: {},
    };

    const elements = toElements(model);
    const edge = elements.find((el) => "source" in el.data)!;
    expect(edge.data.label).toBe("");
  });

  it("tags a self-referencing generalization with both self-loop classes and kind data (DD3)", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [{ id: "c1", name: "Nodo", visibility: "public", attributes: [], operations: [] }],
      enumerations: [],
      relationships: [
        {
          id: "r1",
          kind: "generalization",
          source: { class_id: "c1", multiplicity: { lower: 0, upper: 1 }, role: null },
          target: { class_id: "c1", multiplicity: { lower: 0, upper: 1 }, role: null },
          name: null,
        },
      ],
      generation_metadata: {},
    };

    const elements = toElements(model);
    const edge = elements.find((el) => "source" in el.data)!;
    expect(edge.classes).toBe("self-loop");
    expect(edge.data.kind).toBe("generalization");
  });

  it("drops an edge whose endpoint class is missing from model.classes", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [{ id: "c1", name: "Cliente", visibility: "public", attributes: [], operations: [] }],
      enumerations: [],
      relationships: [
        {
          id: "r1",
          kind: "association",
          source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
          target: { class_id: "missing", multiplicity: { lower: 0, upper: null }, role: null },
          name: null,
        },
      ],
      generation_metadata: {},
    };

    const elements = toElements(model);
    const edges = elements.filter((el) => "source" in el.data);
    expect(edges).toHaveLength(0);
  });
});

/**
 * `STYLE` is exported (design.md DD6) as a plain data structure carrying the
 * UML notation contract — assertable with zero DOM and zero canvas, since
 * jsdom has no canvas and rendered arrowheads are otherwise untestable.
 */
describe("DiagramCanvas — STYLE (per-kind edge notation, DD1-DD3)", () => {
  it("the generic edge selector declares no target-arrow-shape key (association stays a plain line, DD2)", async () => {
    const { STYLE } = await import("@/components/workspace/DiagramCanvas");
    const genericEdge = STYLE.find((rule) => rule.selector === "edge")!;
    expect(genericEdge.style).not.toHaveProperty("target-arrow-shape");
  });

  it.each([
    ["generalization", { "target-arrow-shape": "triangle", "target-arrow-fill": "hollow" }],
    ["aggregation", { "source-arrow-shape": "diamond", "source-arrow-fill": "hollow" }],
    ["composition", { "source-arrow-shape": "diamond", "source-arrow-fill": "filled" }],
  ] as const)(
    "the %s selector declares exactly its terminator shape + fill, and no loop-* property (DD3)",
    async (kind, expectedTerminator) => {
      const { STYLE } = await import("@/components/workspace/DiagramCanvas");
      const rule = STYLE.find((r) => r.selector === `edge[kind = "${kind}"]`)!;
      expect(rule).toBeDefined();
      expect(rule.style).toMatchObject(expectedTerminator);
      expect(rule.style).not.toHaveProperty("loop-direction");
      expect(rule.style).not.toHaveProperty("loop-sweep");
      expect(rule.style).not.toHaveProperty("control-point-step-size");
      expect(rule.style).not.toHaveProperty("text-margin-y");
    },
  );

  it("edge.self-loop still carries its four prior-cycle properties, unchanged (regression guard)", async () => {
    const { STYLE } = await import("@/components/workspace/DiagramCanvas");
    const selfLoop = STYLE.find((r) => r.selector === "edge.self-loop")!;
    expect(selfLoop.style).toEqual({
      "loop-direction": "0deg",
      "loop-sweep": "-90deg",
      "control-point-step-size": 100,
      "text-margin-y": -28,
    });
  });
});

const { cyMock } = vi.hoisted(() => ({
  cyMock: {
    on: vi.fn(),
    destroy: vi.fn(),
    json: vi.fn(),
    layout: vi.fn(() => ({ run: vi.fn() })),
    nodes: vi.fn(() => ({ removeClass: vi.fn() })),
    getElementById: vi.fn(
      (): { addClass: ReturnType<typeof vi.fn>; length: number; position: () => { x: number; y: number } } => ({
        addClass: vi.fn(),
        length: 0,
        position: () => ({ x: 0, y: 0 }),
      }),
    ),
  },
}));

vi.mock("cytoscape", () => {
  const cytoscapeFn = vi.fn(() => cyMock);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (cytoscapeFn as any).use = vi.fn();
  return { default: cytoscapeFn };
});
vi.mock("cytoscape-fcose", () => ({ default: {} }));

describe("DiagramCanvas — Cytoscape lifecycle (mocked)", () => {
  const emptyModel: UmlModel = {
    classes: [],
    enumerations: [],
    relationships: [],
    generation_metadata: {},
  };

  beforeEach(() => {
    cyMock.on.mockClear();
    cyMock.destroy.mockClear();
    cyMock.json.mockClear();
    cyMock.layout.mockClear();
    cyMock.nodes.mockClear();
    cyMock.getElementById.mockClear();
  });

  it("constructs the Cytoscape instance once on mount and destroys it on unmount", async () => {
    const cytoscape = (await import("cytoscape")).default;
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");

    const { unmount } = render(<DiagramCanvas model={emptyModel} revision={1} />);

    expect(cytoscape).toHaveBeenCalledOnce();
    expect(cyMock.destroy).not.toHaveBeenCalled();

    unmount();

    expect(cyMock.destroy).toHaveBeenCalledOnce();
  });

  it("calls cy.json + cy.layout({name: 'fcose'}) on revision change and not on an unrelated re-render", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");

    const { rerender } = render(<DiagramCanvas model={emptyModel} revision={1} />);
    expect(cyMock.json).toHaveBeenCalledOnce();
    expect(cyMock.layout).toHaveBeenCalledWith(expect.objectContaining({ name: "fcose" }));

    cyMock.json.mockClear();
    cyMock.layout.mockClear();

    // Unrelated re-render: same revision, new model identity.
    rerender(<DiagramCanvas model={{ ...emptyModel }} revision={1} />);
    expect(cyMock.json).not.toHaveBeenCalled();
    expect(cyMock.layout).not.toHaveBeenCalled();

    rerender(<DiagramCanvas model={emptyModel} revision={2} />);
    expect(cyMock.json).toHaveBeenCalledOnce();
    expect(cyMock.layout).toHaveBeenCalledOnce();
  });

  it("keeps existing classes fixed in place and only lays out a newly added class (production UX fix)", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const oneClass: UmlModel = {
      classes: [{ id: "c1", name: "A", visibility: "public", attributes: [], operations: [] }],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };
    const twoClasses: UmlModel = {
      ...oneClass,
      classes: [...oneClass.classes, { id: "c2", name: "B", visibility: "public", attributes: [], operations: [] }],
    };
    cyMock.getElementById.mockReturnValue({
      length: 1,
      position: () => ({ x: 10, y: 20 }),
      addClass: vi.fn(),
    });

    const { rerender } = render(<DiagramCanvas model={oneClass} revision={1} />);
    cyMock.layout.mockClear();

    rerender(<DiagramCanvas model={twoClasses} revision={2} />);

    expect(cyMock.layout).toHaveBeenCalledWith(
      expect.objectContaining({
        randomize: false,
        fixedNodeConstraint: [{ nodeId: "c1", position: { x: 10, y: 20 } }],
      }),
    );
  });

  it("skips re-layout entirely when a revision change adds no new class (attribute/relationship-only edit)", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const model: UmlModel = {
      classes: [{ id: "c1", name: "A", visibility: "public", attributes: [], operations: [] }],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };

    const { rerender } = render(<DiagramCanvas model={model} revision={1} />);
    cyMock.layout.mockClear();
    cyMock.json.mockClear();

    // Same class ids as before — e.g. an attribute was added to c1.
    // Revision bumps but no new class exists, so nothing should be moved.
    rerender(<DiagramCanvas model={{ ...model }} revision={2} />);

    expect(cyMock.json).toHaveBeenCalledOnce();
    expect(cyMock.layout).not.toHaveBeenCalled();
  });

  it("routes the tap handler through onNodeTapRef to the latest onNodeTap", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");

    const onNodeTapA = vi.fn();
    const { rerender } = render(
      <DiagramCanvas model={emptyModel} revision={1} onNodeTap={onNodeTapA} />,
    );

    const tapHandler = cyMock.on.mock.calls.find(([event]) => event === "tap")![2] as (e: {
      target: { id: () => string };
    }) => void;

    const onNodeTapB = vi.fn();
    rerender(<DiagramCanvas model={emptyModel} revision={1} onNodeTap={onNodeTapB} />);

    tapHandler({ target: { id: () => "c1" } });

    expect(onNodeTapA).not.toHaveBeenCalled();
    expect(onNodeTapB).toHaveBeenCalledWith("c1");
    expect(cyMock.on).toHaveBeenCalledOnce();
  });

  it("toggles the selected-source class on highlightedClassId change without re-running layout", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const removeClass = vi.fn();
    cyMock.nodes.mockReturnValue({ removeClass });
    const addClass = vi.fn();
    cyMock.getElementById.mockReturnValue({ addClass, length: 1, position: () => ({ x: 0, y: 0 }) });

    const { rerender } = render(
      <DiagramCanvas model={emptyModel} revision={1} highlightedClassId={null} />,
    );
    cyMock.layout.mockClear();

    rerender(<DiagramCanvas model={emptyModel} revision={1} highlightedClassId="c1" />);

    expect(removeClass).toHaveBeenCalledWith("selected-source");
    expect(cyMock.getElementById).toHaveBeenCalledWith("c1");
    expect(addClass).toHaveBeenCalledWith("selected-source");
    expect(cyMock.layout).not.toHaveBeenCalled();
  });
});
