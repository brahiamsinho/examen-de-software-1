import { afterEach, describe, expect, it, vi } from "vitest";

/**
 * `internalApiUrl` (design.md DD5/DV3) is evaluated at import time, so each
 * case needs a fresh module instance via `vi.resetModules()` + dynamic
 * `import()` after stubbing the environment.
 */
describe("internalApiUrl", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("equals INTERNAL_API_URL when it is set", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    vi.stubEnv("INTERNAL_API_URL", "http://backend:8000");
    vi.resetModules();

    const { internalApiUrl } = await import("@/lib/env");

    expect(internalApiUrl).toBe("http://backend:8000");
  });

  it("falls back to apiUrl when INTERNAL_API_URL is unset", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000");
    vi.stubEnv("INTERNAL_API_URL", undefined);
    vi.resetModules();

    const { internalApiUrl, apiUrl } = await import("@/lib/env");

    expect(internalApiUrl).toBe(apiUrl);
    expect(internalApiUrl).toBe("http://localhost:8000");
  });
});
