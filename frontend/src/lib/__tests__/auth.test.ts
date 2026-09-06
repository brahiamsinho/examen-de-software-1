import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import { fetchMe, login, logout, register } from "@/lib/auth";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    apiFetch: vi.fn(),
    invalidateCsrfToken: vi.fn(),
  };
});

const user = { id: "11111111-1111-1111-1111-111111111111", email: "a@b.com", full_name: "A B" };

describe("lib/auth", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockReset();
    vi.mocked(api.invalidateCsrfToken).mockReset();
  });

  it("register posts to /api/auth/register and returns the created user", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(user);

    const result = await register({ email: "a@b.com", password: "s3cret!" });

    expect(api.apiFetch).toHaveBeenCalledWith(
      "/api/auth/register",
      expect.objectContaining({
        method: "POST",
        json: { email: "a@b.com", password: "s3cret!" },
      }),
    );
    expect(result).toEqual(user);
  });

  it("login posts to /api/auth/login and invalidates the CSRF token (Django rotates it)", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(user);

    const result = await login({ email: "a@b.com", password: "s3cret!" });

    expect(api.apiFetch).toHaveBeenCalledWith(
      "/api/auth/login",
      expect.objectContaining({
        method: "POST",
        json: { email: "a@b.com", password: "s3cret!" },
      }),
    );
    expect(api.invalidateCsrfToken).toHaveBeenCalledOnce();
    expect(result).toEqual(user);
  });

  it("logout posts to /api/auth/logout and invalidates the CSRF token (Django rotates it)", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(undefined);

    await logout();

    expect(api.apiFetch).toHaveBeenCalledWith(
      "/api/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
    expect(api.invalidateCsrfToken).toHaveBeenCalledOnce();
  });

  it("fetchMe gets /api/auth/me", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(user);

    const result = await fetchMe();

    expect(api.apiFetch).toHaveBeenCalledWith("/api/auth/me");
    expect(result).toEqual(user);
  });
});
