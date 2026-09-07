import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/auth/LoginForm";
import { ApiError } from "@/lib/api";
import * as authLib from "@/lib/auth";
import * as orgsLib from "@/lib/organizations";

const replace = vi.fn();
let searchParamsValue = "";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(searchParamsValue),
}));

vi.mock("@/lib/auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth")>("@/lib/auth");
  return { ...actual, login: vi.fn() };
});

vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn() };
});

function renderForm() {
  return render(
    <Provider>
      <LoginForm />
    </Provider>,
  );
}

describe("LoginForm", () => {
  beforeEach(() => {
    replace.mockReset();
    searchParamsValue = "";
    vi.mocked(authLib.login).mockReset();
    vi.mocked(orgsLib.listOrganizations).mockReset();
    window.localStorage.clear();
  });

  function loginAsUser() {
    const user = { id: "1", email: "a@b.com", full_name: "A" };
    vi.mocked(authLib.login).mockResolvedValueOnce(user);
    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "s3cret!" } });
    fireEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));
  }

  it("zero organizations: redirects to /dashboard with no next param", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);

    loginAsUser();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(authLib.login).toHaveBeenCalledWith({ email: "a@b.com", password: "s3cret!" });
  });

  it("exactly one organization: sets it active and redirects to /dashboard with no picker", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const },
    ]);

    loginAsUser();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(window.localStorage.getItem("modelia:active-org-slug")).toBe("acme");
  });

  it("two or more organizations: routes to the organization picker", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const },
      { id: "2", name: "Beta", slug: "beta", plan: "free", my_role: "EDITOR" as const },
    ]);

    loginAsUser();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/select-organization"));
  });

  it("redirects to the sanitized next path on success, without fetching organizations", async () => {
    searchParamsValue = "next=%2Fsettings";

    loginAsUser();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/settings"));
    expect(orgsLib.listOrganizations).not.toHaveBeenCalled();
  });

  it("a precedence-winning next beats org-count branching, even with 2+ organizations", async () => {
    searchParamsValue = "next=%2Fsettings";
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const },
      { id: "2", name: "Beta", slug: "beta", plan: "free", my_role: "EDITOR" as const },
    ]);

    loginAsUser();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/settings"));
  });

  it("falls back to /dashboard for an open-redirect next param", async () => {
    searchParamsValue = "next=" + encodeURIComponent("https://evil.com");
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);

    loginAsUser();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });

  it("org-fetch failure after successful login falls back to /dashboard without reusing the login error", async () => {
    vi.mocked(orgsLib.listOrganizations).mockRejectedValueOnce(new Error("network error"));

    loginAsUser();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows one generic inline error on invalid credentials, session stays anonymous, no redirect", async () => {
    vi.mocked(authLib.login).mockRejectedValueOnce(
      new ApiError({ status: 401, code: "invalid_credentials", detail: "Invalid credentials" }),
    );

    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(1));
    expect(replace).not.toHaveBeenCalled();
  });
});
