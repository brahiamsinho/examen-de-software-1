import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AddOperationForm } from "@/components/workspace/AddOperationForm";
import { PRIMITIVE_TYPES } from "@/lib/uml_documents";

const classes = [
  { id: "c1", name: "Cliente", visibility: "public" as const, attributes: [], operations: [] },
  { id: "c2", name: "Pedido", visibility: "public" as const, attributes: [], operations: [] },
];

/**
 * Presentational (design.md DD8), mirror of `AddAttributeForm`. The
 * return-type select's first option is "Sin tipo de retorno" followed by
 * the eight `PRIMITIVE_TYPES` — no `enumeration_ref` option this cycle. No
 * parameter input is rendered; submitted `parameters` is always `()`.
 */
describe("AddOperationForm", () => {
  it("renders class select, name input, return-type select ('Sin tipo de retorno' first, then PRIMITIVE_TYPES), and a visibility select defaulting to public", () => {
    render(<AddOperationForm classes={classes} onSubmit={vi.fn()} />);

    const returnTypeSelect = screen.getByLabelText("Tipo de retorno");
    const options = Array.from(returnTypeSelect.querySelectorAll("option")).map((o) => o.value);
    expect(options).toEqual(["", ...PRIMITIVE_TYPES]);
    expect(returnTypeSelect.querySelector("option[value='']")?.textContent).toBe(
      "Sin tipo de retorno",
    );

    expect(screen.getByLabelText("Visibilidad")).toHaveValue("public");
    expect(screen.getByLabelText("Nombre de la operación")).toBeInTheDocument();
  });

  it("does not render any parameter input", () => {
    render(<AddOperationForm classes={classes} onSubmit={vi.fn()} />);

    expect(screen.queryByLabelText(/parámetro/i)).not.toBeInTheDocument();
  });

  it("submitting with a return type selected sends return_type as that primitive; no parameters field on the wire (v1 always () server-side)", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    render(<AddOperationForm classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c2" } });
    fireEvent.change(screen.getByLabelText("Nombre de la operación"), {
      target: { value: "crearUsuario" },
    });
    fireEvent.change(screen.getByLabelText("Tipo de retorno"), { target: { value: "String" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar operación" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "AddOperation",
        class_id: "c2",
        operation: expect.objectContaining({ name: "crearUsuario", return_type: "String" }),
      }),
    );
    const submittedOperation = onSubmit.mock.calls[0]![0].operation;
    expect(submittedOperation).not.toHaveProperty("parameters");

    await vi.waitFor(() => {
      expect(screen.getByLabelText("Nombre de la operación")).toHaveValue("");
    });
  });

  it("submitting with 'Sin tipo de retorno' sends return_type: null", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    render(<AddOperationForm classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Nombre de la operación"), {
      target: { value: "guardar" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Agregar operación" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "AddOperation",
        operation: expect.objectContaining({ name: "guardar", return_type: null }),
      }),
    );
  });

  it("re-derives the selected class when it mounts with zero classes and one is added later (production bug fix, mirrors AddAttributeForm)", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    const { rerender } = render(<AddOperationForm classes={[]} onSubmit={onSubmit} />);

    rerender(<AddOperationForm classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Nombre de la operación"), { target: { value: "crear" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar operación" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ type: "AddOperation", class_id: "c1" }),
    );
  });
});
