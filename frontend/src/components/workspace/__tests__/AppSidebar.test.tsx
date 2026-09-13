import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppSidebar } from "@/components/workspace/AppSidebar";
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

function renderSidebar() {
  return render(
    <Provider>
      <AppSidebar />
    </Provider>,
  );
}

describe("AppSidebar", () => {
  beforeEach(() => {
    replace.mockReset();
    vi.mocked(authLib.logout).mockReset();
    vi.mocked(orgsLib.listOrganizations).mockReset();
  });

  it("renders the organization switcher (only logout affordance stays reachable at the bottom)", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const },
    ]);

    renderSidebar();

    expect(await screen.findByRole("button", { name: /Acme/ })).toBeInTheDocument();
  });

  it("renders a Miembros link to /settings/members alongside logout", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);

    renderSidebar();

    const link = await screen.findByRole("link", { name: "Miembros" });
    expect(link).toHaveAttribute("href", "/settings/members");
    expect(screen.getByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
  });

  it("renders a Diagramas link back to /dashboard, reachable from any page under the sidebar", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);

    renderSidebar();

    const link = await screen.findByRole("link", { name: "Diagramas" });
    expect(link).toHaveAttribute("href", "/dashboard");
  });

  it("logging out calls logout() and redirects to /", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    vi.mocked(authLib.logout).mockResolvedValueOnce(undefined);

    renderSidebar();
    fireEvent.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    await waitFor(() => expect(authLib.logout).toHaveBeenCalledOnce());
    expect(replace).toHaveBeenCalledWith("/");
  });
});
