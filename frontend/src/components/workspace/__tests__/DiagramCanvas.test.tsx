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
    expect(clienteNode.data.label).toContain("Cliente");
    expect(clienteNode.data.label).toContain("nombre");

    const edges = elements.filter((el) => "source" in el.data);
    expect(edges).toHaveLength(1);
    expect(edges[0]!.data).toMatchObject({ id: "r1", source: "c1", target: "c2" });
    expect(edges[0]!.data.label).toBe("1 → 0..*");
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

const { cyMock } = vi.hoisted(() => ({
  cyMock: {
    on: vi.fn(),
    destroy: vi.fn(),
    json: vi.fn(),
    layout: vi.fn(() => ({ run: vi.fn() })),
    nodes: vi.fn(() => ({ removeClass: vi.fn() })),
    getElementById: vi.fn(() => ({ addClass: vi.fn() })),
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
    cyMock.getElementById.mockReturnValue({ addClass });

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
