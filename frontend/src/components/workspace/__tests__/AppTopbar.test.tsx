import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppTopbar } from "@/components/workspace/AppTopbar";
import * as authLib from "@/lib/auth";
import * as orgsLib from "@/lib/organizations";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("@/lib/auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth")>("@/lib/auth");
  return { ...actual, logout: vi.fn() };
});

vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn(), createOrganization: vi.fn() };
});

function renderTopbar() {
  return render(
    <Provider>
      <AppTopbar />
    </Provider>,
  );
}

describe("AppTopbar", () => {
  beforeEach(() => {
    replace.mockReset();
    vi.mocked(authLib.logout).mockReset();
    vi.mocked(orgsLib.listOrganizations).mockReset();
  });

  it("renders the organization switcher (completes 5.6/D4: only logout affordance)", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const },
    ]);

    renderTopbar();

    expect(await screen.findByRole("button", { name: /Acme/ })).toBeInTheDocument();
  });

  it("renders a Miembros link to /settings/members alongside logout", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);

    renderTopbar();

    const link = await screen.findByRole("link", { name: "Miembros" });
    expect(link).toHaveAttribute("href", "/settings/members");
    expect(screen.getByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
  });

  it("logging out calls logout() and redirects to /", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    vi.mocked(authLib.logout).mockResolvedValueOnce(undefined);

    renderTopbar();
    fireEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    await waitFor(() => expect(authLib.logout).toHaveBeenCalledOnce());
    expect(replace).toHaveBeenCalledWith("/");
  });
});
