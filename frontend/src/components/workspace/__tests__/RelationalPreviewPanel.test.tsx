import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { RelationalPreviewPanel } from "@/components/workspace/RelationalPreviewPanel";
import { ApiError } from "@/lib/api";
import * as previewClient from "@/lib/relational_preview";

vi.mock("@/lib/relational_preview", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/relational_preview")>()),
  getRelationalPreview: vi.fn(),
}));

afterEach(() => vi.restoreAllMocks());

describe("RelationalPreviewPanel", () => {
  it("renders returned tables, keys and SQL", async () => {
    vi.mocked(previewClient.getRelationalPreview).mockResolvedValue({
      tables: [{ name: "orders", columns: [{ name: "id", type: "UUID", nullable: false, primary_key: true }, { name: "customer_id", type: "UUID", nullable: false, primary_key: false }], foreign_keys: [{ name: "fk_orders__customer_id", columns: ["customer_id"], referenced_table: "customers", referenced_columns: ["id"], on_delete: "NO ACTION", on_update: "NO ACTION", relationship_id: "r1" }] }],
      sql: 'CREATE TABLE "orders" ();',
    });
    render(<RelationalPreviewPanel orgSlug="acme" docId="doc-1" documentName="Orders" />);

    fireEvent.click(screen.getByRole("button", { name: "Generar vista previa" }));

    expect(await screen.findByText("orders")).toBeInTheDocument();
    expect(screen.getByText("PK")).toBeInTheDocument();
    expect(screen.getByText("FK → customers")).toBeInTheDocument();
    expect(screen.getByText('CREATE TABLE "orders" ();')).toBeInTheDocument();
  });

  it("shows actionable backend errors", async () => {
    vi.mocked(previewClient.getRelationalPreview).mockRejectedValue(new ApiError({ status: 422, code: "empty_model", detail: "Agrega una clase" }));
    render(<RelationalPreviewPanel orgSlug="acme" docId="doc-1" documentName="Orders" />);

    fireEvent.click(screen.getByRole("button", { name: "Generar vista previa" }));

    await waitFor(() => expect(screen.getByText("Agrega una clase")).toBeInTheDocument());
  });
});
