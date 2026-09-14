import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AddClassForm } from "@/components/workspace/AddClassForm";

/**
 * Presentational, props-in/callback-out like `CreateOrgForm` — receives
 * `onSubmit` from the container's `submitCommand` (design.md File Changes).
 * The `class_id` is generated client-side with `crypto.randomUUID()` (DD10).
 */
describe("AddClassForm", () => {
  it("submitting a name calls onSubmit with an AddClass command and clears the input on success", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    render(<AddClassForm onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Nombre de la clase"), { target: { value: "Cliente" } });
    fireEvent.click(screen.getByRole("button", { name: "Agregar clase" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ type: "AddClass", name: "Cliente" }),
    );
    const [[command]] = onSubmit.mock.calls;
    expect(typeof command.class_id).toBe("string");
    expect(command.class_id.length).toBeGreaterThan(0);

    await vi.waitFor(() => {
      expect(screen.getByLabelText("Nombre de la clase")).toHaveValue("");
    });
  });
});
