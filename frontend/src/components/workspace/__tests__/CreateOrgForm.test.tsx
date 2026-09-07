import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CreateOrgForm } from "@/components/workspace/CreateOrgForm";
import { ApiError } from "@/lib/api";

/**
 * Purely presentational: receives `onCreate` from its container instead of
 * calling `useOrganizations()` itself (see Deviations note — avoids a
 * second `listOrganizations()` fetch when the form is composed alongside
 * other org-state consumers). "Appears in the list / becomes active without
 * a manual refetch" (task 6.5) is exercised end-to-end at the container
 * level in `app/(app)/dashboard/__tests__/page.test.tsx`, since that is the
 * real `useOrganizations()` instance this form is wired to in production.
 */
const gamma = { id: "3", name: "Gamma", slug: "gamma", plan: "free", my_role: "OWNER" as const };

describe("CreateOrgForm", () => {
  it("derives the slug from the name and calls onCreate with both", async () => {
    const onCreate = vi.fn().mockResolvedValueOnce(gamma);

    render(<CreateOrgForm onCreate={onCreate} />);
    fireEvent.change(screen.getByLabelText("Nombre de la organización"), {
      target: { value: "Gamma" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Crear organización" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledWith({ name: "Gamma", slug: "gamma" }));
  });

  it("clears the form after a successful creation", async () => {
    const onCreate = vi.fn().mockResolvedValueOnce(gamma);

    render(<CreateOrgForm onCreate={onCreate} />);
    const nameInput = screen.getByLabelText("Nombre de la organización") as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: "Gamma" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear organización" }));

    await waitFor(() => expect(nameInput.value).toBe(""));
  });

  it("respects a manually edited slug instead of the derived one", async () => {
    const onCreate = vi.fn().mockResolvedValueOnce(gamma);

    render(<CreateOrgForm onCreate={onCreate} />);
    fireEvent.change(screen.getByLabelText("Nombre de la organización"), {
      target: { value: "Gamma" },
    });
    fireEvent.change(screen.getByLabelText("Identificador (slug)"), {
      target: { value: "custom-slug" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Crear organización" }));

    await waitFor(() =>
      expect(onCreate).toHaveBeenCalledWith({ name: "Gamma", slug: "custom-slug" }),
    );
  });

  it("shows the backend detail under the field on a duplicate slug and does not clear the form", async () => {
    const onCreate = vi
      .fn()
      .mockRejectedValueOnce(
        new ApiError({ status: 409, code: "duplicate_slug", detail: "Ese identificador ya existe." }),
      );

    render(<CreateOrgForm onCreate={onCreate} />);
    fireEvent.change(screen.getByLabelText("Nombre de la organización"), {
      target: { value: "Acme" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Crear organización" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Ese identificador ya existe.");
    expect(onCreate).toHaveBeenCalledOnce();
    expect(screen.getByLabelText("Nombre de la organización")).toHaveValue("Acme");
  });
});
