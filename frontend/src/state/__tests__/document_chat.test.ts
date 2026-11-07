import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as chatLib from "@/lib/ai_chat";
import * as docsLib from "@/lib/uml_documents";
import { useDocument } from "@/state/document";

vi.mock("@/lib/uml_documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/uml_documents")>("@/lib/uml_documents");
  return { ...actual, getDocument: vi.fn(), openDocumentSocket: vi.fn() };
});

vi.mock("@/lib/ai_chat", async () => {
  const actual = await vi.importActual<typeof import("@/lib/ai_chat")>("@/lib/ai_chat");
  return { ...actual, listChat: vi.fn() };
});

vi.mock("@/lib/ai_proposals", async () => {
  const actual = await vi.importActual<typeof import("@/lib/ai_proposals")>("@/lib/ai_proposals");
  return { ...actual, listProposals: vi.fn().mockResolvedValue([]) };
});

const documentA = {
  id: "doc-a",
  owner_id: "1",
  revision: 1,
  metadata: { name: "Ventas", description: "" },
  model: { classes: [], enumerations: [], relationships: [], generation_metadata: {} },
  layout: { positions: {} },
  created_at: "2026-09-12T10:00:00Z",
  updated_at: "2026-09-12T10:00:00Z",
};

const message = (id: number): chatLib.ChatMessage => ({
  id,
  document_id: "doc-a",
  author: "Ana",
  author_id: "u1",
  is_ai: false,
  content: `m${id}`,
  created_at: "2026-11-07T10:00:00Z",
});

function lastSocketHandlers() {
  const calls = vi.mocked(docsLib.openDocumentSocket).mock.calls;
  return calls[calls.length - 1]![2];
}

describe("state/document useDocument() — group chat (issue #16)", () => {
  beforeEach(() => {
    vi.mocked(docsLib.getDocument).mockReset();
    vi.mocked(docsLib.getDocument).mockResolvedValue(documentA);
    vi.mocked(docsLib.openDocumentSocket).mockReset();
    vi.mocked(docsLib.openDocumentSocket).mockImplementation(() => ({ close: vi.fn() }) as never);
    vi.mocked(chatLib.listChat).mockReset();
    vi.mocked(chatLib.listChat).mockResolvedValue([]);
  });

  it("loads the chat history whenever the socket opens", async () => {
    vi.mocked(chatLib.listChat).mockResolvedValue([message(1), message(2)]);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    act(() => lastSocketHandlers().onOpen?.());

    await waitFor(() => expect(result.current.chatMessages.map((m) => m.id)).toEqual([1, 2]));
    expect(chatLib.listChat).toHaveBeenCalledWith("acme", "doc-a");
  });

  it("adds live messages in order and ignores a repeat of the same one", async () => {
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    act(() => lastSocketHandlers().onChat?.(message(2)));
    act(() => lastSocketHandlers().onChat?.(message(1)));
    act(() => lastSocketHandlers().onChat?.(message(2)));

    expect(result.current.chatMessages.map((m) => m.id)).toEqual([1, 2]);
  });

  it("does not lose a live message that arrives while the history is loading", async () => {
    let resolveHistory: (messages: chatLib.ChatMessage[]) => void = () => {};
    vi.mocked(chatLib.listChat).mockReturnValue(new Promise((resolve) => (resolveHistory = resolve)));
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));
    act(() => lastSocketHandlers().onOpen?.());

    act(() => lastSocketHandlers().onChat?.(message(3)));
    await act(async () => resolveHistory([message(1), message(2)]));

    expect(result.current.chatMessages.map((m) => m.id)).toEqual([1, 2, 3]);
  });

  it("applies a message returned by an HTTP call without duplicating the socket copy", async () => {
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    act(() => lastSocketHandlers().onChat?.(message(1)));
    act(() => result.current.applyChatMessage(message(1)));

    expect(result.current.chatMessages).toHaveLength(1);
  });

  it("keeps the document usable when the history request fails", async () => {
    vi.mocked(chatLib.listChat).mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    act(() => lastSocketHandlers().onOpen?.());

    await waitFor(() => expect(chatLib.listChat).toHaveBeenCalled());
    expect(result.current.chatMessages).toEqual([]);
    expect(result.current.document).toEqual(documentA);
  });
});
