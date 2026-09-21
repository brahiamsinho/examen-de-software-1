import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as docsLib from "@/lib/uml_documents";
import * as xmiLib from "@/lib/xmi_interop";
import { useDocumentActions, useDocuments, useInvalidateDocuments } from "@/state/documents";

/**
 * `useDocuments` owns local `useState` + a render-time tracked-slug reset
 * (design.md DD5) plus a shared invalidation counter: the sidebar and the
 * dashboard both mount it, so a create/import elsewhere refetches every
 * instance (see `useInvalidateDocuments`/`useDocumentActions`).
 */
vi.mock("@/lib/uml_documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/uml_documents")>("@/lib/uml_documents");
  return { ...actual, listDocuments: vi.fn(), createDocument: vi.fn() };
});

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

vi.mock("@/lib/xmi_interop", async () => {
  const actual = await vi.importActual<typeof import("@/lib/xmi_interop")>("@/lib/xmi_interop");
  return { ...actual, importXmi: vi.fn(), stashImportWarnings: vi.fn() };
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

  // The sidebar and the dashboard both mount this hook; a mutation elsewhere
  // must refresh every instance, without flashing the loading state.
  it("invalidating refetches the list and keeps the current one on screen meanwhile", async () => {
    vi.mocked(docsLib.listDocuments).mockResolvedValueOnce([docA]);
    const { result } = renderHook(() => ({
      list: useDocuments("acme"),
      invalidate: useInvalidateDocuments(),
    }));
    await waitFor(() => expect(result.current.list.documents).toEqual([docA]));

    vi.mocked(docsLib.listDocuments).mockResolvedValueOnce([docA, docB]);
    act(() => result.current.invalidate());

    expect(result.current.list.loading).toBe(false);
    expect(result.current.list.documents).toEqual([docA]);
    await waitFor(() => expect(result.current.list.documents).toEqual([docA, docB]));
  });
});

describe("state/documents useDocumentActions()", () => {
  beforeEach(() => {
    push.mockReset();
    vi.mocked(docsLib.listDocuments).mockReset().mockResolvedValue([]);
    vi.mocked(docsLib.createDocument).mockReset();
    vi.mocked(xmiLib.importXmi).mockReset();
  });

  it("createDiagram creates, refreshes mounted lists and navigates to the new document", async () => {
    vi.mocked(docsLib.createDocument).mockResolvedValueOnce({ id: "doc-7" } as never);
    const { result } = renderHook(() => ({
      list: useDocuments("acme"),
      actions: useDocumentActions("acme"),
    }));
    await waitFor(() => expect(docsLib.listDocuments).toHaveBeenCalledTimes(1));

    await act(() => result.current.actions.createDiagram({ name: "Nuevo" }));

    expect(docsLib.createDocument).toHaveBeenCalledWith("acme", { name: "Nuevo" });
    expect(push).toHaveBeenCalledWith("/documents/doc-7");
    await waitFor(() => expect(docsLib.listDocuments).toHaveBeenCalledTimes(2));
  });

  it("createDiagram rethrows a failure without navigating", async () => {
    vi.mocked(docsLib.createDocument).mockRejectedValueOnce(new Error("403"));
    const { result } = renderHook(() => useDocumentActions("acme"));

    await expect(result.current.createDiagram({ name: "x" })).rejects.toThrow("403");
    expect(push).not.toHaveBeenCalled();
  });

  it("importDiagram stashes the warnings and navigates to the imported document", async () => {
    vi.mocked(xmiLib.importXmi).mockResolvedValueOnce({ id: "doc-8", warnings: ["w"] } as never);
    const { result } = renderHook(() => useDocumentActions("acme"));
    const file = new File(["<xmi/>"], "m.xml");

    await act(() => result.current.importDiagram(file));

    expect(xmiLib.importXmi).toHaveBeenCalledWith("acme", file);
    expect(xmiLib.stashImportWarnings).toHaveBeenCalledWith("doc-8", ["w"]);
    expect(push).toHaveBeenCalledWith("/documents/doc-8");
  });
});
