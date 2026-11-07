import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TemplateCatalogDialog } from "@/components/workspace/TemplateCatalogDialog";
import { listTemplates, type UmlTemplateSummary } from "@/lib/uml_documents";

vi.mock("@/lib/uml_documents", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/uml_documents")>()),
  listTemplates: vi.fn(),
}));

const base = { source_document_id: "doc-1", created_by_id: "user-1", created_at: "2026-11-07T00:00:00Z" };

const sales: UmlTemplateSummary = {
  ...base,
  id: "template-1",
  name: "Sales",
  preview: {
    classes: [
      { id: "c1", name: "Customer", attributes: 2, x: 0, y: 0 },
      { id: "c2", name: "Order", attributes: 1, x: 200, y: 0 },
    ],
    relationships: [{ source: "c1", target: "c2", kind: "association" }],
  },
};

const library: UmlTemplateSummary = {
  ...base,
  id: "template-2",
  name: "Library",
  preview: { classes: [{ id: "b1", name: "Book", attributes: 1, x: 0, y: 0 }], relationships: [] },
};

describe("TemplateCatalogDialog", () => {
  it("instantiates the selected organization template as a new diagram", async () => {
    vi.mocked(listTemplates).mockResolvedValueOnce([sales]);
    const onInstantiate = vi.fn().mockResolvedValue({ id: "doc-2" });

    render(<TemplateCatalogDialog open onOpenChange={vi.fn()} orgSlug="acme" onInstantiate={onInstantiate} />);

    await screen.findByRole("radio", { name: /Sales/ });
    fireEvent.change(screen.getByLabelText("Nombre del nuevo diagrama"), { target: { value: "Q1 sales" } });
    fireEvent.click(screen.getByRole("button", { name: "Usar plantilla" }));

    await waitFor(() => expect(onInstantiate).toHaveBeenCalledWith("template-1", { name: "Q1 sales" }));
  });

  it("shows a thumbnail with a class and relationship summary for every template", async () => {
    vi.mocked(listTemplates).mockResolvedValueOnce([sales, library]);

    render(<TemplateCatalogDialog open onOpenChange={vi.fn()} orgSlug="acme" onInstantiate={vi.fn()} />);

    await screen.findByRole("radio", { name: /Sales/ });
    expect(screen.getAllByTestId("template-thumbnail")).toHaveLength(2);
    expect(screen.getByText("Customer")).toBeInTheDocument();
    expect(screen.getByText("2 clases · 1 relación")).toBeInTheDocument();
    expect(screen.getByText("1 clase · 0 relaciones")).toBeInTheDocument();
  });

  it("uses the template chosen by the user, not just the first one", async () => {
    vi.mocked(listTemplates).mockResolvedValueOnce([sales, library]);
    const onInstantiate = vi.fn().mockResolvedValue({ id: "doc-3" });

    render(<TemplateCatalogDialog open onOpenChange={vi.fn()} orgSlug="acme" onInstantiate={onInstantiate} />);

    fireEvent.click(await screen.findByRole("radio", { name: /Library/ }));
    fireEvent.change(screen.getByLabelText("Nombre del nuevo diagrama"), { target: { value: "My library" } });
    fireEvent.click(screen.getByRole("button", { name: "Usar plantilla" }));

    await waitFor(() => expect(onInstantiate).toHaveBeenCalledWith("template-2", { name: "My library" }));
  });
});
