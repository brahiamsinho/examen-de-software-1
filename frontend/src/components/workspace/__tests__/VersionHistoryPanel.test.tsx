import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VersionHistoryPanel } from "@/components/workspace/VersionHistoryPanel";
import { createVersion, listVersions } from "@/lib/uml_documents";

vi.mock("@/lib/uml_documents", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/uml_documents")>()),
  listVersions: vi.fn(),
  createVersion: vi.fn(),
  compareVersions: vi.fn(),
  restoreVersion: vi.fn(),
}));

const version = {
  id: "version-1",
  number: 1,
  source_revision: 2,
  description: "Before customer",
  created_by_id: "user-1",
  created_at: "2026-11-06T10:00:00Z",
};

describe("VersionHistoryPanel", () => {
  beforeEach(() => {
    vi.mocked(listVersions).mockResolvedValue([version]);
    vi.mocked(createVersion).mockResolvedValue({
      ...version,
      snapshot: { metadata: { name: "Diagram", description: "" }, model: { classes: [], enumerations: [], relationships: [], generation_metadata: {} }, layout: { positions: {} } },
    });
  });

  it("shows historical versions to a viewer without write controls", async () => {
    render(<VersionHistoryPanel orgSlug="acme" docId="doc-1" revision={2} canEdit={false} onRestored={async () => {}} />);

    expect(await screen.findByText("V1 · revisión 2 · Before customer")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Guardar versión" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Restaurar" })).not.toBeInTheDocument();
  });

  it("creates a version using the visible document revision", async () => {
    render(<VersionHistoryPanel orgSlug="acme" docId="doc-1" revision={2} canEdit onRestored={async () => {}} />);
    await screen.findByText("V1 · revisión 2 · Before customer");

    fireEvent.change(screen.getByLabelText("Descripción de versión"), { target: { value: "Before release" } });
    fireEvent.click(screen.getByRole("button", { name: "Guardar versión" }));

    await waitFor(() => expect(createVersion).toHaveBeenCalledWith("acme", "doc-1", {
      description: "Before release",
      expected_revision: 2,
    }));
  });
});
