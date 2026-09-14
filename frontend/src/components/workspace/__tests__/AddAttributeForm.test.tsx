import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AddAttributeForm } from "@/components/workspace/AddAttributeForm";
import { PRIMITIVE_TYPES } from "@/lib/uml_documents";

const classes = [
  { id: "c1", name: "Cliente", visibility: "public" as const, attributes: [], operations: [] },
  { id: "c2", name: "Pedido", visibility: "public" as const, attributes: [], operations: [] },
];

/**
 * Presentational (design.md File Changes). The type select renders only the
 * eight `PRIMITIVE_TYPES` (spec "Enumeration types are not offered" —
 * `enumeration_ref` has no UI this cycle).
 */
describe("AddAttributeForm", () => {
  it("renders only the eight PRIMITIVE_TYPES options, no enumeration option", () => {
    render(<AddAttributeForm classes={classes} onSubmit={vi.fn()} />);

    const typeSelect = screen.getByLabelText("Tipo");
    const options = Array.from(typeSelect.querySelectorAll("option")).map((o) => o.value);
    expect(options).toEqual([...PRIMITIVE_TYPES]);
  });

  it("submitting calls onSubmit with an AddAttribute command for the selected class and clears the name on success", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    render(<AddAttributeForm classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c2" } });
    fireEvent.change(screen.getByLabelText("Nombre del atributo"), { target: { value: "total" } });
    fireEvent.change(screen.getByLabelText("Tipo"), { target: { value: "Decimal" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar atributo" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "AddAttribute",
        class_id: "c2",
        attribute: expect.objectContaining({ name: "total", type: "Decimal" }),
      }),
    );

    await vi.waitFor(() => {
      expect(screen.getByLabelText("Nombre del atributo")).toHaveValue("");
    });
  });

  it("re-derives the selected class when it mounts with zero classes and one is added later (production bug fix)", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    const { rerender } = render(<AddAttributeForm classes={[]} onSubmit={onSubmit} />);

    rerender(<AddAttributeForm classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Nombre del atributo"), { target: { value: "nombre" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar atributo" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ type: "AddAttribute", class_id: "c1" }),
    );
  });
});
