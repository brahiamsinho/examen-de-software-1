import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { EditRelationshipDialog } from "@/components/workspace/EditRelationshipDialog";
import type { Relationship } from "@/lib/uml_documents";

const classes = [
  { id: "c1", name: "Cliente", visibility: "public" as const, attributes: [], operations: [] },
  { id: "c2", name: "Pedido", visibility: "public" as const, attributes: [], operations: [] },
];

const association: Relationship = {
  id: "r1",
  kind: "association",
  source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
  target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
  name: "realiza",
};

function renderDialog(relationship: Relationship | null, onSubmit = vi.fn().mockResolvedValue({}), onClose = vi.fn()) {
  render(<EditRelationshipDialog relationship={relationship} classes={classes} onSubmit={onSubmit} onClose={onClose} />);
  return { onSubmit, onClose };
}

describe("EditRelationshipDialog", () => {
  it("renders nothing while no relationship is being edited", () => {
    renderDialog(null);
    expect(screen.queryByText("Editar relación")).toBeNull();
  });

  it("shows the current name and both multiplicities, labelled with the class names", () => {
    renderDialog(association);

    expect(screen.getByText("Editar relación")).toBeTruthy();
    expect((screen.getByLabelText("Nombre") as HTMLInputElement).value).toBe("realiza");
    expect((screen.getByLabelText("Multiplicidad en Cliente") as HTMLInputElement).value).toBe("1");
    expect((screen.getByLabelText("Multiplicidad en Pedido") as HTMLInputElement).value).toBe("0..*");
  });

  it("submits an UpdateRelationship command with canonical multiplicities and closes", async () => {
    const { onSubmit, onClose } = renderDialog(association);

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "  compra  " } });
    fireEvent.change(screen.getByLabelText("Multiplicidad en Cliente"), { target: { value: "0 .. 1" } });
    fireEvent.change(screen.getByLabelText("Multiplicidad en Pedido"), { target: { value: "*" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(onSubmit).toHaveBeenCalledExactlyOnceWith({
      type: "UpdateRelationship",
      relationship_id: "r1",
      name: "compra",
      source_multiplicity: "0..1",
      target_multiplicity: "0..*",
    });
  });

  it("sends a null name when the field is cleared", async () => {
    const { onSubmit } = renderDialog(association);

    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit.mock.calls[0]![0]).toMatchObject({ name: null });
  });

  it.each(["abc", "3..1", "-1", "1..", ""])("rejects the multiplicity %j without sending anything", (value) => {
    const { onSubmit } = renderDialog(association);

    fireEvent.change(screen.getByLabelText("Multiplicidad en Cliente"), { target: { value } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));

    expect(screen.getByText("Multiplicidad inválida. Ejemplos: 1, 0..1, 0..*, 1..*")).toBeTruthy();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows only the name for a generalization and sends no multiplicities", async () => {
    const { onSubmit } = renderDialog({ ...association, kind: "generalization", name: null });

    expect(screen.queryByLabelText("Multiplicidad en Cliente")).toBeNull();
    fireEvent.change(screen.getByLabelText("Nombre"), { target: { value: "es un" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
    expect(onSubmit).toHaveBeenCalledWith({ type: "UpdateRelationship", relationship_id: "r1", name: "es un" });
  });
});
