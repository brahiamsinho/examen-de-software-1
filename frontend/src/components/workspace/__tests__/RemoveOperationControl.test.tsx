import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RemoveOperationControl } from "@/components/workspace/RemoveOperationControl";

const classes = [
  {
    id: "c1",
    name: "Cliente",
    visibility: "public" as const,
    attributes: [],
    operations: [
      { id: "o1", name: "crear", return_type: null, parameters: [], visibility: "public" as const },
      { id: "o2", name: "guardar", return_type: "String" as const, parameters: [], visibility: "public" as const },
    ],
  },
  {
    id: "c2",
    name: "Pedido",
    visibility: "public" as const,
    attributes: [],
    operations: [
      { id: "o3", name: "cancelar", return_type: null, parameters: [], visibility: "public" as const },
    ],
  },
];

/**
 * Presentational (design.md DD8), mirror of `RemoveAttributeControl`.
 * Operation options are scoped to the selected class's own `operations`.
 * Submission is immediate, no confirmation step.
 */
describe("RemoveOperationControl", () => {
  it("selecting a class populates the operation select with exactly that class's operations", () => {
    render(<RemoveOperationControl classes={classes} onSubmit={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });

    const operationSelect = screen.getByLabelText("Operación");
    const optionLabels = Array.from(operationSelect.querySelectorAll("option"))
      .map((o) => o.textContent)
      .filter((label) => label !== "Selecciona una operación");
    expect(optionLabels).toEqual(["crear", "guardar"]);
  });

  it("changing the selected class clears the operation selection", () => {
    render(<RemoveOperationControl classes={classes} onSubmit={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("Operación"), { target: { value: "o1" } });
    expect(screen.getByLabelText("Operación")).toHaveValue("o1");

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c2" } });
    expect(screen.getByLabelText("Operación")).toHaveValue("");
  });

  it("submits RemoveOperation immediately with no confirmation step", async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    render(<RemoveOperationControl classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.change(screen.getByLabelText("Operación"), { target: { value: "o2" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar operación" }));

    await vi.waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
    expect(onSubmit).toHaveBeenCalledWith({
      type: "RemoveOperation",
      class_id: "c1",
      operation_id: "o2",
    });
    expect(screen.queryByText(/confirmar/i)).not.toBeInTheDocument();
  });
});
