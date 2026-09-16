import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
    openDocumentSocket: vi.fn(() => ({
      close: vi.fn(),
      sendClaim: vi.fn(),
      sendPosition: vi.fn(),
      sendRelease: vi.fn(),
    })),
  };
});

/** Returns the `handlers` object passed to the most recent `openDocumentSocket` call. */
function lastSocketHandlers() {
  const calls = vi.mocked(docsLib.openDocumentSocket).mock.calls;
  return calls[calls.length - 1]![2];
}

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

/**
 * The realtime socket effect (design.md DD11/DD13): opens on
 * `[orgSlug, docId]`, merges every incoming/refetched document
 * monotonically by revision, refetches once on every successful open
 * (including the first), reconnects with capped exponential backoff on a
 * non-terminal close, and never reconnects after 4401/4403/4404.
 */
describe("state/document useDocument() — realtime socket", () => {
  beforeEach(() => {
    vi.mocked(docsLib.getDocument).mockReset();
    vi.mocked(docsLib.openDocumentSocket).mockReset();
    vi.mocked(docsLib.openDocumentSocket).mockImplementation(() => ({ close: vi.fn() }) as never);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("opens a socket keyed on the current orgSlug/docId", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    renderHook(() => useDocument("acme", "doc-a"));

    await waitFor(() =>
      expect(docsLib.openDocumentSocket).toHaveBeenCalledWith("acme", "doc-a", expect.any(Object)),
    );
  });

  it("mergeRemote: a lower/equal incoming revision keeps the exact same object identity", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    const before = result.current.document;
    const handlers = lastSocketHandlers();

    act(() => {
      handlers.onMessage({ ...documentA, revision: documentA.revision });
    });

    expect(result.current.document).toBe(before);
  });

  it("mergeRemote: a higher incoming revision replaces the document", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    const handlers = lastSocketHandlers();
    const incoming = { ...documentA, revision: documentA.revision + 1 };

    act(() => {
      handlers.onMessage(incoming);
    });

    expect(result.current.document).toEqual(incoming);
  });

  it("every successful open — including the first — triggers exactly one getDocument() call, merged monotonically", async () => {
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    const refetched = { ...documentA, revision: documentA.revision + 1 };
    vi.mocked(docsLib.getDocument).mockClear();
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(refetched);

    const handlers = lastSocketHandlers();
    await act(async () => {
      handlers.onOpen?.();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(docsLib.getDocument).toHaveBeenCalledTimes(1);
    expect(result.current.document).toEqual(refetched);
  });

  it.each([4401, 4403, 4404])("close code %d schedules no reconnect", async (code) => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    renderHook(() => useDocument("acme", "doc-a"));
    await vi.waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    const handlers = lastSocketHandlers();
    act(() => handlers.onClose({ code }));
    act(() => vi.advanceTimersByTime(20_000));

    expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1);
  });

  it("a non-terminal close reconnects with capped exponential backoff (1s, 2s, 4s, 8s, 10s)", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(docsLib.getDocument).mockResolvedValue(documentA);
    renderHook(() => useDocument("acme", "doc-a"));
    await vi.waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    const closeAndExpectDelay = (delayMs: number, expectedCallsAfter: number) => {
      act(() => lastSocketHandlers().onClose({ code: 1006 }));
      act(() => vi.advanceTimersByTime(delayMs - 1));
      expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(expectedCallsAfter - 1);
      act(() => vi.advanceTimersByTime(1));
      expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(expectedCallsAfter);
    };

    closeAndExpectDelay(1_000, 2);
    closeAndExpectDelay(2_000, 3);
    closeAndExpectDelay(4_000, 4);
    closeAndExpectDelay(8_000, 5);
    closeAndExpectDelay(10_000, 6);
    // Stays capped at 10s, does not keep growing.
    closeAndExpectDelay(10_000, 7);
  });

  it("unmount closes the socket and clears the pending reconnect timer", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);
    const { unmount } = renderHook(() => useDocument("acme", "doc-a"));
    await vi.waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    const socketResult = vi.mocked(docsLib.openDocumentSocket).mock.results[0]!;
    const socket = socketResult.value as { close: ReturnType<typeof vi.fn> };

    act(() => lastSocketHandlers().onClose({ code: 1006 }));
    unmount();

    expect(socket.close).toHaveBeenCalledOnce();

    act(() => vi.advanceTimersByTime(20_000));
    expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1);
  });
});

/**
 * Node lock state + live position wiring (design.md DD4, DD9, DD11).
 * `locks` is plain `useState` (low-frequency, belongs in render); live
 * position frames bypass React entirely via `positionListenerRef`, and
 * `sendPosition` is throttled to at most one frame per 50ms window while
 * always flushing the final coalesced position (never silently dropping
 * the last frame before `release`).
 */
describe("state/document useDocument() — locks and live position (DD4/DD9/DD11)", () => {
  function mockConnection() {
    return {
      close: vi.fn(),
      sendClaim: vi.fn(),
      sendPosition: vi.fn(),
      sendRelease: vi.fn(),
    };
  }

  beforeEach(() => {
    vi.mocked(docsLib.getDocument).mockReset();
    vi.mocked(docsLib.openDocumentSocket).mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("node.locked/node.unlocked update locks state, keyed by class id", async () => {
    const connection = mockConnection();
    vi.mocked(docsLib.openDocumentSocket).mockImplementation(() => connection as never);
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);

    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));
    const handlers = lastSocketHandlers();

    act(() => {
      handlers.onNodeLocked?.({ type: "node.locked", class_id: "c1", owner_label: "Ana", mine: false });
    });
    expect(result.current.locks).toEqual({ c1: { ownerLabel: "Ana", mine: false } });

    act(() => {
      handlers.onNodeUnlocked?.({ type: "node.unlocked", class_id: "c1" });
    });
    expect(result.current.locks).toEqual({});
  });

  it("node.locks replaces the entire locks snapshot on join", async () => {
    const connection = mockConnection();
    vi.mocked(docsLib.openDocumentSocket).mockImplementation(() => connection as never);
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);

    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));
    const handlers = lastSocketHandlers();

    act(() => {
      handlers.onNodeLocks?.({
        type: "node.locks",
        locks: [{ class_id: "c1", owner_label: "Ana", mine: false }],
      });
    });

    expect(result.current.locks).toEqual({ c1: { ownerLabel: "Ana", mine: false } });
  });

  it("node.position for a foreign node calls positionListenerRef.current with (classId, x, y)", async () => {
    const connection = mockConnection();
    vi.mocked(docsLib.openDocumentSocket).mockImplementation(() => connection as never);
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);

    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));
    const handlers = lastSocketHandlers();

    const listener = vi.fn();
    result.current.positionListenerRef.current = listener;

    act(() => {
      handlers.onNodePosition?.({ type: "node.position", class_id: "c1", x: 5, y: 6, mine: false });
    });

    expect(listener).toHaveBeenCalledWith("c1", 5, 6);
  });

  it("sendClaim/sendRelease pass straight through to the socket connection", async () => {
    const connection = mockConnection();
    vi.mocked(docsLib.openDocumentSocket).mockImplementation(() => connection as never);
    vi.mocked(docsLib.getDocument).mockResolvedValueOnce(documentA);

    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await waitFor(() => expect(result.current.document).toEqual(documentA));

    act(() => {
      result.current.sendClaim("c1");
      result.current.sendRelease("c1", 9, 9);
    });

    expect(connection.sendClaim).toHaveBeenCalledWith("c1");
    expect(connection.sendRelease).toHaveBeenCalledWith("c1", 9, 9);
  });

  it("sendPosition emits at most one frame per 50ms window and always flushes the final coalesced position", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const connection = mockConnection();
    vi.mocked(docsLib.openDocumentSocket).mockImplementation(() => connection as never);
    vi.mocked(docsLib.getDocument).mockResolvedValue(documentA);

    const { result } = renderHook(() => useDocument("acme", "doc-a"));
    await vi.waitFor(() => expect(docsLib.openDocumentSocket).toHaveBeenCalledTimes(1));

    act(() => {
      result.current.sendPosition("c1", 1, 1);
    });
    // Leading edge: the first call in a window fires immediately.
    expect(connection.sendPosition).toHaveBeenCalledTimes(1);
    expect(connection.sendPosition).toHaveBeenLastCalledWith("c1", 1, 1);

    act(() => {
      result.current.sendPosition("c1", 2, 2);
      result.current.sendPosition("c1", 3, 3);
    });
    // Coalesced — still only the leading call so far.
    expect(connection.sendPosition).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(50);
    });
    // Trailing edge flushes exactly the LAST coalesced position.
    expect(connection.sendPosition).toHaveBeenCalledTimes(2);
    expect(connection.sendPosition).toHaveBeenLastCalledWith("c1", 3, 3);
  });
});
