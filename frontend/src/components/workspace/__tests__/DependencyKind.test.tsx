import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AddRelationshipControl } from "@/components/workspace/AddRelationshipControl";
import { STYLE, toElements } from "@/components/workspace/DiagramCanvas";
import { EditRelationshipDialog } from "@/components/workspace/EditRelationshipDialog";
import type { Relationship, UmlModel } from "@/lib/uml_documents";

const classes = [
  { id: "c1", name: "Pedido", visibility: "public" as const, attributes: [], operations: [] },
  { id: "c2", name: "Calculadora", visibility: "public" as const, attributes: [], operations: [] },
];

const dependency: Relationship = {
  id: "d1",
  kind: "dependency",
  source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
  target: { class_id: "c2", multiplicity: { lower: 1, upper: 1 }, role: null },
  name: "usa",
};

describe("a UML 2.5 dependency on the canvas", () => {
  it("is a dashed line with an open arrow at the supplier, and no loop geometry of its own", () => {
    const rule = STYLE.find((item) => item.selector === 'edge[kind = "dependency"]')!;

    expect(rule).toBeDefined();
    expect(rule.style).toMatchObject({ "line-style": "dashed", "target-arrow-shape": "vee" });
    expect(rule.style).not.toHaveProperty("loop-direction");
  });

  it("is drawn from the client to the supplier, and its neutral 1..1 is not printed on the line", () => {
    const model: UmlModel = { classes, enumerations: [], relationships: [dependency], generation_metadata: {} };

    const edge = toElements(model).find((element) => element.data.id === "d1")!;

    expect(edge.data).toMatchObject({ source: "c1", target: "c2", kind: "dependency", label: "usa" });
    expect(edge.data.sourceLabel).toBe("");
    expect(edge.data.targetLabel).toBe("");
  });
});

describe("adding a dependency", () => {
  const renderControl = (onSubmit = vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } })) => {
    render(
      <AddRelationshipControl
        pendingSourceId="c1"
        pendingTargetId="c2"
        classes={classes}
        onSubmit={onSubmit}
        onCancel={vi.fn()}
        onSelectSelf={vi.fn()}
      />,
    );
    return onSubmit;
  };

  it("is offered as 'Dependencia'", () => {
    renderControl();

    const select = screen.getByLabelText("Tipo de relación") as HTMLSelectElement;
    expect(within(select).getByRole("option", { name: "Dependencia" })).toHaveValue("dependency");
  });

  it("asks for no multiplicity and sends the neutral 1 and 1", async () => {
    const onSubmit = renderControl();

    fireEvent.change(screen.getByLabelText("Tipo de relación"), { target: { value: "dependency" } });
    expect(screen.queryByLabelText("Multiplicidad origen")).toBeNull();
    expect(screen.queryByLabelText("Multiplicidad destino")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Confirmar relación" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0][0].relationship).toMatchObject({
      kind: "dependency",
      source: { class_id: "c1", multiplicity: "1" },
      target: { class_id: "c2", multiplicity: "1" },
    });
  });
});

describe("editing a dependency", () => {
  it("only lets you change its name, since a dependency has no multiplicities", () => {
    render(<EditRelationshipDialog relationship={dependency} classes={classes} onSubmit={vi.fn()} onClose={vi.fn()} />);

    expect(screen.getByLabelText("Nombre")).toBeTruthy();
    expect(screen.queryByLabelText("Multiplicidad en Pedido")).toBeNull();
    expect(screen.queryByLabelText("Multiplicidad en Calculadora")).toBeNull();
  });
});
