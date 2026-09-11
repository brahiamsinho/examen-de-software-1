import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";
import { ApiError } from "@/lib/api";
import * as authLib from "@/lib/auth";

const replace = vi.fn();
let searchParamsValue = "token=raw-reset-token";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  useSearchParams: () => new URLSearchParams(searchParamsValue),
}));

vi.mock("@/lib/auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth")>("@/lib/auth");
  return { ...actual, confirmPasswordReset: vi.fn() };
});

describe("ResetPasswordForm", () => {
  beforeEach(() => {
    replace.mockReset();
    searchParamsValue = "token=raw-reset-token";
    vi.mocked(authLib.confirmPasswordReset).mockReset();
  });

  it("submits the token from searchParams with the new password and redirects on success", async () => {
    vi.mocked(authLib.confirmPasswordReset).mockResolvedValueOnce({ message: "ok" });

    render(<ResetPasswordForm />);
    fireEvent.change(screen.getByLabelText("Nueva contraseña"), {
      target: { value: "brand-new-strong-1" },
    });
    fireEvent.click(screen.getByRole("button", { name: /restablecer/i }));

    await waitFor(() =>
      expect(authLib.confirmPasswordReset).toHaveBeenCalledWith({
        token: "raw-reset-token",
        password: "brand-new-strong-1",
      }),
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("shows the backend error detail inline on failure, no redirect", async () => {
    vi.mocked(authLib.confirmPasswordReset).mockRejectedValueOnce(
      new ApiError({ status: 400, code: "password_invalid", detail: "This password is too common." }),
    );

    render(<ResetPasswordForm />);
    fireEvent.change(screen.getByLabelText("Nueva contraseña"), { target: { value: "weak" } });
    fireEvent.click(screen.getByRole("button", { name: /restablecer/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("This password is too common.");
    expect(replace).not.toHaveBeenCalled();
  });
});
