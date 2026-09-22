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
    expect(edges[0]!.data).toMatchObject({ label: "", sourceLabel: "1", targetLabel: "0..*" });
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

  it("shows the relationship name above the multiplicities when it has one", async () => {
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
          kind: "association",
          source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
          target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
          name: "Name A",
        },
      ],
      generation_metadata: {},
    };

    const edge = toElements(model).find((el) => "source" in el.data)!;
    expect(edge.data).toMatchObject({ label: "Name A", sourceLabel: "1", targetLabel: "0..*" });
  });

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
    expect(edge.data).toMatchObject({ label: "", sourceLabel: "", targetLabel: "" });
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

  it("seeds position from layout.positions for a persisted class id and omits it for an unplaced one (DD13)", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [
        { id: "c1", name: "Cliente", visibility: "public", attributes: [], operations: [] },
        { id: "c2", name: "Pedido", visibility: "public", attributes: [], operations: [] },
      ],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };
    const layout = { positions: { c1: { x: 120.5, y: -40.0 } } };

    const elements = toElements(model, layout);

    const c1Node = elements.find((el) => el.data.id === "c1")!;
    expect(c1Node.position).toEqual({ x: 120.5, y: -40.0 });
    const c2Node = elements.find((el) => el.data.id === "c2")!;
    expect(c2Node.position).toBeUndefined();
  });

  it("defaults to an empty layout (no seeded positions) when the second argument is omitted", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [{ id: "c1", name: "Cliente", visibility: "public", attributes: [], operations: [] }],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };

    const elements = toElements(model);

    expect(elements[0]!.position).toBeUndefined();
  });
});

/**
 * `joinTableHintElements` (design.md DD177): the visual-only preview of a
 * both-ends-many association's implied join table. Pure like `toElements`,
 * and deliberately NOT part of it — see its own doc comment for why.
 */
describe("DiagramCanvas — joinTableHintElements (pure)", () => {
  const model: UmlModel = {
    classes: [
      { id: "a", name: "Class A", visibility: "public", attributes: [], operations: [] },
      { id: "b", name: "Class B", visibility: "public", attributes: [], operations: [] },
    ],
    enumerations: [],
    relationships: [
      {
        id: "r1",
        kind: "association",
        name: null,
        source: { class_id: "a", multiplicity: { lower: 0, upper: null }, role: null },
        target: { class_id: "b", multiplicity: { lower: 0, upper: null }, role: null },
      },
    ],
    generation_metadata: {},
  };

  it("places one node plus two connector edges per hint, off the straight line between its two classes", async () => {
    const { joinTableHintElements } = await import("@/components/workspace/DiagramCanvas");
    const positions: Record<string, { x: number; y: number }> = { a: { x: 0, y: 0 }, b: { x: 100, y: 0 } };

    const elements = joinTableHintElements(
      model,
      [{ relationship_id: "r1", table_name: "class_a_class_b", columns: ["id", "class_a_id", "class_b_id"] }],
      (classId) => positions[classId] ?? null,
    );

    expect(elements).toHaveLength(3);
    const [hint, sourceEdge, targetEdge] = elements;
    expect(hint!.data.id).toBe("join-table:r1");
    expect(hint!.classes).toBe("join-table-hint");
    // Perpendicular to a horizontal a->b line: x stays at the midpoint, y moves off it.
    expect(hint!.position!.x).toBeCloseTo(50);
    expect(hint!.position!.y).not.toBe(0);

    expect(sourceEdge!.data).toMatchObject({ source: "a", target: "join-table:r1", synthetic: true });
    expect(sourceEdge!.classes).toBe("join-table-edge");
    expect(targetEdge!.data).toMatchObject({ source: "join-table:r1", target: "b", synthetic: true });
    expect(targetEdge!.classes).toBe("join-table-edge");
  });

  it("uses the override position instead of the computed midpoint when the hint was manually dragged", async () => {
    const { joinTableHintElements } = await import("@/components/workspace/DiagramCanvas");
    const positions: Record<string, { x: number; y: number }> = { a: { x: 0, y: 0 }, b: { x: 100, y: 0 } };

    const elements = joinTableHintElements(
      model,
      [{ relationship_id: "r1", table_name: "class_a_class_b", columns: ["id"] }],
      (classId) => positions[classId] ?? null,
      (hintId) => (hintId === "join-table:r1" ? { x: 999, y: 888 } : null),
    );

    const [hint] = elements;
    expect(hint!.position).toEqual({ x: 999, y: 888 });
  });

  it("skips a hint whose relationship id is not in the model", async () => {
    const { joinTableHintElements } = await import("@/components/workspace/DiagramCanvas");

    const elements = joinTableHintElements(
      model,
      [{ relationship_id: "no-such-relationship", table_name: "x", columns: ["id"] }],
      () => ({ x: 0, y: 0 }),
    );

    expect(elements).toHaveLength(0);
  });

  it("skips a hint whose endpoint has no known position yet", async () => {
    const { joinTableHintElements } = await import("@/components/workspace/DiagramCanvas");

    const elements = joinTableHintElements(
      model,
      [{ relationship_id: "r1", table_name: "class_a_class_b", columns: ["id"] }],
      () => null,
    );

    expect(elements).toHaveLength(0);
  });
});

/**
 * Operations compartment (design.md DD9/DD10, spec "Diagram Rendering"):
 * a second compartment below attributes, separated by a divider, in UML
 * notation `{visibility symbol} {name}({parameters}): {returnType}`. A
 * class with zero operations MUST render byte-identically to the
 * attribute-only case — additive-only layout math.
 */
describe("DiagramCanvas — operations compartment (DD9/DD10)", () => {
  it("renders an operations compartment below attributes, separated by a divider, in UML notation", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [
        {
          id: "c1",
          name: "Cliente",
          visibility: "public",
          attributes: [{ id: "a1", name: "nombre", type: "String", visibility: "private" }],
          operations: [
            {
              id: "o1",
              name: "crearUsuario",
              return_type: "String",
              parameters: [],
              visibility: "public",
            },
          ],
        },
      ],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };

    const elements = toElements(model);
    const node = elements[0]!;
    const svg = decodeURIComponent((node.data.bgImage as string).replace("data:image/svg+xml,", ""));

    expect(svg).toContain("+ crearUsuario(): String");
    // Two dividers: one under the name compartment, one under attributes.
    expect((svg.match(/<line/g) ?? []).length).toBe(2);
  });

  it("renders an operation with no return type without a ': {returnType}' suffix, distinct from one with a return type", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const model: UmlModel = {
      classes: [
        {
          id: "c1",
          name: "Cliente",
          visibility: "public",
          attributes: [],
          operations: [
            { id: "o1", name: "eliminar", return_type: null, parameters: [], visibility: "public" },
            {
              id: "o2",
              name: "crearUsuario",
              return_type: "String",
              parameters: [],
              visibility: "public",
            },
          ],
        },
      ],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };

    const elements = toElements(model);
    const svg = decodeURIComponent(
      (elements[0]!.data.bgImage as string).replace("data:image/svg+xml,", ""),
    );

    expect(svg).toContain("+ eliminar()");
    expect(svg).not.toContain("eliminar(): ");
    expect(svg).toContain("+ crearUsuario(): String");
  });

  it("a class with zero operations renders byte-identically to the attribute-only case (SVG, width, height)", async () => {
    const { toElements } = await import("@/components/workspace/DiagramCanvas");

    const withoutOperationsField: UmlModel = {
      classes: [
        {
          id: "c1",
          name: "Cliente",
          visibility: "public",
          attributes: [{ id: "a1", name: "nombre", type: "String", visibility: "private" }],
          operations: [],
        },
      ],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };

    const elements = toElements(withoutOperationsField);
    const node = elements[0]!;

    // Pinned against the pre-operations-cycle shape: one divider (name only)
    // and no operations compartment markup at all.
    const svg = decodeURIComponent((node.data.bgImage as string).replace("data:image/svg+xml,", ""));
    expect((svg.match(/<line/g) ?? []).length).toBe(1);
    expect(svg).toContain("nombre: String");

    const expectedWidth = 150; // MIN_BOX_WIDTH floor for this short content
    expect(node.data.width).toBeGreaterThanOrEqual(expectedWidth);
    // height: PADDING_Y*2 + NAME_LINE_HEIGHT + DIVIDER_MARGIN*2 + 1 attr line
    expect(node.data.height).toBe(10 * 2 + 24 + 8 * 2 + 1 * 18);
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
    nodes: vi.fn(() => ({ removeClass: vi.fn(), forEach: vi.fn() })),
    // Used by `syncJoinTableHints` (join-table hints, design.md DD177), a
    // no-op here since none of these lifecycle tests pass `joinTableHints`.
    $: vi.fn(() => ({ remove: vi.fn() })),
    add: vi.fn(),
    getElementById: vi.fn(
      (): {
        addClass: ReturnType<typeof vi.fn>;
        removeClass: ReturnType<typeof vi.fn>;
        ungrabify: ReturnType<typeof vi.fn>;
        grabify: ReturnType<typeof vi.fn>;
        length: number;
        position: ReturnType<typeof vi.fn>;
      } => ({
        addClass: vi.fn(),
        removeClass: vi.fn(),
        ungrabify: vi.fn(),
        grabify: vi.fn(),
        length: 0,
        position: vi.fn(() => ({ x: 0, y: 0 })),
      }),
    ),
  },
}));

/** A fake Cytoscape node, shaped like `cy.getElementById(id)`'s return. */
function createNodeMock(id: string, initialPosition = { x: 0, y: 0 }) {
  let position = initialPosition;
  return {
    id: () => id,
    // Every real node here is a class, never a join-table hint (DD177) —
    // `undefined` matches Cytoscape's own `data(key)` for an unset key.
    data: vi.fn(() => undefined),
    addClass: vi.fn(),
    removeClass: vi.fn(),
    ungrabify: vi.fn(),
    grabify: vi.fn(),
    length: 1,
    position: vi.fn((next?: { x: number; y: number }) => {
      if (next === undefined) return position;
      position = next;
      return undefined;
    }),
  };
}

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
      ...createNodeMock("unused"),
      length: 1,
      position: vi.fn(() => ({ x: 10, y: 20 })),
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
      target: { id: () => string; data: (key: string) => unknown };
    }) => void;

    const onNodeTapB = vi.fn();
    rerender(<DiagramCanvas model={emptyModel} revision={1} onNodeTap={onNodeTapB} />);

    tapHandler({ target: { id: () => "c1", data: () => undefined } });

    expect(onNodeTapA).not.toHaveBeenCalled();
    expect(onNodeTapB).toHaveBeenCalledWith("c1");
    // Mount binds 5 handlers once: node tap (DD9), edge tap (double-tap edit), and
    // grab/drag/free (DD11/DD12's claim/live-position/release + drag
    // guard) — each registered exactly once.
    expect(cyMock.on).toHaveBeenCalledTimes(5);
    expect(cyMock.on).toHaveBeenCalledWith("tap", "node", expect.any(Function));
    expect(cyMock.on).toHaveBeenCalledWith("grab", "node", expect.any(Function));
    expect(cyMock.on).toHaveBeenCalledWith("drag", "node", expect.any(Function));
    expect(cyMock.on).toHaveBeenCalledWith("free", "node", expect.any(Function));
  });

  it("a second tap on the same edge within the double-tap window calls onEdgeEdit; taps on different edges or too far apart do not", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const onEdgeEdit = vi.fn();
    render(<DiagramCanvas model={emptyModel} revision={1} onEdgeEdit={onEdgeEdit} />);
    const edgeTap = cyMock.on.mock.calls.find(([event, selector]) => event === "tap" && selector === "edge")![2] as (e: {
      target: { id: () => string; data: (key: string) => unknown };
    }) => void;
    const tap = (id: string) => edgeTap({ target: { id: () => id, data: () => undefined } });

    vi.useFakeTimers();
    try {
      tap("r1");
      tap("r2"); // different edge: starts a new pair
      expect(onEdgeEdit).not.toHaveBeenCalled();

      tap("r2");
      expect(onEdgeEdit).toHaveBeenCalledExactlyOnceWith("r2");

      tap("r1");
      vi.advanceTimersByTime(1000); // outside the window
      tap("r1");
      expect(onEdgeEdit).toHaveBeenCalledOnce();
    } finally {
      vi.useRealTimers();
    }
  });

  it("performs no cy.json() while draggingRef is set on a revision bump, and the free event flushes exactly one deferred sync (DD12)", async () => {
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

    const { rerender } = render(<DiagramCanvas model={oneClass} revision={1} />);
    cyMock.json.mockClear();
    cyMock.layout.mockClear();

    const grabHandler = cyMock.on.mock.calls.find(([event]) => event === "grab")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    const freeHandler = cyMock.on.mock.calls.find(([event]) => event === "free")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    const node = createNodeMock("c1");

    grabHandler({ target: node });

    // A remote update arrives mid-drag: the sync must be deferred, not
    // applied immediately.
    rerender(<DiagramCanvas model={twoClasses} revision={2} />);
    expect(cyMock.json).not.toHaveBeenCalled();

    // The drag ends: exactly one deferred sync flushes.
    freeHandler({ target: node });
    expect(cyMock.json).toHaveBeenCalledOnce();
  });

  it("a revision bump while not dragging syncs immediately, and free with no pending update is a no-op (DD12)", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");

    const { rerender } = render(<DiagramCanvas model={emptyModel} revision={1} />);
    cyMock.json.mockClear();

    const freeHandler = cyMock.on.mock.calls.find(([event]) => event === "free")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    const node = createNodeMock("c1");

    rerender(<DiagramCanvas model={emptyModel} revision={2} />);
    expect(cyMock.json).toHaveBeenCalledOnce();

    cyMock.json.mockClear();
    freeHandler({ target: node });
    expect(cyMock.json).not.toHaveBeenCalled();
  });

  it("toggles the selected-source class on highlightedClassId change without re-running layout", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const removeClass = vi.fn();
    cyMock.nodes.mockReturnValue({ removeClass, forEach: vi.fn() });
    const addClass = vi.fn();
    cyMock.getElementById.mockReturnValue({
      ...createNodeMock("unused"),
      addClass,
      length: 1,
      position: vi.fn(() => ({ x: 0, y: 0 })),
    });

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

  // --- Phase 6: drag emits claim/live-position/release, foreign lock
  // rendering, claim rejection, remote live frames (design.md DD11/DD12) ---

  it("grabbing a node calls onClaim with the class id before the drag proceeds", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const onClaim = vi.fn();

    render(<DiagramCanvas model={emptyModel} revision={1} onClaim={onClaim} />);

    const grabHandler = cyMock.on.mock.calls.find(([event]) => event === "grab")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    grabHandler({ target: createNodeMock("c1", { x: 5, y: 7 }) });

    expect(onClaim).toHaveBeenCalledWith("c1");
  });

  it("dragging a node calls onLivePosition with its current coordinates on every drag tick", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const onLivePosition = vi.fn();

    render(<DiagramCanvas model={emptyModel} revision={1} onLivePosition={onLivePosition} />);

    const dragHandler = cyMock.on.mock.calls.find(([event]) => event === "drag")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    dragHandler({ target: createNodeMock("c1", { x: 11, y: 22 }) });

    expect(onLivePosition).toHaveBeenCalledWith("c1", 11, 22);
  });

  it("releasing a node calls onRelease with its final coordinates exactly once", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const onRelease = vi.fn();

    render(<DiagramCanvas model={emptyModel} revision={1} onRelease={onRelease} />);

    const freeHandler = cyMock.on.mock.calls.find(([event]) => event === "free")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    freeHandler({ target: createNodeMock("c1", { x: 33, y: 44 }) });

    expect(onRelease).toHaveBeenCalledTimes(1);
    expect(onRelease).toHaveBeenCalledWith("c1", 33, 44);
  });

  it("ungrabifies and tags a foreign-held node with .locked-remote; releasing the lock re-grabifies and untags it", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const node = createNodeMock("c1");
    cyMock.nodes.mockReturnValue({
      removeClass: vi.fn(),
      forEach: vi.fn((cb: (n: ReturnType<typeof createNodeMock>) => void) => cb(node)),
    });

    const { rerender } = render(
      <DiagramCanvas model={emptyModel} revision={1} locks={{ c1: { ownerLabel: "Ana", mine: false } }} />,
    );

    expect(node.ungrabify).toHaveBeenCalled();
    expect(node.addClass).toHaveBeenCalledWith("locked-remote");

    rerender(<DiagramCanvas model={emptyModel} revision={1} locks={{}} />);

    expect(node.grabify).toHaveBeenCalled();
    expect(node.removeClass).toHaveBeenCalledWith("locked-remote");
  });

  it("node.claim_rejected (via claimRejectedListenerRef) restores the node's stashed grab-start position", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const claimRejectedListenerRef = { current: null as ((classId: string) => void) | null };
    const restoreTarget = createNodeMock("c1");
    cyMock.getElementById.mockReturnValue(restoreTarget);

    render(
      <DiagramCanvas model={emptyModel} revision={1} claimRejectedListenerRef={claimRejectedListenerRef} />,
    );

    const grabHandler = cyMock.on.mock.calls.find(([event]) => event === "grab")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    grabHandler({ target: createNodeMock("c1", { x: 100, y: 200 }) });

    expect(claimRejectedListenerRef.current).toBeTypeOf("function");
    claimRejectedListenerRef.current!("c1");

    expect(restoreTarget.position).toHaveBeenCalledWith({ x: 100, y: 200 });
  });

  it("positionListenerRef moves a node imperatively via getElementById(...).position(...) without calling cy.json again", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const positionListenerRef = {
      current: null as ((classId: string, x: number, y: number) => void) | null,
    };
    const target = createNodeMock("c1");
    cyMock.getElementById.mockReturnValue(target);

    render(<DiagramCanvas model={emptyModel} revision={1} positionListenerRef={positionListenerRef} />);
    cyMock.json.mockClear();

    expect(positionListenerRef.current).toBeTypeOf("function");
    positionListenerRef.current!("c1", 42, 84);

    expect(target.position).toHaveBeenCalledWith({ x: 42, y: 84 });
    expect(cyMock.json).not.toHaveBeenCalled();
  });

  it("an empty layout.positions still runs the full first-layout fcose path with randomize: true (DD13 fallback)", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");

    render(<DiagramCanvas model={emptyModel} revision={1} layout={{ positions: {} }} />);

    expect(cyMock.layout).toHaveBeenCalledWith(expect.objectContaining({ name: "fcose", randomize: true }));
  });

  it("removing the held class mid-drag does not crash; free still fires and the deferred sync flushes cleanly (task 7.1, Local Node Removed While Held Drops the Local Lock)", async () => {
    const { DiagramCanvas } = await import("@/components/workspace/DiagramCanvas");
    const oneClass: UmlModel = {
      classes: [{ id: "c1", name: "A", visibility: "public", attributes: [], operations: [] }],
      enumerations: [],
      relationships: [],
      generation_metadata: {},
    };
    const noClasses: UmlModel = { ...oneClass, classes: [] };
    const onRelease = vi.fn();

    const { rerender } = render(<DiagramCanvas model={oneClass} revision={1} onRelease={onRelease} />);
    cyMock.json.mockClear();

    const grabHandler = cyMock.on.mock.calls.find(([event]) => event === "grab")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    const freeHandler = cyMock.on.mock.calls.find(([event]) => event === "free")![2] as (e: {
      target: ReturnType<typeof createNodeMock>;
    }) => void;
    const node = createNodeMock("c1", { x: 7, y: 8 });

    grabHandler({ target: node });

    // The class is removed by a `RemoveClass` command from any client
    // while still held locally — the drag guard defers the sync instead
    // of yanking the node out from under the user's cursor.
    expect(() =>
      rerender(<DiagramCanvas model={noClasses} revision={2} onRelease={onRelease} />),
    ).not.toThrow();
    expect(cyMock.json).not.toHaveBeenCalled();

    // The drag ends: release still fires with the node's last position,
    // and the deferred sync (now against the class-less model) flushes
    // without crashing — cy.json's own diffing removes the node.
    expect(() => freeHandler({ target: node })).not.toThrow();
    expect(onRelease).toHaveBeenCalledWith("c1", 7, 8);
    expect(cyMock.json).toHaveBeenCalledOnce();
  });
});
