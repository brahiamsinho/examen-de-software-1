import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RemoveRelationshipControl } from "@/components/workspace/RemoveRelationshipControl";

const classes = [
  { id: "c1", name: "Cliente", visibility: "public" as const, attributes: [], operations: [] },
  { id: "c2", name: "Pedido", visibility: "public" as const, attributes: [], operations: [] },
];

const relationships = [
  {
    id: "r1",
    kind: "association" as const,
    source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
    target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
    name: null,
  },
  {
    id: "r2",
    kind: "composition" as const,
    source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
    target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
    name: null,
  },
];

/**
 * Presentational (design.md DD2/DD6). Option labels identify a relationship
 * by its endpoint class names and kind — multiplicity does not disambiguate
 * two relationships between the same class pair. Dangling relationships
 * (an endpoint no longer resolves to a class) are listed, not filtered,
 * using the raw `class_id` fallback — this control is the only way to
 * delete one, since `toElements` drops them from the canvas.
 */
describe("RemoveRelationshipControl", () => {
  it("labels an association from Cliente to Pedido as 'Cliente → Pedido (association)'", () => {
    render(
      <RemoveRelationshipControl classes={classes} relationships={[relationships[0]!]} onSubmit={vi.fn()} />,
    );

    const select = screen.getByLabelText("Relación");
    expect(screen.getByRole("option", { name: "Cliente → Pedido (association)" })).toBeInTheDocument();
    expect(select).toBeInTheDocument();
  });

  it("two relationships between the same classes remain distinguishable by kind", () => {
    render(
      <RemoveRelationshipControl classes={classes} relationships={relationships} onSubmit={vi.fn()} />,
    );

    expect(screen.getByRole("option", { name: "Cliente → Pedido (association)" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Cliente → Pedido (composition)" })).toBeInTheDocument();
  });

  it("a dangling relationship still appears using its raw class_id fallback", () => {
    const dangling = [
      {
        id: "r3",
        kind: "association" as const,
        source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
        target: { class_id: "missing-id", multiplicity: { lower: 1, upper: 1 }, role: null },
        name: null,
      },
    ];
    render(<RemoveRelationshipControl classes={classes} relationships={dangling} onSubmit={vi.fn()} />);

    expect(
      screen.getByRole("option", { name: "Cliente → missing-id (association)" }),
    ).toBeInTheDocument();
  });

  it("submits RemoveRelationship immediately with no confirmation step", async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    render(
      <RemoveRelationshipControl classes={classes} relationships={[relationships[0]!]} onSubmit={onSubmit} />,
    );

    fireEvent.change(screen.getByLabelText("Relación"), { target: { value: "r1" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar relación" }));

    await vi.waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
    expect(onSubmit).toHaveBeenCalledWith({ type: "RemoveRelationship", relationship_id: "r1" });
    expect(screen.queryByText(/confirmar/i)).not.toBeInTheDocument();
  });

  it("the selected relationship disappearing after a refetch resets the selection", () => {
    const { rerender } = render(
      <RemoveRelationshipControl classes={classes} relationships={relationships} onSubmit={vi.fn()} />,
    );

    fireEvent.change(screen.getByLabelText("Relación"), { target: { value: "r1" } });
    expect(screen.getByLabelText("Relación")).toHaveValue("r1");

    rerender(
      <RemoveRelationshipControl classes={classes} relationships={[relationships[1]!]} onSubmit={vi.fn()} />,
    );

    expect(screen.getByLabelText("Relación")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Eliminar relación" })).toBeDisabled();
  });
});
