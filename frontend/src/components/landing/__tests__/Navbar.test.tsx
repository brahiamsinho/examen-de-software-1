import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Provider } from "jotai";

import { Navbar } from "@/components/landing/Navbar";
import * as sessionState from "@/state/session";

/**
 * `Navbar` now reads `useSession()` to switch its auth links (proposal Q3;
 * design.md "Read `sessionAtom` via `useSession()`/`useAtomValue` — landing
 * stays outside `(app)`, so this is the one place outside the guard that
 * reads session state"). `useSession` is mocked (same pattern as
 * `SessionGuard.test.tsx`) so each scenario is deterministic and no test
 * depends on a real `fetch`.
 */
vi.mock("@/state/session", async () => {
  const actual = await vi.importActual<typeof import("@/state/session")>("@/state/session");
  return { ...actual, useSession: vi.fn() };
});

function renderNavbar() {
  return render(
    <Provider>
      <Navbar />
    </Provider>,
  );
}

describe("Navbar", () => {
  beforeEach(() => {
    vi.mocked(sessionState.useSession).mockReset();
  });

  it("renders the brand and the primary CTA", () => {
    vi.mocked(sessionState.useSession).mockReturnValue({ status: "anonymous" });
    renderNavbar();

    expect(screen.getByText("Modelia")).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: "Empezar gratis" });
    expect(cta).toHaveAttribute("href", "#precios");
  });

  it("renders the section nav links", () => {
    vi.mocked(sessionState.useSession).mockReturnValue({ status: "anonymous" });
    renderNavbar();

    expect(screen.getByRole("link", { name: "Producto" })).toHaveAttribute("href", "#producto");
    expect(screen.getByRole("link", { name: "Organizaciones" })).toHaveAttribute(
      "href",
      "#organizaciones"
    );
    expect(screen.getByRole("link", { name: "Precios" })).toHaveAttribute("href", "#precios");
  });

  it("renders Iniciar sesión and Registrarse links when anonymous", () => {
    vi.mocked(sessionState.useSession).mockReturnValue({ status: "anonymous" });
    renderNavbar();

    expect(screen.getByRole("link", { name: "Iniciar sesión" })).toHaveAttribute("href", "/login");
    expect(screen.getByRole("link", { name: "Registrarse" })).toHaveAttribute("href", "/register");
    expect(screen.queryByRole("link", { name: "Ir al panel" })).not.toBeInTheDocument();
  });

  it("renders a link to /dashboard instead when authenticated", () => {
    vi.mocked(sessionState.useSession).mockReturnValue({
      status: "authenticated",
      user: { id: "1", email: "a@b.com", full_name: "A", is_verified: false },
    });
    renderNavbar();

    expect(screen.getByRole("link", { name: "Ir al panel" })).toHaveAttribute("href", "/dashboard");
    expect(screen.queryByRole("link", { name: "Iniciar sesión" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Registrarse" })).not.toBeInTheDocument();
  });
});
