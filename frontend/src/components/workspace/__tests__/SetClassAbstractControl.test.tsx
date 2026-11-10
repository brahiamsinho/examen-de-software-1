import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SetClassAbstractControl } from "@/components/workspace/SetClassAbstractControl";
import { ApiError } from "@/lib/api";

const classes = [
  { id: "c1", name: "Forma", visibility: "public" as const, attributes: [], operations: [], is_abstract: true },
  { id: "c2", name: "Pedido", visibility: "public" as const, attributes: [], operations: [] },
];

const ok = { revision: 2, validation: { is_valid: true, violations: [] } };

describe("SetClassAbstractControl", () => {
  it("has nothing to do until a class is chosen", () => {
    render(<SetClassAbstractControl classes={classes} onSubmit={vi.fn()} />);

    expect(screen.getByRole("button", { name: "Marcar como abstracta" })).toBeDisabled();
  });

  it("marks a concrete class abstract", async () => {
    const onSubmit = vi.fn().mockResolvedValue(ok);
    render(<SetClassAbstractControl classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c2" } });
    expect(screen.getByText("Pedido es concreta.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Marcar como abstracta" }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({ type: "SetClassAbstract", class_id: "c2", is_abstract: true }),
    );
  });

  it("makes an abstract class concrete again", async () => {
    const onSubmit = vi.fn().mockResolvedValue(ok);
    render(<SetClassAbstractControl classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    expect(screen.getByText("Forma es abstracta.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Quitar abstracta" }));

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({ type: "SetClassAbstract", class_id: "c1", is_abstract: false }),
    );
  });

  it("shows the server's explanation when the change is refused", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new ApiError({ status: 403, code: "forbidden", detail: "No tienes permiso para editar." }));
    render(<SetClassAbstractControl classes={classes} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c2" } });
    fireEvent.click(screen.getByRole("button", { name: "Marcar como abstracta" }));

    expect(await screen.findByText("No tienes permiso para editar.")).toBeInTheDocument();
  });

  it("cannot be used while another command is being sent", () => {
    render(<SetClassAbstractControl classes={classes} onSubmit={vi.fn()} disabled />);

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c2" } });

    expect(screen.getByRole("button", { name: "Marcar como abstracta" })).toBeDisabled();
  });
});
