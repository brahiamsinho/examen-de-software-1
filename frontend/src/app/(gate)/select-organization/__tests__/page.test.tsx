import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import SelectOrganizationPage from "@/app/(gate)/select-organization/page";
import * as orgsLib from "@/lib/organizations";

/**
 * Container: `useOrganizations()` + `OrgPicker` + `setActiveOrg` then
 * `router.replace("/dashboard")` (design.md DD4). A list with fewer than 2
 * organizations redirects to `/dashboard` so a bookmarked/back-button visit
 * can never become a permanent dead end.
 */
const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn() };
});

function renderPage() {
  return render(
    <Provider>
      <SelectOrganizationPage />
    </Provider>,
  );
}

const orgA = { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const };
const orgB = { id: "2", name: "Beta", slug: "beta", plan: "free", my_role: "EDITOR" as const };

describe("SelectOrganizationPage", () => {
  beforeEach(() => {
    replace.mockReset();
    vi.mocked(orgsLib.listOrganizations).mockReset();
    window.localStorage.clear();
  });

  it("selecting an organization sets it active and redirects to /dashboard", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA, orgB]);

    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /Beta/ }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
    expect(window.localStorage.getItem("modelia:active-org-slug")).toBe("beta");
  });

  it("selection survives a page reload (persisted to localStorage)", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA, orgB]);
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: /Acme/ }));
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));

    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA, orgB]);
    renderPage();

    await waitFor(() => expect(window.localStorage.getItem("modelia:active-org-slug")).toBe("acme"));
  });

  it("redirects to /dashboard when the loaded list has fewer than 2 organizations", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA]);

    renderPage();

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard"));
  });
});
