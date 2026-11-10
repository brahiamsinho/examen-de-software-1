import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ActivityLogDialog } from "@/components/workspace/ActivityLogDialog";
import type { LogEntry, LogSession } from "@/lib/session_log";

const entries: LogEntry[] = [
  {
    id: "000000000000000000000001",
    session: 1,
    kind: "change",
    author: "Ana",
    author_id: "u1",
    is_ai: false,
    summary: "AddClass Pedido",
    data: { commands: [{ type: "AddClass", label: "Pedido" }], total: 1 },
    created_at: "2026-11-07T10:00:00+00:00",
  },
  {
    id: "000000000000000000000002",
    session: 1,
    kind: "proposal.created",
    author: "IA",
    author_id: null,
    is_ai: true,
    summary: "AI proposed 2 changes",
    data: { changes: ["a", "b"], requested_by: "Ana" },
    created_at: "2026-11-07T10:05:00+00:00",
  },
  {
    id: "000000000000000000000003",
    session: 2,
    kind: "chat.message",
    author: "Luis",
    author_id: "u2",
    is_ai: false,
    summary: "Yo hago Cliente",
    data: { message_id: 4 },
    created_at: "2026-11-07T12:00:00+00:00",
  },
];

const sessions: LogSession[] = [
  {
    session: 1,
    started_at: "2026-11-07T10:00:00+00:00",
    ended_at: "2026-11-07T10:05:00+00:00",
    entries: 2,
    actors: [{ id: "u1", label: "Ana", is_ai: false }, { id: null, label: "IA", is_ai: true }],
  },
  {
    session: 2,
    started_at: "2026-11-07T12:00:00+00:00",
    ended_at: "2026-11-07T12:00:00+00:00",
    entries: 1,
    actors: [{ id: "u2", label: "Luis", is_ai: false }],
  },
];

function renderDialog(overrides: Partial<React.ComponentProps<typeof ActivityLogDialog>> = {}) {
  const props = {
    open: true,
    onOpenChange: vi.fn(),
    entries,
    sessions,
    filters: {},
    loading: false,
    error: null,
    exporting: false,
    exportError: null,
    onFiltersChange: vi.fn(),
    onExport: vi.fn(),
    onReload: vi.fn(),
    ...overrides,
  };
  render(<ActivityLogDialog {...props} />);
  return props;
}

describe("ActivityLogDialog", () => {
  it("lists every entry with its author, kind and what happened, in Spanish", () => {
    renderDialog();

    expect(screen.getByText("Agregó la clase «Pedido»")).toBeInTheDocument();
    expect(screen.getByText("Propuso 2 cambios, a petición de Ana")).toBeInTheDocument();
    expect(screen.getByText("Yo hago Cliente")).toBeInTheDocument();
    expect(screen.getAllByText("Ana").length).toBeGreaterThan(0);
    expect(screen.getByText("Cambio")).toBeInTheDocument();
    expect(screen.getByText("Propuesta de la IA")).toBeInTheDocument();
    expect(screen.getByText("Chat")).toBeInTheDocument();
  });

  it("offers every session in the session filter and applies the chosen one", () => {
    const props = renderDialog();
    const select = screen.getByLabelText("Sesión");

    expect(Array.from((select as HTMLSelectElement).options).map((option) => option.text)).toEqual([
      "Todas las sesiones",
      expect.stringContaining("Sesión 1"),
      expect.stringContaining("Sesión 2"),
    ]);

    fireEvent.change(select, { target: { value: "2" } });

    expect(props.onFiltersChange).toHaveBeenCalledWith({ session: 2 });
  });

  it("offers the people and the AI in the user filter, and applies the chosen one", () => {
    const props = renderDialog({ filters: { session: 1 } });
    const select = screen.getByLabelText("Usuario");

    expect(Array.from((select as HTMLSelectElement).options).map((option) => option.text)).toEqual([
      "Todos los usuarios",
      "Ana",
      "IA",
      "Luis",
    ]);

    fireEvent.change(select, { target: { value: "ai" } });

    expect(props.onFiltersChange).toHaveBeenCalledWith({ session: 1, user: "ai" });
  });

  it("clears a filter when 'all' is chosen again", () => {
    const props = renderDialog({ filters: { session: 2, user: "u2" } });

    fireEvent.change(screen.getByLabelText("Sesión"), { target: { value: "" } });

    expect(props.onFiltersChange).toHaveBeenCalledWith({ user: "u2" });
  });

  it("reflects the filters that are active", () => {
    renderDialog({ filters: { session: 2, user: "u2" } });

    expect((screen.getByLabelText("Sesión") as HTMLSelectElement).value).toBe("2");
    expect((screen.getByLabelText("Usuario") as HTMLSelectElement).value).toBe("u2");
  });

  it("exports with one click and can reload", () => {
    const props = renderDialog();

    fireEvent.click(screen.getByRole("button", { name: "Exportar CSV" }));
    fireEvent.click(screen.getByRole("button", { name: "Actualizar" }));

    expect(props.onExport).toHaveBeenCalledTimes(1);
    expect(props.onReload).toHaveBeenCalledTimes(1);
  });

  it("shows the busy and the failure states of the export", () => {
    renderDialog({ exporting: true, exportError: "No se pudo exportar la bitácora." });

    expect(screen.getByRole("button", { name: "Exportando..." })).toBeDisabled();
    expect(screen.getByText("No se pudo exportar la bitácora.")).toBeInTheDocument();
  });

  it("explains an empty log", () => {
    renderDialog({ entries: [], sessions: [] });

    expect(screen.getByText(/Todavía no hay registros/)).toBeInTheDocument();
  });

  it("says it is loading", () => {
    renderDialog({ loading: true, entries: [] });
    expect(screen.getByText("Cargando bitácora...")).toBeInTheDocument();
  });

  it("shows a load error instead of an empty list", () => {
    renderDialog({ error: "No se pudo cargar la bitácora.", entries: [] });
    expect(screen.getByText("No se pudo cargar la bitácora.")).toBeInTheDocument();
    expect(screen.queryByText(/Todavía no hay registros/)).not.toBeInTheDocument();
  });

  it("tells who can see it and that chat messages are in it", () => {
    renderDialog();

    expect(screen.getByText(/Solo los miembros de la organización/)).toBeInTheDocument();
    expect(screen.getByText(/mensajes del chat/)).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    renderDialog({ open: false });

    expect(screen.queryByText("Bitácora")).not.toBeInTheDocument();
  });
});
