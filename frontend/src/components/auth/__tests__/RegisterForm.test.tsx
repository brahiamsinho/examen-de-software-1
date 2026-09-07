import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RegisterForm } from "@/components/auth/RegisterForm";
import { ApiError } from "@/lib/api";
import * as authLib from "@/lib/auth";
import * as orgsLib from "@/lib/organizations";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("@/lib/auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth")>("@/lib/auth");
  return { ...actual, register: vi.fn() };
});

vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn() };
});

function renderForm() {
  return render(
    <Provider>
      <RegisterForm />
    </Provider>,
  );
}

describe("RegisterForm", () => {
  beforeEach(() => {
    replace.mockReset();
    vi.mocked(authLib.register).mockReset();
    vi.mocked(orgsLib.listOrganizations).mockReset();
    window.localStorage.clear();
  });

  it("authenticates and redirects to /dashboard on successful registration", async () => {
    const user = { id: "1", email: "new@b.com", full_name: "New User" };
    vi.mocked(authLib.register).mockResolvedValueOnce(user);
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { id: "1", name: "New's Workspace", slug: "new-abc123", plan: "free", my_role: "OWNER" as const },
    ]);

    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "new@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "s3cret!" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrarse" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(authLib.register).toHaveBeenCalledWith(
      expect.objectContaining({ email: "new@b.com", password: "s3cret!" }),
    );
  });

  it("adopts the sole provisioned organization as active before redirect", async () => {
    const user = { id: "1", email: "new@b.com", full_name: "New User" };
    vi.mocked(authLib.register).mockResolvedValueOnce(user);
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { id: "1", name: "New's Workspace", slug: "new-abc123", plan: "free", my_role: "OWNER" as const },
    ]);

    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "new@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "s3cret!" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrarse" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(window.localStorage.getItem("modelia:active-org-slug")).toBe("new-abc123");
  });

  it("a post-register org-fetch failure still redirects to /dashboard, non-fatally", async () => {
    const user = { id: "1", email: "new@b.com", full_name: "New User" };
    vi.mocked(authLib.register).mockResolvedValueOnce(user);
    vi.mocked(orgsLib.listOrganizations).mockRejectedValueOnce(new Error("network error"));

    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "new@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "s3cret!" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrarse" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows the backend's detail inline on a duplicate email, session stays anonymous, no redirect", async () => {
    vi.mocked(authLib.register).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "duplicate_email", detail: "Ese correo ya está registrado." }),
    );

    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "dup@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "s3cret!" } });
    fireEvent.click(screen.getByRole("button", { name: "Registrarse" }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Ese correo ya está registrado."),
    );
    expect(replace).not.toHaveBeenCalled();
  });
});
