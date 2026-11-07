import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as proposalsLib from "@/lib/ai_proposals";
import * as docsLib from "@/lib/uml_documents";
import { useDocument } from "@/state/document";

vi.mock("@/lib/uml_documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/uml_documents")>("@/lib/uml_documents");
  return { ...actual, getDocument: vi.fn(), openDocumentSocket: vi.fn() };
});

vi.mock("@/lib/ai_proposals", async () => {
  const actual = await vi.importActual<typeof import("@/lib/ai_proposals")>("@/lib/ai_proposals");
  return { ...actual, listProposals: vi.fn() };
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

const pendingProposal = {
  id: "p1",
  document_id: "doc-a",
  status: "pending" as const,
  prompt: "ideas",
  base_revision: 1,
  changes: [],
  calls: [],
  applied_indices: null,
  requested_by: "Ana",
  decided_by: null,
  created_at: "2026-11-07T10:00:00Z",
  decided_at: null,
};

function lastSocketHandlers() {
  const calls = vi.mocked(docsLib.openDocumentSocket).mock.calls;
  return calls[calls.length - 1]![2];
}

describe("state/document useDocument() — AI proposals (issue #15)", () => {
  beforeEach(() => {
    vi.mocked(docsLib.getDocument).mockReset();
    vi.mocked(docsLib.getDocument).mockResolvedValue(documentA);
    vi.mocked(docsLib.openDocumentSocket).mockReset();
    vi.mocked(docsLib.openDocumentSocket).mockImplementation(() => ({ close: vi.fn() }) as never);
    vi.mocked(proposalsLib.listProposals).mockReset();
    vi.mocked(proposalsLib.listProposals).mockResolvedValue([]);
  });

  it("loads the pending proposals whenever the socket opens", async () => {
    vi.mocked(proposalsLib.listProposals).mockResolvedValue([pendingProposal]);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    act(() => lastSocketHandlers().onOpen?.());

    await waitFor(() => expect(result.current.proposals).toEqual([pendingProposal]));
    expect(proposalsLib.listProposals).toHaveBeenCalledWith("acme", "doc-a");
  });

  it("adds a live proposal and drops it once it is decided", async () => {
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    act(() => lastSocketHandlers().onProposal?.(pendingProposal));
    expect(result.current.proposals).toEqual([pendingProposal]);

    act(() => lastSocketHandlers().onProposal?.({ ...pendingProposal, status: "approved" }));
    expect(result.current.proposals).toEqual([]);
  });

  it("keeps the document usable when the proposals request fails", async () => {
    vi.mocked(proposalsLib.listProposals).mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    act(() => lastSocketHandlers().onOpen?.());

    await waitFor(() => expect(proposalsLib.listProposals).toHaveBeenCalled());
    expect(result.current.proposals).toEqual([]);
    expect(result.current.document).toEqual(documentA);
  });
});
