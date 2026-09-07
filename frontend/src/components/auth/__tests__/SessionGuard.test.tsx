import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SessionGuard } from "@/components/auth/SessionGuard";
import * as sessionState from "@/state/session";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
  usePathname: () => "/dashboard",
}));

vi.mock("@/state/session", async () => {
  const actual = await vi.importActual<typeof import("@/state/session")>("@/state/session");
  return { ...actual, useSession: vi.fn() };
});

describe("SessionGuard", () => {
  beforeEach(() => {
    replace.mockReset();
    vi.mocked(sessionState.useSession).mockReset();
  });

  it("renders a skeleton and no protected children while loading", () => {
    vi.mocked(sessionState.useSession).mockReturnValue({ status: "loading" });

    render(
      <SessionGuard>
        <div>protected</div>
      </SessionGuard>,
    );

    expect(screen.queryByText("protected")).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("redirects to /login?next=<path> and renders nothing else when anonymous", () => {
    vi.mocked(sessionState.useSession).mockReturnValue({ status: "anonymous" });

    const { container } = render(
      <SessionGuard>
        <div>protected</div>
      </SessionGuard>,
    );

    expect(replace).toHaveBeenCalledWith("/login?next=%2Fdashboard");
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it("renders a retry panel and does not redirect on error", () => {
    vi.mocked(sessionState.useSession).mockReturnValue({ status: "error", message: "boom" });

    render(
      <SessionGuard>
        <div>protected</div>
      </SessionGuard>,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.queryByText("protected")).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders children when authenticated", () => {
    vi.mocked(sessionState.useSession).mockReturnValue({
      status: "authenticated",
      user: { id: "1", email: "a@b.com", full_name: "A" },
    });

    render(
      <SessionGuard>
        <div>protected</div>
      </SessionGuard>,
    );

    expect(screen.getByText("protected")).toBeInTheDocument();
  });
});
