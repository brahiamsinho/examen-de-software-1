import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RemoveAttributeControl } from "@/components/workspace/RemoveAttributeControl";

const classes = [
  {
    id: "c1",
    name: "Cliente",
    visibility: "public" as const,
    attributes: [
      { id: "a1", name: "nombre", type: "String" as const, visibility: "private" as const },
      { id: "a2", name: "email", type: "String" as const, visibility: "private" as const },
    ],
    operations: [],
  },
  {
    id: "c2",
    name: "Pedido",
    visibility: "public" as const,
    attributes: [
      { id: "a3", name: "total", type: "Decimal" as const, visibility: "private" as const },
    ],
    operations: [],
  },
];

/**
 * Presentational (design.md DD2/DD3). Attribute options are scoped to the
 * selected class's own `attributes` (attribute ids are only unique within a
 * class — DD1). Submission is immediate, no confirmation step.
 */
describe("RemoveAttributeControl", () => {
  it("selecting a class populates the attribute select with exactly that class's attributes", () => {
    render(<RemoveAttributeControl classes={classes} onSubmit={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });

    const attributeSelect = screen.getByLabelText("Atributo");
    const optionLabels = Array.from(attributeSelect.querySelectorAll("option"))
      .map((o) => o.textContent)
      .filter((label) => label !== "Selecciona un atributo");
    expect(optionLabels).toEqual(["nombre", "email"]);
  });

  it("changing the selected class clears the attribute selection", () => {
    render(<RemoveAttributeControl classes={classes} onSubmit={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("Atributo"), { target: { value: "a1" } });
    expect(screen.getByLabelText("Atributo")).toHaveValue("a1");

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c2" } });
    expect(screen.getByLabelText("Atributo")).toHaveValue("");
  });

  it("submits RemoveAttribute immediately with no confirmation step", async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    render(<RemoveAttributeControl classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("Atributo"), { target: { value: "a2" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar atributo" }));

    await vi.waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
    expect(onSubmit).toHaveBeenCalledWith({
      type: "RemoveAttribute",
      class_id: "c1",
      attribute_id: "a2",
    });
    expect(screen.queryByText(/confirmar/i)).not.toBeInTheDocument();
  });

  it("the class disappearing after a refetch resets both selects without crashing", () => {
    const { rerender } = render(<RemoveAttributeControl classes={classes} onSubmit={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("Atributo"), { target: { value: "a1" } });

    rerender(<RemoveAttributeControl classes={[classes[1]!]} onSubmit={vi.fn()} />);

    expect(screen.getByLabelText("Clase")).toHaveValue("");
    expect(screen.getByLabelText("Atributo")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Eliminar atributo" })).toBeDisabled();
  });
});
