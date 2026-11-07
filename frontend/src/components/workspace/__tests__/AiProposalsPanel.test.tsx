import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AiProposalsPanel } from "@/components/workspace/AiProposalsPanel";
import type { AiProposal } from "@/lib/ai_proposals";

const proposal: AiProposal = {
  id: "p1",
  document_id: "d1",
  status: "pending",
  prompt: "¿Qué le falta al diagrama?",
  base_revision: 3,
  changes: [
    { ok: true, message: "Crear la clase Pedido" },
    { ok: true, message: "Agregar total a Pedido" },
  ],
  calls: [],
  requested_by: "Ana",
  decided_by: null,
  created_at: "2026-11-07T10:00:00Z",
  decided_at: null,
};

function renderPanel(overrides: Partial<React.ComponentProps<typeof AiProposalsPanel>> = {}) {
  const props = {
    proposals: [proposal],
    canDecide: true,
    busyId: null,
    asking: false,
    error: null,
    onAsk: vi.fn().mockResolvedValue(undefined),
    onApprove: vi.fn(),
    onReject: vi.fn(),
    ...overrides,
  };
  render(<AiProposalsPanel {...props} />);
  return props;
}

describe("AiProposalsPanel", () => {
  it("shows who asked, what they asked and every proposed change", () => {
    renderPanel();

    expect(screen.getByText(/Pedida por Ana/)).toBeInTheDocument();
    expect(screen.getByText(/¿Qué le falta al diagrama\?/)).toBeInTheDocument();
    expect(screen.getByText("Crear la clase Pedido")).toBeInTheDocument();
    expect(screen.getByText("Agregar total a Pedido")).toBeInTheDocument();
  });

  it("lets an editor approve or reject a proposal", () => {
    const props = renderPanel();

    fireEvent.click(screen.getByRole("button", { name: "Aprobar" }));
    fireEvent.click(screen.getByRole("button", { name: "Rechazar" }));

    expect(props.onApprove).toHaveBeenCalledWith("p1");
    expect(props.onReject).toHaveBeenCalledWith("p1");
  });

  it("lets an editor ask the AI for ideas and clears the field afterwards", async () => {
    const props = renderPanel({ proposals: [] });
    const field = screen.getByLabelText("Pide ideas a la IA");

    fireEvent.change(field, { target: { value: "  Agrega pedidos  " } });
    fireEvent.click(screen.getByRole("button", { name: "Pedir ideas" }));

    await waitFor(() => expect(props.onAsk).toHaveBeenCalledWith("Agrega pedidos"));
    await waitFor(() => expect(field).toHaveValue(""));
  });

  it("does not ask with an empty prompt and keeps the text when asking fails", async () => {
    const props = renderPanel({ proposals: [], onAsk: vi.fn().mockRejectedValue(new Error("fail")) });
    const ask = screen.getByRole("button", { name: "Pedir ideas" });
    expect(ask).toBeDisabled();

    const field = screen.getByLabelText("Pide ideas a la IA");
    fireEvent.change(field, { target: { value: "ideas" } });
    fireEvent.click(ask);

    await waitFor(() => expect(props.onAsk).toHaveBeenCalled());
    expect(field).toHaveValue("ideas");
  });

  it("gives a viewer a read-only list with no way to ask, approve or reject", () => {
    renderPanel({ canDecide: false });

    expect(screen.getByText("Crear la clase Pedido")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Aprobar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rechazar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pedir ideas" })).not.toBeInTheDocument();
    expect(screen.getByText(/Solo un editor puede aprobar/)).toBeInTheDocument();
  });

  it("blocks approval when a proposed change cannot be applied", () => {
    renderPanel({
      proposals: [{ ...proposal, changes: [{ ok: false, message: "La clase Ghost no existe" }] }],
    });

    expect(screen.getByRole("button", { name: "Aprobar" })).toBeDisabled();
    expect(screen.getByText(/La clase Ghost no existe/)).toBeInTheDocument();
  });

  it("disables the decision buttons of the proposal being processed and shows asking state", () => {
    renderPanel({ busyId: "p1", asking: true });

    expect(screen.getByRole("button", { name: "Aprobar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Rechazar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Pensando..." })).toBeDisabled();
  });

  it("explains the empty state and surfaces an error", () => {
    renderPanel({ proposals: [], error: "La IA no tuvo sugerencias." });

    expect(screen.getByText(/No hay propuestas pendientes/)).toBeInTheDocument();
    expect(screen.getByText("La IA no tuvo sugerencias.")).toBeInTheDocument();
  });
});
