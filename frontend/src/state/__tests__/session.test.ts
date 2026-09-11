import { renderHook, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, NetworkError } from "@/lib/api";
import * as authLib from "@/lib/auth";
import { useSession } from "@/state/session";

/**
 * `useSession()` owns the single `fetchMe()` call per shell mount
 * (design.md DD5). Each test renders inside a fresh `<Provider>` so the
 * module-level jotai store never leaks session state across test files.
 */
vi.mock("@/lib/auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth")>("@/lib/auth");
  return { ...actual, fetchMe: vi.fn() };
});

function wrapper({ children }: { children: ReactNode }) {
  return createElement(Provider, null, children);
}

const user = { id: "1", email: "a@b.com", full_name: "A B", is_verified: false };

describe("state/session useSession()", () => {
  beforeEach(() => {
    vi.mocked(authLib.fetchMe).mockReset();
  });

  it("starts loading, then fires fetchMe once and resolves to authenticated", async () => {
    vi.mocked(authLib.fetchMe).mockResolvedValueOnce(user);

    const { result } = renderHook(() => useSession(), { wrapper });

    expect(result.current).toEqual({ status: "loading" });

    await waitFor(() => expect(result.current.status).toBe("authenticated"));
    expect(result.current).toEqual({ status: "authenticated", user });
    expect(authLib.fetchMe).toHaveBeenCalledOnce();
  });

  it("maps a 401 ApiError to anonymous", async () => {
    vi.mocked(authLib.fetchMe).mockRejectedValueOnce(
      new ApiError({ status: 401, code: "http_401", detail: "Unauthorized" }),
    );

    const { result } = renderHook(() => useSession(), { wrapper });

    await waitFor(() => expect(result.current.status).toBe("anonymous"));
  });

  it("maps a NetworkError to error, not anonymous (an outage must not log the user out)", async () => {
    vi.mocked(authLib.fetchMe).mockRejectedValueOnce(new NetworkError());

    const { result } = renderHook(() => useSession(), { wrapper });

    await waitFor(() => expect(result.current.status).toBe("error"));
  });

  it("maps a non-401 ApiError to error", async () => {
    vi.mocked(authLib.fetchMe).mockRejectedValueOnce(
      new ApiError({ status: 500, code: "http_500", detail: "boom" }),
    );

    const { result } = renderHook(() => useSession(), { wrapper });

    await waitFor(() => expect(result.current.status).toBe("error"));
  });
});
