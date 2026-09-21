import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/lib/api";
import type { Deployment } from "@/lib/backend_deployments";
import { useBackendDeployment } from "@/state/backend_deployment";

const getLatest = vi.fn();
const start = vi.fn();
const stop = vi.fn();
vi.mock("@/lib/backend_deployments", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/backend_deployments")>()),
  getLatestDeployment: (...args: unknown[]) => getLatest(...args),
  startDeployment: (...args: unknown[]) => start(...args),
  stopDeployment: (...args: unknown[]) => stop(...args),
}));

function dep(status: Deployment["status"]): Deployment {
  return {
    id: "d1",
    document_id: "doc-1",
    status,
    error: "",
    log_tail: "",
    public_path: "",
    public_url: null,
    openapi_url: null,
    docs_url: null,
    created_at: "2026-09-20T10:00:00Z",
    updated_at: "2026-09-20T10:00:00Z",
  };
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
}

describe("useBackendDeployment", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    getLatest.mockReset();
    start.mockReset();
    stop.mockReset();
  });
  afterEach(() => vi.useRealTimers());

  it("loads the latest deployment, polls every 3 s while building and stops once running", async () => {
    getLatest.mockResolvedValueOnce(dep("building")).mockResolvedValueOnce(dep("running"));
    const { result } = renderHook(() => useBackendDeployment("acme", "doc-1"));
    await flush();
    expect(result.current.deployment?.status).toBe("building");
    expect(getLatest).toHaveBeenCalledTimes(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000);
    });
    expect(result.current.deployment?.status).toBe("running");
    expect(getLatest).toHaveBeenCalledTimes(2);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(9000);
    });
    expect(getLatest).toHaveBeenCalledTimes(2);
  });

  it("does not poll when there is no deployment yet", async () => {
    getLatest.mockResolvedValue(null);
    const { result } = renderHook(() => useBackendDeployment("acme", "doc-1"));
    await flush();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(9000);
    });

    expect(result.current.deployment).toBeNull();
    expect(getLatest).toHaveBeenCalledTimes(1);
  });

  it("maps a quota_exceeded start failure to a friendly message", async () => {
    getLatest.mockResolvedValue(null);
    start.mockRejectedValue(new ApiError({ status: 409, code: "quota_exceeded", detail: "quota" }));
    const { result } = renderHook(() => useBackendDeployment("acme", "doc-1"));
    await flush();

    await act(async () => {
      await result.current.start();
    });

    expect(result.current.actionError).toMatch(/límite/i);
    expect(result.current.actionError).not.toContain("quota_exceeded");
    expect(result.current.deployment).toBeNull();
  });

  it("stops the current deployment", async () => {
    getLatest.mockResolvedValue(dep("running"));
    stop.mockResolvedValue(dep("stopped"));
    const { result } = renderHook(() => useBackendDeployment("acme", "doc-1"));
    await flush();

    await act(async () => {
      await result.current.stop();
    });

    expect(stop).toHaveBeenCalledWith("acme", "doc-1", "d1");
    expect(result.current.deployment?.status).toBe("stopped");
  });
});
