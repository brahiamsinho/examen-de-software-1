import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as logLib from "@/lib/session_log";
import { useSessionLog } from "@/state/session_log";

vi.mock("@/lib/session_log", async () => {
  const actual = await vi.importActual<typeof import("@/lib/session_log")>("@/lib/session_log");
  return { ...actual, listLog: vi.fn(), listLogSessions: vi.fn() };
});

const entries = [
  {
    id: "000000000000000000000001",
    session: 1,
    kind: "change",
    author: "Ana",
    author_id: "u1",
    is_ai: false,
    summary: "AddClass A",
    data: {},
    created_at: "2026-11-07T10:00:00+00:00",
  },
];
const sessions = [
  { session: 1, started_at: "2026-11-07T10:00:00+00:00", ended_at: "2026-11-07T10:05:00+00:00", entries: 1, actors: [] },
];

describe("state/session_log useSessionLog()", () => {
  beforeEach(() => {
    vi.mocked(logLib.listLog).mockReset();
    vi.mocked(logLib.listLog).mockResolvedValue(entries);
    vi.mocked(logLib.listLogSessions).mockReset();
    vi.mocked(logLib.listLogSessions).mockResolvedValue(sessions);
  });

  it("loads nothing while the dialog is closed", async () => {
    renderHook(() => useSessionLog("acme", "d1", false));

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(logLib.listLog).not.toHaveBeenCalled();
    expect(logLib.listLogSessions).not.toHaveBeenCalled();
  });

  it("loads the entries and the sessions when it opens, and says it is loading until then", async () => {
    const { result } = renderHook(() => useSessionLog("acme", "d1", true));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.entries).toEqual(entries);
    expect(result.current.sessions).toEqual(sessions);
    expect(logLib.listLog).toHaveBeenCalledWith("acme", "d1", {});
  });

  it("asks again, with the filter, when the filter changes", async () => {
    const { result } = renderHook(() => useSessionLog("acme", "d1", true));
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => result.current.setFilters({ session: 2, user: "ai" }));

    await waitFor(() => expect(logLib.listLog).toHaveBeenLastCalledWith("acme", "d1", { session: 2, user: "ai" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.filters).toEqual({ session: 2, user: "ai" });
  });

  it("loads again on demand", async () => {
    const { result } = renderHook(() => useSessionLog("acme", "d1", true));
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => result.current.reload());

    await waitFor(() => expect(logLib.listLog).toHaveBeenCalledTimes(2));
  });

  it("surfaces a failure instead of an empty log", async () => {
    vi.mocked(logLib.listLog).mockRejectedValue(new Error("boom"));
    const { result } = renderHook(() => useSessionLog("acme", "d1", true));

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.error).toMatch(/No se pudo cargar la bitácora/);
    expect(result.current.entries).toEqual([]);
  });

  it("does not load without an organization", async () => {
    renderHook(() => useSessionLog(null, "d1", true));

    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(logLib.listLog).not.toHaveBeenCalled();
  });
});
