import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Mocking pattern per design.md DD7. `vi.hoisted` holders let each case vary
 * inputs without re-mocking. The `redirect` mock throws `NEXT_REDIRECT:<url>`
 * to mirror Next's real behavior — a silent mock would let execution fall
 * through to `return user`, masking a mis-ordered guard.
 */
const nav = vi.hoisted(() => ({
  redirect: vi.fn((url: string) => {
    throw new Error(`NEXT_REDIRECT:${url}`);
  }),
}));
vi.mock("next/navigation", () => nav);

const jar = vi.hoisted(() => ({ value: "" }));
vi.mock("next/headers", () => ({ cookies: async () => ({ toString: () => jar.value }) }));

const env = vi.hoisted(() => ({
  apiUrl: "http://localhost:8000",
  internalApiUrl: "http://backend:8000",
}));
vi.mock("@/lib/env", () => env);

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("getServerUser", () => {
  beforeEach(() => {
    jar.value = "";
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    nav.redirect.mockClear();
  });

  it("forwards the whole cookie jar verbatim as the cookie header", async () => {
    jar.value = "sessionid=abc123; csrftoken=xyz";
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: "1", email: "a@b.com", full_name: "A" }));

    const { getServerUser } = await import("@/lib/server-session");
    await getServerUser();

    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(new Headers(init?.headers).get("cookie")).toBe("sessionid=abc123; csrftoken=xyz");
  });

  it("sends no cookie header when the jar is empty", async () => {
    jar.value = "";
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: "1", email: "a@b.com", full_name: "A" }));

    const { getServerUser } = await import("@/lib/server-session");
    await getServerUser();

    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(new Headers(init?.headers).has("cookie")).toBe(false);
  });

  it("always sends cache: no-store", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: "1", email: "a@b.com", full_name: "A" }));

    const { getServerUser } = await import("@/lib/server-session");
    await getServerUser();

    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(init?.cache).toBe("no-store");
  });

  it("targets internalApiUrl, not apiUrl", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: "1", email: "a@b.com", full_name: "A" }));

    const { getServerUser } = await import("@/lib/server-session");
    await getServerUser();

    const [url] = vi.mocked(fetch).mock.calls[0]!;
    expect(String(url)).toBe("http://backend:8000/api/auth/me");
  });

  it("returns the parsed User on 200", async () => {
    const user = { id: "1", email: "a@b.com", full_name: "A" };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(user));

    const { getServerUser } = await import("@/lib/server-session");
    await expect(getServerUser()).resolves.toEqual(user);
  });

  it("returns null on 401", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "unauthenticated" }, 401));

    const { getServerUser } = await import("@/lib/server-session");
    await expect(getServerUser()).resolves.toBeNull();
  });

  it("returns null on 403", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "forbidden" }, 403));

    const { getServerUser } = await import("@/lib/server-session");
    await expect(getServerUser()).resolves.toBeNull();
  });

  it("throws on 500", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "boom" }, 500));

    const { getServerUser } = await import("@/lib/server-session");
    await expect(getServerUser()).rejects.toThrow();
  });

  it("throws when fetch rejects (network error)", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const { getServerUser } = await import("@/lib/server-session");
    await expect(getServerUser()).rejects.toThrow();
  });
});

describe("requireUser", () => {
  beforeEach(() => {
    jar.value = "";
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    nav.redirect.mockClear();
  });

  it("returns the user on 200", async () => {
    const user = { id: "1", email: "a@b.com", full_name: "A" };
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(user));

    const { requireUser } = await import("@/lib/server-session");
    await expect(requireUser("/dashboard")).resolves.toEqual(user);
    expect(nav.redirect).not.toHaveBeenCalled();
  });

  it("redirects to /login?next=%2Fdashboard on 401", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "unauthenticated" }, 401));

    const { requireUser } = await import("@/lib/server-session");
    await expect(requireUser("/dashboard")).rejects.toThrow(
      "NEXT_REDIRECT:/login?next=%2Fdashboard",
    );
  });

  it("collapses a hostile nextPath (//evil.com) to %2Fdashboard via safe()", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ detail: "unauthenticated" }, 401));

    const { requireUser } = await import("@/lib/server-session");
    await expect(requireUser("//evil.com")).rejects.toThrow(
      "NEXT_REDIRECT:/login?next=%2Fdashboard",
    );
  });

  it("does not redirect and returns null when getServerUser throws", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const { requireUser } = await import("@/lib/server-session");
    await expect(requireUser("/dashboard")).resolves.toBeNull();
    expect(nav.redirect).not.toHaveBeenCalled();
  });
});
