import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ArchitectureAuditPanel } from "@/components/workspace/ArchitectureAuditPanel";
import { ApiError } from "@/lib/api";
import * as auditClient from "@/lib/architecture_audit";

vi.mock("@/lib/architecture_audit", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/architecture_audit")>()),
  getArchitectureAudit: vi.fn(),
}));

afterEach(() => vi.restoreAllMocks());

describe("ArchitectureAuditPanel", () => {
  it("renders findings, evidence, summary and exports", async () => {
    vi.mocked(auditClient.getArchitectureAudit).mockResolvedValue({
      contract_version: "1.0", rules_version: "1.0", document: { id: "doc-1", revision: 3 },
      summary: { ERROR: 0, WARNING: 1, INFO: 0 },
      findings: [{ id: "ar-002-test", rule_id: "AR-002", rule_name: "Acoplamiento elevado", rule_purpose: "Detecta relaciones directas", severity: "WARNING", title: "Acoplamiento elevado", explanation: "Demasiadas relaciones", evidence: "Clase Order (order) con 5 relaciones.", element_ids: ["order"], recommendation: "Separar responsabilidades." }],
    });
    render(<ArchitectureAuditPanel orgSlug="acme" docId="doc-1" documentName="Orders" />);
    fireEvent.click(screen.getByRole("button", { name: "Ejecutar auditoría" }));
    expect(await screen.findByText("Acoplamiento elevado")).toBeInTheDocument();
    expect(screen.getByText(/Clase Order/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descargar JSON" })).toBeInTheDocument();
  });

  it("shows an empty state and backend errors", async () => {
    vi.mocked(auditClient.getArchitectureAudit).mockResolvedValueOnce({
      contract_version: "1.0", rules_version: "1.0", document: { id: "doc-1", revision: 3 }, summary: { ERROR: 0, WARNING: 0, INFO: 0 }, findings: [],
    });
    render(<ArchitectureAuditPanel orgSlug="acme" docId="doc-1" documentName="Orders" />);
    fireEvent.click(screen.getByRole("button", { name: "Ejecutar auditoría" }));
    expect(await screen.findByText(/No se encontraron riesgos/)).toBeInTheDocument();

    vi.mocked(auditClient.getArchitectureAudit).mockRejectedValueOnce(new ApiError({ status: 422, code: "bad", detail: "No disponible" }));
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));
    await waitFor(() => expect(screen.getByText("No disponible")).toBeInTheDocument());
  });
});
