import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import * as docsLib from "@/lib/uml_documents";
import { useDocument } from "@/state/document";

/**
 * `useDocument` owns local `useState` (design.md DD2), not a shared atom:
 * exactly one consumer (the `[docId]` container) and it must reset per
 * document. Idle while `orgSlug` is null; `submitCommand` POSTs then awaits
 * a GET refetch (DD3) and stores both the fresh document and
 * `result.validation`; a rejected POST leaves `document` untouched and
 * rethrows.
 */
vi.mock("@/lib/uml_documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/uml_documents")>("@/lib/uml_documents");
  return {
    ...actual,
    getDocument: vi.fn(),
    createDocument: vi.fn(),
    submitCommand: vi.fn(),
  };
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

const documentB = { ...documentA, id: "doc-b", revision: 1 };

describe("state/document useDocument()", () => {
  beforeEach(() => {
    vi.mocked(docsLib.getDocument).mockReset();
    vi.mocked(docsLib.submitCommand).mockReset();
  });

  it("stays idle and does not fetch when orgSlug is null", () => {
    const { result } = renderHook(() => useDocument(null, "doc-a"));

    expect(result.current.document).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(docsLib.getDocument).not.toHaveBeenCalled();
  });

  it("loads the document on mount when orgSlug is provided", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);

    const { result } = renderHook(() => useDocument("acme", "doc-a"));

    await waitFor(() => expect(result.current.document).toEqual(documentA));
    expect(docsLib.getDocument).toHaveBeenCalledWith("acme", "doc-a");
  });

  it("resets document/loading/lastValidation when docId changes", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result, rerender } = renderHook(({ docId }) => useDocument("acme", docId), {
      initialProps: { docId: "doc-a" },
    });
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentB);
    rerender({ docId: "doc-b" });

    expect(result.current.document).toBeNull();
    expect(result.current.loading).toBe(true);
    expect(result.current.lastValidation).toBeNull();

    await waitFor(() => expect(result.current.document).toEqual(documentB));
    expect(docsLib.getDocument).toHaveBeenCalledWith("acme", "doc-b");
  });

  it("submitCommand calls POST then GET in that order and stores result.validation", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    const callOrder: string[] = [];
    vi.mocked(docsLib.submitCommand).mockImplementationOnce(async () => {
      callOrder.push("post");
      return { revision: 2, validation: { is_valid: true, violations: [] } };
    });
    const refetched = { ...documentA, revision: 2 };
    vi.mocked(docsLib.getDocument).mockImplementationOnce(async () => {
      callOrder.push("get");
      return refetched;
    });

    await act(async () => {
      await result.current.submitCommand({ type: "AddClass", class_id: "c1", name: "Cliente" });
    });

    expect(callOrder).toEqual(["post", "get"]);
    expect(result.current.document).toEqual(refetched);
    expect(result.current.lastValidation).toEqual({ is_valid: true, violations: [] });
  });

  it("a rejected POST leaves document untouched and rethrows", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    vi.mocked(docsLib.submitCommand).mockRejectedValueOnce(new Error("422"));

    await expect(
      act(async () => {
        await result.current.submitCommand({ type: "AddClass", class_id: "c1", name: "Cliente" });
      }),
    ).rejects.toThrow("422");

    expect(result.current.document).toEqual(documentA);
    expect(docsLib.getDocument).toHaveBeenCalledOnce();
  });

  it("stores a notFound error when the initial load rejects with a 404 ApiError", async () => {
    vi.mocked(docsLib.getDocument).mockRejectedValueOnce(
      new ApiError({ status: 404, code: "not_found", detail: "Not found" }),
    );

    const { result } = renderHook(() => useDocument("acme", "doc-a"));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toEqual({ message: "Not found", notFound: true });
  });

  it("stores a non-notFound error for a non-404 failure", async () => {
    vi.mocked(docsLib.getDocument).mockRejectedValueOnce(new Error("boom"));

    const { result } = renderHook(() => useDocument("acme", "doc-a"));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toEqual({ message: "boom", notFound: false });
  });

  it("rejects when submitCommand resolves with a malformed body and leaves document/lastValidation unchanged", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    // Malformed: missing `validation` entirely.
    vi.mocked(docsLib.submitCommand).mockResolvedValueOnce({ revision: 2 } as never);

    await expect(
      act(async () => {
        await result.current.submitCommand({ type: "AddClass", class_id: "c1", name: "Cliente" });
      }),
    ).rejects.toThrow();

    expect(result.current.document).toEqual(documentA);
    expect(result.current.lastValidation).toBeNull();
    expect(docsLib.getDocument).toHaveBeenCalledOnce();
  });

  it("still stores lastValidation when the post-command GET rejects after a successful POST", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    const validation = {
      is_valid: false,
      violations: [{ severity: "error" as const, code: "x", message: "m", path: "p" }],
    };
    vi.mocked(docsLib.submitCommand).mockResolvedValueOnce({ revision: 2, validation });
    vi.mocked(docsLib.getDocument).mockRejectedValueOnce(new Error("network blip"));

    // React's `act()` only flushes state updates scheduled before an
    // *awaited* callback resolves, not before it rejects — so the rejection
    // is caught inside the `act` scope to let the setLastValidation update
    // flush, and asserted separately.
    let caughtError: unknown;
    await act(async () => {
      try {
        await result.current.submitCommand({ type: "AddClass", class_id: "c1", name: "Cliente" });
      } catch (err) {
        caughtError = err;
      }
    });

    expect(caughtError).toBeInstanceOf(Error);
    expect(result.current.lastValidation).toEqual(validation);
    expect(result.current.document).toEqual(documentA);
  });

  it("isSubmitting is true while submitCommand is pending and false once it resolves (post-verify WARNING 3 on uml-canvas-remove-ui)", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    expect(result.current.isSubmitting).toBe(false);

    let resolvePost!: (value: Awaited<ReturnType<typeof docsLib.submitCommand>>) => void;
    const postPromise = new Promise<Awaited<ReturnType<typeof docsLib.submitCommand>>>((resolve) => {
      resolvePost = resolve;
    });
    vi.mocked(docsLib.submitCommand).mockReturnValueOnce(postPromise);
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce({ ...documentA, revision: 2 });

    let submitPromise!: ReturnType<typeof result.current.submitCommand>;
    act(() => {
      submitPromise = result.current.submitCommand({ type: "AddClass", class_id: "c1", name: "Cliente" });
    });

    await waitFor(() => expect(result.current.isSubmitting).toBe(true));

    await act(async () => {
      resolvePost({ revision: 2, validation: { is_valid: true, violations: [] } });
      await submitPromise;
    });

    expect(result.current.isSubmitting).toBe(false);
  });

  it("isSubmitting is true while submitCommand is pending and false once it rejects (post-verify WARNING 3 on uml-canvas-remove-ui)", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    let rejectPost!: (reason: unknown) => void;
    const postPromise = new Promise<Awaited<ReturnType<typeof docsLib.submitCommand>>>((_, reject) => {
      rejectPost = reject;
    });
    vi.mocked(docsLib.submitCommand).mockReturnValueOnce(postPromise);

    let submitError: unknown;
    let settled = false;
    act(() => {
      result.current.submitCommand({ type: "AddClass", class_id: "c1", name: "Cliente" }).catch((err) => {
        submitError = err;
      }).finally(() => {
        settled = true;
      });
    });

    await waitFor(() => expect(result.current.isSubmitting).toBe(true));

    await act(async () => {
      rejectPost(new Error("500"));
      await waitFor(() => expect(settled).toBe(true));
    });

    expect(submitError).toBeInstanceOf(Error);
    expect(result.current.isSubmitting).toBe(false);
  });
});
