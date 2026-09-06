import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginForm } from "@/components/auth/LoginForm";
import { ApiError } from "@/lib/api";
import * as authLib from "@/lib/auth";

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
  });

  it("authenticates and redirects to /dashboard on successful login with no next param", async () => {
    const user = { id: "1", email: "a@b.com", full_name: "A" };
    vi.mocked(authLib.login).mockResolvedValueOnce(user);

    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "s3cret!" } });
    fireEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(authLib.login).toHaveBeenCalledWith({ email: "a@b.com", password: "s3cret!" });
  });

  it("redirects to the sanitized next path on success", async () => {
    searchParamsValue = "next=%2Fsettings";
    const user = { id: "1", email: "a@b.com", full_name: "A" };
    vi.mocked(authLib.login).mockResolvedValueOnce(user);

    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "s3cret!" } });
    fireEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/settings"));
  });

  it("falls back to /dashboard for an open-redirect next param", async () => {
    searchParamsValue = "next=" + encodeURIComponent("https://evil.com");
    const user = { id: "1", email: "a@b.com", full_name: "A" };
    vi.mocked(authLib.login).mockResolvedValueOnce(user);

    renderForm();
    fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: "a@b.com" } });
    fireEvent.change(screen.getByLabelText("Contraseña"), { target: { value: "s3cret!" } });
    fireEvent.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
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
