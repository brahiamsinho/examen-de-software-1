import { fireEvent, render, screen } from "@testing-library/react";
import { createStore, Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/(app)/dashboard/page";
import * as orgsLib from "@/lib/organizations";
import { sessionAtom } from "@/state/session";

/**
 * Container: owns the single `useOrganizations()` instance for this route
 * and wires its `createOrganization` down into `CreateOrgForm` as
 * `onCreate` (task 6.9's empty-state vs. populated branching, plus the
 * end-to-end "appears in the list / becomes active without a manual
 * refetch" scenario from task 6.5 — `CreateOrgForm.test.tsx` itself only
 * proves the prop is called correctly, since it no longer owns the hook).
 */
vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn(), createOrganization: vi.fn() };
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
  });

  // Precondition-agnostic by design (web-organization-workspace § Zero-Organization Empty
  // State, DD7): the frontend cannot distinguish a legacy pre-change account from a user
  // whose sole org was deleted — both just render `organizations.length === 0`. This one
  // test is the evidence for both "Legacy pre-change account reaches the empty state" and
  // "Sole organization deleted falls back to the empty state" scenarios.
  it("renders the empty state and the creation form when there are no organizations", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    renderPage();

    expect(
      await screen.findByRole("heading", { name: "Crea tu primera organización" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear organización" })).toBeInTheDocument();
  });

  it("renders the active org detail and the creation form when organizations exist", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([
      { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const },
    ]);
    renderPage();

    expect(await screen.findByRole("heading", { name: "Acme" })).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Crea tu primera organización" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Crear organización" })).toBeInTheDocument();
  });

  it("creating an organization from the empty state shows it as active without a manual refetch", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([]);
    const gamma = { id: "3", name: "Gamma", slug: "gamma", plan: "free", my_role: "OWNER" as const };
    vi.mocked(orgsLib.createOrganization).mockResolvedValueOnce(gamma);

    renderPage();
    await screen.findByRole("heading", { name: "Crea tu primera organización" });

    fireEvent.change(screen.getByLabelText("Nombre de la organización"), {
      target: { value: "Gamma" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Crear organización" }));

    expect(await screen.findByRole("heading", { name: "Gamma" })).toBeInTheDocument();
    expect(orgsLib.listOrganizations).toHaveBeenCalledOnce();
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
});
