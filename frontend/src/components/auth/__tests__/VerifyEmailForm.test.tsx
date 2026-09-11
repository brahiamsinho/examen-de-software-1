import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { VerifyEmailForm } from "@/components/auth/VerifyEmailForm";
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
  return { ...actual, verifyEmail: vi.fn() };
});

function renderForm() {
  return render(
    <Provider>
      <VerifyEmailForm />
    </Provider>,
  );
}

describe("VerifyEmailForm", () => {
  beforeEach(() => {
    replace.mockReset();
    searchParamsValue = "";
    vi.mocked(authLib.verifyEmail).mockReset();
  });

  it("auto-submits the token from searchParams and redirects on success", async () => {
    searchParamsValue = "token=raw-token-value";
    vi.mocked(authLib.verifyEmail).mockResolvedValueOnce({ message: "ok" });

    renderForm();

    await waitFor(() => expect(authLib.verifyEmail).toHaveBeenCalledWith({ token: "raw-token-value" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });

  it("auto-submits exactly once even across re-renders", async () => {
    searchParamsValue = "token=raw-token-value";
    vi.mocked(authLib.verifyEmail).mockResolvedValueOnce({ message: "ok" });

    const { rerender } = renderForm();
    rerender(
      <Provider>
        <VerifyEmailForm />
      </Provider>,
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
    expect(authLib.verifyEmail).toHaveBeenCalledTimes(1);
  });

  it("shows the backend error detail on failure and does not redirect", async () => {
    searchParamsValue = "token=expired-token";
    vi.mocked(authLib.verifyEmail).mockRejectedValueOnce(
      new ApiError({ status: 400, code: "token_expired", detail: "This verification link has expired." }),
    );

    renderForm();

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This verification link has expired.",
    );
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows a manual paste-token field when no token param is present", () => {
    renderForm();

    expect(screen.getByLabelText(/token/i)).toBeInTheDocument();
    expect(authLib.verifyEmail).not.toHaveBeenCalled();
  });

  it("submits the manually pasted token", async () => {
    vi.mocked(authLib.verifyEmail).mockResolvedValueOnce({ message: "ok" });

    renderForm();
    fireEvent.change(screen.getByLabelText(/token/i), { target: { value: "pasted-token" } });
    fireEvent.click(screen.getByRole("button", { name: /verificar/i }));

    await waitFor(() => expect(authLib.verifyEmail).toHaveBeenCalledWith({ token: "pasted-token" }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/login"));
  });
});
