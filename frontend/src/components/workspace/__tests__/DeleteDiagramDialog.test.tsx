import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DeleteDiagramDialog } from "@/components/workspace/DeleteDiagramDialog";
import { ApiError } from "@/lib/api";

function setup(onConfirm: () => Promise<void>) {
  const onOpenChange = vi.fn();
  render(
    <DeleteDiagramDialog open onOpenChange={onOpenChange} diagramName="Ventas" onConfirm={onConfirm} />,
  );
  return onOpenChange;
}

describe("DeleteDiagramDialog", () => {
  it("asks for confirmation and closes only after the delete succeeds", async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onOpenChange = setup(onConfirm);

    expect(screen.getByText(/¿Eliminar este diagrama\? Esta acción no se puede deshacer\./)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Eliminar diagrama" }));

    await vi.waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it.each([
    [new ApiError({ status: 403, code: "forbidden", detail: "x" }), /No tienes permiso/],
    [new ApiError({ status: 500, code: "http_500", detail: "x" }), /No se pudo eliminar/],
  ])("keeps the dialog open with a friendly message on failure", async (error, message) => {
    const onOpenChange = setup(vi.fn().mockRejectedValue(error));

    fireEvent.click(screen.getByRole("button", { name: "Eliminar diagrama" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(onOpenChange).not.toHaveBeenCalled();
  });
});
