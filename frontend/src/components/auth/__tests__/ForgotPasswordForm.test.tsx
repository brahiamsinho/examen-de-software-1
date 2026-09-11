import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";
import { ApiError } from "@/lib/api";
import * as authLib from "@/lib/auth";

vi.mock("@/lib/auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth")>("@/lib/auth");
  return { ...actual, requestPasswordReset: vi.fn() };
});

function submitEmail(email: string) {
  render(<ForgotPasswordForm />);
  fireEvent.change(screen.getByLabelText("Correo electrónico"), { target: { value: email } });
  fireEvent.click(screen.getByRole("button", { name: /enviar/i }));
}

describe("ForgotPasswordForm", () => {
  it("shows the generic confirmation when the backend reports success", async () => {
    vi.mocked(authLib.requestPasswordReset).mockResolvedValueOnce({ message: "anything" });

    submitEmail("exists@example.com");

    expect(
      await screen.findByText(/si esa cuenta existe|si la cuenta existe/i),
    ).toBeInTheDocument();
  });

  it("shows the identical generic confirmation even if the backend call rejects", async () => {
    vi.mocked(authLib.requestPasswordReset).mockRejectedValueOnce(
      new ApiError({ status: 500, code: "server_error", detail: "boom" }),
    );

    submitEmail("ghost@example.com");

    expect(
      await screen.findByText(/si esa cuenta existe|si la cuenta existe/i),
    ).toBeInTheDocument();
  });

  it("calls requestPasswordReset with the submitted email", async () => {
    vi.mocked(authLib.requestPasswordReset).mockResolvedValueOnce({ message: "a" });

    submitEmail("first@example.com");

    await waitFor(() =>
      expect(authLib.requestPasswordReset).toHaveBeenCalledWith({ email: "first@example.com" }),
    );
  });
});
