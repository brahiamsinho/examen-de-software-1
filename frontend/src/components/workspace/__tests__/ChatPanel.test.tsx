import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { ChatPanel } from "@/components/workspace/ChatPanel";
import type { ChatMessage } from "@/lib/ai_chat";

beforeAll(() => {
  // jsdom does not implement scrolling; the panel scrolls to the newest message.
  Element.prototype.scrollIntoView = vi.fn();
});

const messages: ChatMessage[] = [
  { id: 1, document_id: "d1", author: "Ana", author_id: "u1", is_ai: false, content: "¿Quién toma Pedido?", created_at: "2026-11-07T10:00:00Z" },
  { id: 2, document_id: "d1", author: "Luis", author_id: "u2", is_ai: false, content: "Yo, @IA ¿qué falta?", created_at: "2026-11-07T10:01:00Z" },
  { id: 3, document_id: "d1", author: "IA", author_id: null, is_ai: true, content: "Falta Cliente.", created_at: "2026-11-07T10:02:00Z" },
];

function renderPanel(overrides: Partial<React.ComponentProps<typeof ChatPanel>> = {}) {
  const props = {
    messages,
    canWrite: true,
    error: null,
    onSend: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
  render(<ChatPanel {...props} />);
  return props;
}

describe("ChatPanel", () => {
  it("shows every message with its author, the AI included", () => {
    renderPanel();

    expect(screen.getByText("Ana")).toBeInTheDocument();
    expect(screen.getByText("Luis")).toBeInTheDocument();
    expect(screen.getByText("IA")).toBeInTheDocument();
    expect(screen.getByText("¿Quién toma Pedido?")).toBeInTheDocument();
    expect(screen.getByText("Falta Cliente.")).toBeInTheDocument();
  });

  it("explains the empty state and how to wake the AI", () => {
    renderPanel({ messages: [] });

    expect(screen.getByText(/Todavía no hay mensajes/)).toBeInTheDocument();
    expect(screen.getByText(/@IA/)).toBeInTheDocument();
  });

  it("sends the trimmed text and clears the field", async () => {
    const props = renderPanel();
    const field = screen.getByLabelText("Mensaje para el equipo");

    fireEvent.change(field, { target: { value: "  hola equipo  " } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(props.onSend).toHaveBeenCalledWith("hola equipo"));
    await waitFor(() => expect(field).toHaveValue(""));
  });

  it("sends with Enter but keeps Shift+Enter for a new line", () => {
    const props = renderPanel();
    const field = screen.getByLabelText("Mensaje para el equipo");
    fireEvent.change(field, { target: { value: "uno" } });

    fireEvent.keyDown(field, { key: "Enter", shiftKey: true });
    expect(props.onSend).not.toHaveBeenCalled();

    fireEvent.keyDown(field, { key: "Enter" });
    expect(props.onSend).toHaveBeenCalledWith("uno");
  });

  it("does not send an empty message", () => {
    renderPanel();

    expect(screen.getByRole("button", { name: "Enviar" })).toBeDisabled();
  });

  it("puts the text back when sending fails and the field is still empty", async () => {
    renderPanel({ onSend: vi.fn().mockRejectedValue(new Error("fail")) });
    const field = screen.getByLabelText("Mensaje para el equipo");

    fireEvent.change(field, { target: { value: "importante" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(field).toHaveValue("importante"));
  });

  it("shows that the AI is thinking only while a message that mentions it is pending", async () => {
    let finish: () => void = () => {};
    renderPanel({ onSend: vi.fn(() => new Promise<void>((resolve) => (finish = resolve))) });
    const field = screen.getByLabelText("Mensaje para el equipo");

    fireEvent.change(field, { target: { value: "@IA ayuda" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    expect(await screen.findByText(/La IA está pensando/)).toBeInTheDocument();
    finish();
    await waitFor(() => expect(screen.queryByText(/La IA está pensando/)).not.toBeInTheDocument());
  });

  it("does not show the thinking state for a message that does not mention the AI", async () => {
    renderPanel({ onSend: vi.fn(() => new Promise<void>(() => {})) });
    const field = screen.getByLabelText("Mensaje para el equipo");

    fireEvent.change(field, { target: { value: "hola" } });
    fireEvent.click(screen.getByRole("button", { name: "Enviar" }));

    await waitFor(() => expect(field).toHaveValue(""));
    expect(screen.queryByText(/La IA está pensando/)).not.toBeInTheDocument();
  });

  it("gives a viewer a read-only chat with no field and no send button", () => {
    renderPanel({ canWrite: false });

    expect(screen.getByText("Falta Cliente.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Mensaje para el equipo")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Enviar" })).not.toBeInTheDocument();
    expect(screen.getByText(/Solo un editor puede escribir/)).toBeInTheDocument();
  });

  it("surfaces an error", () => {
    renderPanel({ error: "La IA no respondió a tiempo." });

    expect(screen.getByText("La IA no respondió a tiempo.")).toBeInTheDocument();
  });
});
