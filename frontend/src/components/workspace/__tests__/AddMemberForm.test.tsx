import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AddMemberForm } from "@/components/workspace/AddMemberForm";
import { ApiError } from "@/lib/api";

/**
 * `CreateOrgForm` clone (design.md File Changes): local state, no fetch, no
 * atom access. Spec `web-member-management` § Add Member by Email — role
 * selector limited to EDITOR/VIEWER, submit calls `onAdd`, rejection renders
 * `ApiError.detail` in `role="alert"` without clearing the form.
 */
const created = {
  user_id: "3",
  email: "new@example.com",
  full_name: "New Member",
  role: "EDITOR" as const,
  created_at: "2026-01-01T00:00:00Z",
};

describe("AddMemberForm", () => {
  it("the role selector offers only EDITOR and VIEWER", () => {
    render(<AddMemberForm onAdd={vi.fn()} />);

    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Editor", "Lector"]);
  });

  it("submits the entered email and selected role to onAdd", async () => {
    const onAdd = vi.fn().mockResolvedValueOnce(created);

    render(<AddMemberForm onAdd={onAdd} />);
    fireEvent.change(screen.getByLabelText("Correo electrónico"), {
      target: { value: "new@example.com" },
    });
    fireEvent.change(screen.getByLabelText("Rol"), { target: { value: "VIEWER" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar miembro" }));

    await waitFor(() =>
      expect(onAdd).toHaveBeenCalledWith({ email: "new@example.com", role: "VIEWER" }),
    );
  });

  it("clears the form after a successful add", async () => {
    const onAdd = vi.fn().mockResolvedValueOnce(created);

    render(<AddMemberForm onAdd={onAdd} />);
    const emailInput = screen.getByLabelText("Correo electrónico") as HTMLInputElement;
    fireEvent.change(emailInput, { target: { value: "new@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar miembro" }));

    await waitFor(() => expect(emailInput.value).toBe(""));
  });

  it("shows the backend detail in role=alert and does not clear the form on rejection", async () => {
    const onAdd = vi
      .fn()
      .mockRejectedValueOnce(
        new ApiError({
          status: 404,
          code: "user_not_found",
          detail: "No existe un usuario con ese correo.",
        }),
      );

    render(<AddMemberForm onAdd={onAdd} />);
    fireEvent.change(screen.getByLabelText("Correo electrónico"), {
      target: { value: "ghost@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Agregar miembro" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No existe un usuario con ese correo.",
    );
    expect(onAdd).toHaveBeenCalledOnce();
    expect(screen.getByLabelText("Correo electrónico")).toHaveValue("ghost@example.com");
  });
});
