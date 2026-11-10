import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AiProposalsPanel } from "@/components/workspace/AiProposalsPanel";
import type { AiProposal } from "@/lib/ai_proposals";

// 0 class Pedido, 1 Pedido.total, 2 class Cliente
const proposal: AiProposal = {
  id: "p1",
  document_id: "d1",
  status: "pending",
  prompt: "¿Qué le falta al diagrama?",
  base_revision: 3,
  changes: [
    { ok: true, message: "Created class 'Pedido'" },
    { ok: true, message: "Added attribute 'total' to 'Pedido'" },
    { ok: true, message: "Created class 'Cliente'" },
  ],
  calls: [
    { name: "add_class", args: { name: "Pedido" } },
    { name: "add_attribute", args: { class_name: "Pedido", attribute_name: "total", attribute_type: "Decimal" } },
    { name: "add_class", args: { name: "Cliente" } },
  ],
  applied_indices: null,
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
    error: null,
    onApprove: vi.fn(),
    onReject: vi.fn(),
    ...overrides,
  };
  render(<AiProposalsPanel {...props} />);
  return props;
}

const box = (name: string) => screen.getByRole("checkbox", { name }) as HTMLInputElement;

describe("AiProposalsPanel", () => {
  it("shows who asked and every proposed change as a checked option", () => {
    renderPanel();

    expect(screen.getByText(/Pedida por Ana/)).toBeInTheDocument();
    expect(screen.getByText(/¿Qué le falta al diagrama\?/)).toBeInTheDocument();
    expect(box("Created class 'Pedido'").checked).toBe(true);
    expect(box("Added attribute 'total' to 'Pedido'").checked).toBe(true);
    expect(box("Created class 'Cliente'").checked).toBe(true);
    expect(screen.getByRole("button", { name: "Aprobar todo (3)" })).toBeInTheDocument();
  });

  it("approves only the chosen changes", () => {
    const props = renderPanel();

    fireEvent.click(box("Created class 'Cliente'"));
    fireEvent.click(screen.getByRole("button", { name: "Aprobar selección (2)" }));

    expect(props.onApprove).toHaveBeenCalledWith("p1", [0, 1]);
  });

  it("approves everything when nothing was unchecked", () => {
    const props = renderPanel();

    fireEvent.click(screen.getByRole("button", { name: "Aprobar todo (3)" }));

    expect(props.onApprove).toHaveBeenCalledWith("p1", [0, 1, 2]);
  });

  it("unchecking a class also unchecks its attribute", () => {
    renderPanel();

    fireEvent.click(box("Created class 'Pedido'"));

    expect(box("Created class 'Pedido'").checked).toBe(false);
    expect(box("Added attribute 'total' to 'Pedido'").checked).toBe(false);
    expect(box("Created class 'Cliente'").checked).toBe(true);
  });

  it("checking an attribute also checks the class it belongs to", () => {
    renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Ninguno" }));

    fireEvent.click(box("Added attribute 'total' to 'Pedido'"));

    expect(box("Added attribute 'total' to 'Pedido'").checked).toBe(true);
    expect(box("Created class 'Pedido'").checked).toBe(true);
    expect(box("Created class 'Cliente'").checked).toBe(false);
  });

  it("offers select all and select none, and cannot approve an empty selection", () => {
    renderPanel();

    fireEvent.click(screen.getByRole("button", { name: "Ninguno" }));
    expect(screen.getByRole("button", { name: "Aprobar selección (0)" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Todos" }));
    expect(screen.getByRole("button", { name: "Aprobar todo (3)" })).toBeEnabled();
  });

  it("keeps each proposal's selection separate", () => {
    const other = { ...proposal, id: "p2", prompt: "otra" };
    renderPanel({ proposals: [proposal, other] });

    fireEvent.click(screen.getAllByRole("button", { name: "Ninguno" })[0]!);

    expect(screen.getByRole("button", { name: "Aprobar selección (0)" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Aprobar todo (3)" })).toBeEnabled();
  });

  it("lets an editor reject a proposal", () => {
    const props = renderPanel();

    fireEvent.click(screen.getByRole("button", { name: "Rechazar" }));

    expect(props.onReject).toHaveBeenCalledWith("p1");
  });

  it("has no box to ask the AI: ideas are asked in the team chat with @IA", () => {
    renderPanel({ proposals: [] });

    expect(screen.queryByLabelText("Pide ideas a la IA")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Pedir ideas" })).not.toBeInTheDocument();
    expect(screen.getByText(/chat del equipo/)).toBeInTheDocument();
    expect(screen.getByText(/@IA/)).toBeInTheDocument();
  });

  it("gives a viewer a read-only list with no checkboxes and no way to ask, approve or reject", () => {
    renderPanel({ canDecide: false });

    expect(screen.getByText("Created class 'Pedido'")).toBeInTheDocument();
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Aprobar/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rechazar" })).not.toBeInTheDocument();
    expect(screen.getByText(/Solo un editor puede aprobar/)).toBeInTheDocument();
  });

  it("leaves a change that cannot be applied unchecked and disabled, and still approves the rest", () => {
    const props = renderPanel({
      proposals: [
        {
          ...proposal,
          changes: [
            { ok: true, message: "Created class 'Pedido'" },
            { ok: false, message: "Class 'Ghost' does not exist" },
            { ok: true, message: "Created class 'Cliente'" },
          ],
          calls: [
            { name: "add_class", args: { name: "Pedido" } },
            { name: "rename_class", args: { class_name: "Ghost", new_name: "X" } },
            { name: "add_class", args: { name: "Cliente" } },
          ],
        },
      ],
    });

    const broken = box("Class 'Ghost' does not exist");
    expect(broken.checked).toBe(false);
    expect(broken.disabled).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: "Aprobar selección (2)" }));
    expect(props.onApprove).toHaveBeenCalledWith("p1", [0, 2]);
  });

  it("disables the decision buttons of the proposal being processed", () => {
    renderPanel({ busyId: "p1" });

    expect(screen.getByRole("button", { name: "Aprobar todo (3)" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Rechazar" })).toBeDisabled();
  });

  it("explains the empty state and surfaces an error", () => {
    renderPanel({ proposals: [], error: "La IA no tuvo sugerencias." });

    expect(screen.getByText(/No hay propuestas pendientes/)).toBeInTheDocument();
    expect(screen.getByText("La IA no tuvo sugerencias.")).toBeInTheDocument();
  });
});
