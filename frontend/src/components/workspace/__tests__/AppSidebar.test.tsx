import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createStore, Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppSidebar } from "@/components/workspace/AppSidebar";
import * as authLib from "@/lib/auth";
import * as orgsLib from "@/lib/organizations";
import * as docsLib from "@/lib/uml_documents";
import { sessionAtom } from "@/state/session";

const replace = vi.fn();
const push = vi.fn();
let pathname = "/dashboard";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push }),
  usePathname: () => pathname,
}));

vi.mock("@/lib/auth", async () => {
  const actual = await vi.importActual<typeof import("@/lib/auth")>("@/lib/auth");
  return { ...actual, logout: vi.fn() };
});

vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn(), createOrganization: vi.fn() };
});

vi.mock("@/lib/uml_documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/uml_documents")>("@/lib/uml_documents");
  return { ...actual, listDocuments: vi.fn(), createDocument: vi.fn() };
});

const acme = { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const };

function renderSidebar() {
  const store = createStore();
  store.set(sessionAtom, {
    status: "authenticated",
    user: { id: "u1", email: "ana@acme.test", full_name: "Ana Pérez", is_verified: true },
  });
  return render(
    <Provider store={store}>
      <AppSidebar />
    </Provider>,
  );
}

describe("AppSidebar", () => {
  beforeEach(() => {
    replace.mockReset();
    push.mockReset();
    pathname = "/dashboard";
    vi.mocked(authLib.logout).mockReset();
    vi.mocked(orgsLib.listOrganizations).mockReset();
    vi.mocked(docsLib.listDocuments).mockReset().mockResolvedValue([]);
    vi.mocked(docsLib.createDocument).mockReset();
  });

  it("renders the organization switcher at the top with the active organization", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme]);

    renderSidebar();

    const trigger = await screen.findByRole("button", { name: /Acme/ });
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
  });

  it("no longer renders an inline organization list or creation form", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme]);

    renderSidebar();
    await screen.findByRole("button", { name: /Acme/ });

    expect(screen.queryByRole("list", { name: "Organizaciones" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Nombre de la organización")).not.toBeInTheDocument();
  });

  it("lists the current organization's diagrams, highlighting the open one", async () => {
    pathname = "/documents/doc-2";
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme]);
    vi.mocked(docsLib.listDocuments).mockReset().mockResolvedValue([
      { id: "doc-1", name: "Ventas", revision: 1, updated_at: "2026-09-12T10:05:00Z" },
      { id: "doc-2", name: "", revision: 2, updated_at: "2026-09-12T10:06:00Z" },
    ]);

    renderSidebar();

    expect(await screen.findByRole("link", { name: "Ventas" })).toHaveAttribute(
      "href",
      "/documents/doc-1",
    );
    expect(screen.getByRole("link", { name: "Sin título" })).toHaveAttribute("aria-current", "page");
    expect(docsLib.listDocuments).toHaveBeenCalledWith("acme");
  });

  it('"+" opens the new-diagram dialog; submitting creates it and opens it', async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme]);
    vi.mocked(docsLib.createDocument).mockResolvedValueOnce({
      id: "doc-9",
      owner_id: "1",
      revision: 0,
      metadata: { name: "Compras", description: "" },
      model: { classes: [], enumerations: [], relationships: [], generation_metadata: {} },
      layout: { positions: {} },
      created_at: "2026-09-12T10:00:00Z",
      updated_at: "2026-09-12T10:00:00Z",
    });

    renderSidebar();
    fireEvent.click(await screen.findByRole("button", { name: "Nuevo diagrama" }));

    fireEvent.change(await screen.findByLabelText("Nombre del diagrama"), {
      target: { value: "Compras" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Crear diagrama" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/documents/doc-9"));
    expect(docsLib.createDocument).toHaveBeenCalledWith("acme", { name: "Compras" });
    // The shared invalidation counter makes the sidebar list refetch.
    await waitFor(() => expect(docsLib.listDocuments).toHaveBeenCalledTimes(2));
  });

  it('hides the "+" for a VIEWER, who cannot create diagrams', async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { ...acme, my_role: "VIEWER" as const },
    ]);

    renderSidebar();
    await screen.findByRole("button", { name: /Acme/ });

    expect(screen.queryByRole("button", { name: "Nuevo diagrama" })).not.toBeInTheDocument();
  });

  it("renders a Miembros link to /settings/members alongside logout and the signed-in user", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);

    renderSidebar();

    const link = await screen.findByRole("link", { name: "Miembros" });
    expect(link).toHaveAttribute("href", "/settings/members");
    expect(screen.getByRole("button", { name: "Cerrar sesión" })).toBeInTheDocument();
    expect(screen.getByText("Ana Pérez")).toBeInTheDocument();
  });

  it("renders a Diagramas header link back to /dashboard", async () => {
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
