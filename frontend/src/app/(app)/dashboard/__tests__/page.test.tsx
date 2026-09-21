import { fireEvent, render, screen } from "@testing-library/react";
import { createStore, Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/(app)/dashboard/page";
import * as orgsLib from "@/lib/organizations";
import * as docsLib from "@/lib/uml_documents";
import { sessionAtom } from "@/state/session";

/**
 * Container: the dashboard shows diagrams and their actions only —
 * organization administration lives in the sidebar's `OrgSwitcher`, so the
 * only place this page can create an organization is the zero-organization
 * empty state (through a dialog, never an inline form). Diagram creation
 * goes through `useDocumentActions` (`createDocument` then `router.push`).
 */
vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn(), createOrganization: vi.fn() };
});

vi.mock("@/lib/uml_documents", async () => {
  const actual = await vi.importActual<typeof import("@/lib/uml_documents")>("@/lib/uml_documents");
  return { ...actual, createDocument: vi.fn(), listDocuments: vi.fn() };
});

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: mockPush }) }));

const acme = (my_role: "OWNER" | "EDITOR" | "VIEWER" = "OWNER") => ({
  id: "1",
  name: "Acme",
  slug: "acme",
  plan: "team",
  my_role,
});

function renderPage() {
  return render(
    <Provider>
      <DashboardPage />
    </Provider>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.mocked(orgsLib.listOrganizations).mockReset();
    vi.mocked(orgsLib.createOrganization).mockReset();
    vi.mocked(docsLib.createDocument).mockReset();
    vi.mocked(docsLib.listDocuments).mockReset().mockResolvedValue([]);
    mockPush.mockReset();
  });

  // Precondition-agnostic by design (web-organization-workspace § Zero-Organization Empty
  // State): the frontend cannot distinguish a legacy account from one whose sole org was
  // deleted — both just render `organizations.length === 0`.
  it("renders the zero-organization empty state and calls no document request", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Crea tu primera organización" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear organización" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Nombre de la organización")).not.toBeInTheDocument();
    expect(docsLib.listDocuments).not.toHaveBeenCalled();
  });

  it("creating the first organization from the empty-state dialog shows it as active without a refetch", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    const gamma = { id: "3", name: "Gamma", slug: "gamma", plan: "free", my_role: "OWNER" as const };
    vi.mocked(orgsLib.createOrganization).mockResolvedValueOnce(gamma);

    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Crear organización" }));

    fireEvent.change(await screen.findByLabelText("Nombre de la organización"), {
      target: { value: "Gamma" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Crear organización" }).at(-1)!);

    expect(await screen.findByRole("heading", { name: "Gamma" })).toBeInTheDocument();
    expect(orgsLib.listOrganizations).toHaveBeenCalledOnce();
  });

  it("shows the org name as title with plan and role, and no organization admin content", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme()]);
    renderPage();

    expect(await screen.findByRole("heading", { level: 1, name: "Acme" })).toBeInTheDocument();
    expect(screen.getByText("Plan TEAM")).toBeInTheDocument();
    expect(screen.getByText("Propietario")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Crear organización" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Nombre de la organización")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Identificador (slug)")).not.toBeInTheDocument();
  });

  // web-account-recovery § "Dismissible Verify-Email Banner on Dashboard".
  it("shows the verify-email banner for an unverified authenticated user", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    const store = createStore();
    store.set(sessionAtom, {
      status: "authenticated",
      user: { id: "1", email: "a@b.com", full_name: "A", is_verified: false },
    });

    render(
      <Provider store={store}>
        <DashboardPage />
      </Provider>,
    );

    expect(await screen.findByRole("region")).toBeInTheDocument();
  });

  it("does not show the verify-email banner for a verified user", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    const store = createStore();
    store.set(sessionAtom, {
      status: "authenticated",
      user: { id: "1", email: "a@b.com", full_name: "A", is_verified: true },
    });

    render(
      <Provider store={store}>
        <DashboardPage />
      </Provider>,
    );

    await screen.findByRole("heading", { name: "Crea tu primera organización" });
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });

  it('hides "Nuevo diagrama" and "Importar XML" with no organization', async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    renderPage();

    await screen.findByRole("heading", { name: "Crea tu primera organización" });
    expect(screen.queryByRole("button", { name: "Nuevo diagrama" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Importar XML/ })).not.toBeInTheDocument();
  });

  it('"Nuevo diagrama" opens a dialog; submitting calls createDocument and navigates to the new page', async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme()]);
    vi.mocked(docsLib.listDocuments)
      .mockReset()
      .mockResolvedValue([
        { id: "doc-0", name: "Existente", revision: 1, updated_at: "2026-09-12T10:05:00Z" },
      ]);
    vi.mocked(docsLib.createDocument).mockResolvedValueOnce({
      id: "doc-1",
      owner_id: "1",
      revision: 0,
      metadata: { name: "Ventas", description: "" },
      model: { classes: [], enumerations: [], relationships: [], generation_metadata: {} },
      layout: { positions: {} },
      created_at: "2026-09-12T10:00:00Z",
      updated_at: "2026-09-12T10:00:00Z",
    });

    renderPage();
    await screen.findByRole("link", { name: /Existente/ });
    expect(screen.queryByLabelText("Nombre del diagrama")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Nuevo diagrama" }));
    fireEvent.change(await screen.findByLabelText("Nombre del diagrama"), {
      target: { value: "Ventas" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Crear diagrama" }));

    await vi.waitFor(() => expect(mockPush).toHaveBeenCalledWith("/documents/doc-1"));
    expect(docsLib.createDocument).toHaveBeenCalledWith("acme", { name: "Ventas" });
  });

  it("renders the diagrams as cards linking to their page, with the header actions above", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme()]);
    vi.mocked(docsLib.listDocuments)
      .mockReset()
      .mockResolvedValueOnce([
        { id: "doc-1", name: "Ventas", revision: 4, updated_at: "2026-09-12T10:05:00Z" },
        { id: "doc-2", name: "", revision: 1, updated_at: "2026-09-11T09:00:00Z" },
      ]);
    renderPage();

    const card = await screen.findByRole("link", { name: /Ventas/ });
    expect(card).toHaveAttribute("href", "/documents/doc-1");
    expect(card).toHaveTextContent("Revisión 4");
    expect(screen.getByRole("link", { name: /Sin título/ })).toHaveAttribute(
      "href",
      "/documents/doc-2",
    );
    expect(docsLib.listDocuments).toHaveBeenCalledWith("acme");

    const newButton = screen.getByRole("button", { name: "Nuevo diagrama" });
    expect(
      newButton.compareDocumentPosition(card) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: /Importar XML/ })).toBeInTheDocument();
  });

  it("with zero diagrams shows the empty state carrying both actions exactly once", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme()]);
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Todavía no hay diagramas" }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Nuevo diagrama" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /Importar XML/ })).toHaveLength(1);
  });

  it("shows a loading skeleton instead of the empty state while documents load", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme()]);
    vi.mocked(docsLib.listDocuments).mockReset().mockImplementation(() => new Promise(() => {}));
    renderPage();

    await screen.findByRole("heading", { level: 1, name: "Acme" });
    expect(screen.getByRole("status", { name: "Cargando diagramas" })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Todavía no hay diagramas" }),
    ).not.toBeInTheDocument();
  });

  it('hides the create actions for a VIEWER, who would always get a 403', async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme("VIEWER")]);
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Todavía no hay diagramas" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Nuevo diagrama" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Importar XML/ })).not.toBeInTheDocument();
  });

  it('shows "Nuevo diagrama" for an EDITOR, not just OWNER', async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([acme("EDITOR")]);
    renderPage();

    expect(await screen.findByRole("button", { name: "Nuevo diagrama" })).toBeInTheDocument();
  });
});
