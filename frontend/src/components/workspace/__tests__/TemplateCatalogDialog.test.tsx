import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TemplateCatalogDialog } from "@/components/workspace/TemplateCatalogDialog";
import { listTemplates } from "@/lib/uml_documents";

vi.mock("@/lib/uml_documents", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/uml_documents")>()),
  listTemplates: vi.fn(),
}));

describe("TemplateCatalogDialog", () => {
  it("instantiates the selected organization template as a new diagram", async () => {
    vi.mocked(listTemplates).mockResolvedValueOnce([
      { id: "template-1", name: "Sales", source_document_id: "doc-1", created_by_id: "user-1", created_at: "2026-11-07T00:00:00Z" },
    ]);
    const onInstantiate = vi.fn().mockResolvedValue({ id: "doc-2" });

    render(<TemplateCatalogDialog open onOpenChange={vi.fn()} orgSlug="acme" onInstantiate={onInstantiate} />);

    await screen.findByRole("option", { name: "Sales" });
    fireEvent.change(screen.getByLabelText("Nombre del nuevo diagrama"), { target: { value: "Q1 sales" } });
    fireEvent.click(screen.getByRole("button", { name: "Usar plantilla" }));

    await waitFor(() => expect(onInstantiate).toHaveBeenCalledWith("template-1", { name: "Q1 sales" }));
  });
});
