import { act, renderHook, waitFor } from "@testing-library/react";
import { Provider } from "jotai";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as orgsLib from "@/lib/organizations";
import { useOrganizations } from "@/state/organizations";

/**
 * `useOrganizations()` owns the `listOrganizations()` fetch and the
 * localStorage-backed active-org selection (design.md DD6/DD7). Each test
 * renders inside a fresh `<Provider>` and clears localStorage first.
 */
vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn(), createOrganization: vi.fn() };
});

function wrapper({ children }: { children: ReactNode }) {
  return createElement(Provider, null, children);
}

const orgA = { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const };
const orgB = { id: "2", name: "Beta", slug: "beta", plan: "free", my_role: "EDITOR" as const };

describe("state/organizations useOrganizations()", () => {
  beforeEach(() => {
    vi.mocked(orgsLib.listOrganizations).mockReset();
    vi.mocked(orgsLib.createOrganization).mockReset();
    window.localStorage.clear();
  });

  it("falls back to the first listed org when no slug is persisted", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA, orgB]);

    const { result } = renderHook(() => useOrganizations(), { wrapper });

    await waitFor(() => expect(result.current.organizations).toEqual([orgA, orgB]));
    expect(result.current.activeSlug).toBe("acme");
  });

  it("keeps the persisted slug active when it is still in the fetched list", async () => {
    window.localStorage.setItem("modelia:active-org-slug", "beta");
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA, orgB]);

    const { result } = renderHook(() => useOrganizations(), { wrapper });

    await waitFor(() => expect(result.current.activeSlug).toBe("beta"));
  });

  it("falls back to the first listed org when the persisted slug matches no membership", async () => {
    window.localStorage.setItem("modelia:active-org-slug", "ghost");
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA, orgB]);

    const { result } = renderHook(() => useOrganizations(), { wrapper });

    await waitFor(() => expect(result.current.activeSlug).toBe("acme"));
  });

  it("appends a created org optimistically and activates it without a refetch", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA]);
    const gamma = { id: "3", name: "Gamma", slug: "gamma", plan: "free", my_role: "OWNER" as const };
    vi.mocked(orgsLib.createOrganization).mockResolvedValueOnce(gamma);

    const { result } = renderHook(() => useOrganizations(), { wrapper });
    await waitFor(() => expect(result.current.activeSlug).toBe("acme"));

    await act(async () => {
      await result.current.createOrganization({ name: "Gamma", slug: "gamma" });
    });

    expect(result.current.organizations).toEqual([orgA, gamma]);
    expect(result.current.activeSlug).toBe("gamma");
    expect(orgsLib.listOrganizations).toHaveBeenCalledOnce();
  });

  it("setActiveOrg persists the selection to localStorage", async () => {
    vi.mocked(orgsLib.listOrganizations).mockResolvedValueOnce([orgA, orgB]);

    const { result } = renderHook(() => useOrganizations(), { wrapper });
    await waitFor(() => expect(result.current.activeSlug).toBe("acme"));

    act(() => {
      result.current.setActiveOrg("beta");
    });

    expect(result.current.activeSlug).toBe("beta");
    expect(window.localStorage.getItem("modelia:active-org-slug")).toBe("beta");
  });
});
