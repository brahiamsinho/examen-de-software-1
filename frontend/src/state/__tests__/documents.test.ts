import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as docsLib from "@/lib/uml_documents";
import { useDocuments } from "@/state/documents";

/**
 * `useDocuments` owns local `useState` + a render-time tracked-slug reset
 * (design.md DD5), cloned from `useMembers`'s shape — a document list has
 * exactly one consumer (the dashboard container), so a shared Jotai atom
 * would only risk painting the previous org's documents for a frame after
 * switching. Read-only: no mutators, since `handleCreateDocument`
 * navigates away on success.
 */
vi.mock("@/lib/uml_documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/uml_documents")>("@/lib/uml_documents");
  return { ...actual, listDocuments: vi.fn() };
});

const docA = { id: "doc-1", name: "Ventas", revision: 4, updated_at: "2026-09-12T10:05:00Z" };
const docB = { id: "doc-2", name: "Compras", revision: 1, updated_at: "2026-09-11T10:00:00Z" };

describe("state/documents useDocuments()", () => {
  beforeEach(() => {
    vi.mocked(docsLib.listDocuments).mockReset();
  });

  it("stays idle and does not fetch when orgSlug is null", () => {
    const { result } = renderHook(() => useDocuments(null));

    expect(result.current.documents).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(docsLib.listDocuments).not.toHaveBeenCalled();
  });

  it("fetches documents on mount when orgSlug is provided", async () => {
    vi.mocked(docsLib.listDocuments).mockResolvedValueOnce([docA, docB]);

    const { result } = renderHook(() => useDocuments("acme"));

    await waitFor(() => expect(result.current.documents).toEqual([docA, docB]));
    expect(docsLib.listDocuments).toHaveBeenCalledWith("acme");
    expect(result.current.loading).toBe(false);
  });

  it("clears documents in the same render as the refetch when orgSlug changes", async () => {
    vi.mocked(docsLib.listDocuments).mockResolvedValueOnce([docA]);
    const { result, rerender } = renderHook(({ slug }) => useDocuments(slug), {
      initialProps: { slug: "acme" as string | null },
    });
    await waitFor(() => expect(result.current.documents).toEqual([docA]));

    vi.mocked(docsLib.listDocuments).mockResolvedValueOnce([docB]);
    rerender({ slug: "beta" });

    expect(result.current.documents).toEqual([]);

    await waitFor(() => expect(result.current.documents).toEqual([docB]));
    expect(docsLib.listDocuments).toHaveBeenCalledWith("beta");
  });

  it("a rejection sets error and leaves documents empty", async () => {
    vi.mocked(docsLib.listDocuments).mockRejectedValueOnce(new Error("boom"));

    const { result } = renderHook(() => useDocuments("acme"));

    await waitFor(() => expect(result.current.error).toBe("boom"));
    expect(result.current.documents).toEqual([]);
    expect(result.current.loading).toBe(false);
  });
});
