import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CreateDocumentForm } from "@/components/workspace/CreateDocumentForm";

/**
 * Mirrors `CreateOrgForm` (DD14): the form is props-in/callback-out and
 * does not call `useRouter` itself — navigation belongs to the dashboard
 * container's handler.
 */
describe("CreateDocumentForm", () => {
  it("submitting a name calls onCreate({name})", async () => {
    const onCreate = vi.fn().mockResolvedValue({ id: "doc-1" });
    render(<CreateDocumentForm onCreate={onCreate} />);

    fireEvent.change(screen.getByLabelText("Nombre del diagrama"), { target: { value: "Ventas" } });
    fireEvent.click(screen.getByRole("button", { name: "Crear diagrama" }));

    expect(onCreate).toHaveBeenCalledWith({ name: "Ventas" });
  });

  it("does not call useRouter itself", () => {
    // If this component imported/called `useRouter` outside a router
    // context, rendering it without a mocked "next/navigation" would throw.
    expect(() => render(<CreateDocumentForm onCreate={vi.fn()} />)).not.toThrow();
  });
});
