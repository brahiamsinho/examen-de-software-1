import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiFetch, invalidateCsrfToken } from "@/lib/api";

function setCsrfCookie(value: string) {
  document.cookie = `csrftoken=${value}; path=/`;
}

function clearCsrfCookie() {
  document.cookie = "csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/";
}

function jsonResponse(body: unknown, init: ResponseInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
    ...init,
  });
}

function errorResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("apiFetch", () => {
  beforeEach(() => {
    clearCsrfCookie();
    invalidateCsrfToken();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("includes credentials on every request", async () => {
    setCsrfCookie("token-abc");
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));

    await apiFetch("/api/orgs");

    expect(fetch).toHaveBeenCalledWith(
      expect.any(URL),
      expect.objectContaining({ credentials: "include" }),
    );
  });

  it("primes CSRF via GET /api/auth/csrf before an unsafe request when no cookie is present", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "primed-token" }))
      .mockResolvedValueOnce(jsonResponse({ id: 1 }));

    await apiFetch("/api/orgs", { method: "POST", body: "{}" });

    expect(fetch).toHaveBeenCalledTimes(2);
    const [firstUrl] = vi.mocked(fetch).mock.calls[0]!;
    expect(String(firstUrl)).toContain("/api/auth/csrf");
    const [secondUrl] = vi.mocked(fetch).mock.calls[1]!;
    expect(String(secondUrl)).toContain("/api/orgs");
  });

  it("skips CSRF priming when the csrftoken cookie already exists", async () => {
    setCsrfCookie("existing-token");
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 1 }));

    await apiFetch("/api/orgs", { method: "POST", body: "{}" });

    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("attaches X-CSRFToken on unsafe methods and omits it on GET", async () => {
    setCsrfCookie("token-xyz");
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 1 }));

    await apiFetch("/api/orgs", { method: "POST", body: "{}" });
    const [, postInit] = vi.mocked(fetch).mock.calls[0]!;
    expect(new Headers(postInit?.headers).get("X-CSRFToken")).toBe("token-xyz");

    vi.mocked(fetch).mockClear();
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 1 }));
    await apiFetch("/api/orgs");
    const [, getInit] = vi.mocked(fetch).mock.calls[0]!;
    expect(new Headers(getInit?.headers).has("X-CSRFToken")).toBe(false);
  });

  it("re-primes and retries exactly once after a 403 CSRF failure, then surfaces ApiError", async () => {
    setCsrfCookie("stale-token");
    vi.mocked(fetch)
      .mockResolvedValueOnce(errorResponse(403, { code: "csrf_failed", detail: "CSRF Failed" }))
      .mockResolvedValueOnce(jsonResponse({ csrf_token: "fresh-token" }))
      .mockResolvedValueOnce(errorResponse(403, { code: "csrf_failed", detail: "CSRF Failed" }));

    await expect(
      apiFetch("/api/orgs", { method: "POST", body: "{}" }),
    ).rejects.toMatchObject({ status: 403, code: "csrf_failed" });

    expect(fetch).toHaveBeenCalledTimes(3);
    const [, retryInit] = vi.mocked(fetch).mock.calls[2]!;
    expect(new Headers(retryInit?.headers).get("X-CSRFToken")).toBe("fresh-token");
  });

  it("normalizes a non-2xx response with no code into ApiError with an http_<status> code", async () => {
    setCsrfCookie("token-abc");
    vi.mocked(fetch).mockResolvedValueOnce(
      errorResponse(401, { detail: "Authentication credentials were not provided." }),
    );

    await expect(apiFetch("/api/auth/me")).rejects.toMatchObject({
      status: 401,
      code: "http_401",
      detail: "Authentication credentials were not provided.",
    });
  });

  it("coerces a non-string (array) detail via JSON.stringify", async () => {
    setCsrfCookie("token-abc");
    const arrayDetail = [{ loc: ["body", "email"], msg: "field required", type: "missing" }];
    vi.mocked(fetch).mockResolvedValueOnce(errorResponse(422, { detail: arrayDetail }));

    await expect(apiFetch("/api/auth/register", { method: "POST", body: "{}" })).rejects.toMatchObject({
      status: 422,
      code: "http_422",
      detail: JSON.stringify(arrayDetail),
    });
  });

  it("surfaces a fetch rejection as NetworkError, distinct from ApiError", async () => {
    setCsrfCookie("token-abc");
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const rejection = apiFetch("/api/orgs");
    await expect(rejection).rejects.toThrow();
    await expect(rejection).rejects.not.toMatchObject({ status: expect.anything() });
    await expect(rejection).rejects.toMatchObject({ name: "NetworkError" });
  });

  it("resolves a 204 response to undefined", async () => {
    setCsrfCookie("token-abc");
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(apiFetch("/api/auth/logout", { method: "POST" })).resolves.toBeUndefined();
  });

  it("serializes the `json` convenience field and sets Content-Type", async () => {
    setCsrfCookie("token-abc");
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: 1 }));

    await apiFetch("/api/auth/register", { method: "POST", json: { email: "a@b.com" } });

    const [, init] = vi.mocked(fetch).mock.calls[0]!;
    expect(init?.body).toBe(JSON.stringify({ email: "a@b.com" }));
    expect(new Headers(init?.headers).get("Content-Type")).toBe("application/json");
  });
});
