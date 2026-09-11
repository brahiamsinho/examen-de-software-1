import { act, renderHook, waitFor } from "@testing-library/react";
import { createStore, Provider, useAtomValue } from "jotai";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as orgsLib from "@/lib/organizations";
import {
  activeOrgSlugAtom,
  organizationsAtom,
  persistActiveOrgSlug,
  useLeaveOrganization,
  useOrganizations,
  useSetActiveOrg,
} from "@/state/organizations";

const ACTIVE_ORG_STORAGE_KEY = "modelia:active-org-slug";

/**
 * `useOrganizations()` owns the `listOrganizations()` fetch and the
 * localStorage-backed active-org selection (design.md DD6/DD7). Each test
 * renders inside a fresh `<Provider>` and clears localStorage first.
 */
vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return { ...actual, listOrganizations: vi.fn(), createOrganization: vi.fn(), removeMember: vi.fn() };
});

const replace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace }) }));

function wrapper({ children }: { children: ReactNode }) {
  return createElement(Provider, null, children);
}

function storeWrapper(store: ReturnType<typeof createStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(Provider, { store }, children);
  };
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

/**
 * `useSetActiveOrg` (design.md DD5, DV1) is the write half of
 * `useOrganizations`, extracted so `LoginForm`/`RegisterForm` can set the
 * active org without mounting the fetch effect (which would fire an
 * anonymous `listOrganizations()` on the login/register page).
 */
describe("state/organizations useSetActiveOrg()", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("sets the active org slug atom and persists it to localStorage", () => {
    const { result } = renderHook(
      () => ({ setActiveOrg: useSetActiveOrg(), activeSlug: useAtomValue(activeOrgSlugAtom) }),
      { wrapper },
    );

    act(() => {
      result.current.setActiveOrg("acme");
    });

    expect(result.current.activeSlug).toBe("acme");
    expect(window.localStorage.getItem("modelia:active-org-slug")).toBe("acme");
  });
});

/**
 * `persistActiveOrgSlug` (design.md's leave-org helper, extracted from
 * `useSetActiveOrg`'s inline `localStorage.setItem` call) is the single
 * writer for the storage key: a string slug persists it, `null` removes it
 * — the case `useSetActiveOrg` never needed until self-removal.
 */
describe("persistActiveOrgSlug", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("persists a slug to localStorage", () => {
    persistActiveOrgSlug("acme");

    expect(window.localStorage.getItem(ACTIVE_ORG_STORAGE_KEY)).toBe("acme");
  });

  it("removes the storage key when given null", () => {
    window.localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, "acme");

    persistActiveOrgSlug(null);

    expect(window.localStorage.getItem(ACTIVE_ORG_STORAGE_KEY)).toBeNull();
  });
});

/**
 * `useLeaveOrganization` (design.md's self-removal repointing, "highest
 * risk" per tasks.md Phase 2) — each test seeds an explicit jotai `store` so
 * assertions can read atom state directly via `store.get(...)` instead of
 * re-rendering a harness component.
 */
describe("state/organizations useLeaveOrganization()", () => {
  beforeEach(() => {
    vi.mocked(orgsLib.removeMember).mockReset();
    replace.mockReset();
    window.localStorage.clear();
  });

  it("repoints the active org to the first remaining org (two-org case)", async () => {
    const store = createStore();
    store.set(organizationsAtom, [orgA, orgB]);
    store.set(activeOrgSlugAtom, "acme");
    window.localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, "acme");
    vi.mocked(orgsLib.removeMember).mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useLeaveOrganization(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current("acme", "user-1");
    });

    expect(orgsLib.removeMember).toHaveBeenCalledWith("acme", "user-1");
    expect(store.get(organizationsAtom)).toEqual([orgB]);
    expect(store.get(activeOrgSlugAtom)).toBe("beta");
    expect(window.localStorage.getItem(ACTIVE_ORG_STORAGE_KEY)).toBe("beta");
    expect(replace).toHaveBeenCalledWith("/dashboard");
  });

  it("falls back to the no-organization state when no org remains (zero-remaining case)", async () => {
    const store = createStore();
    store.set(organizationsAtom, [orgA]);
    store.set(activeOrgSlugAtom, "acme");
    window.localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, "acme");
    vi.mocked(orgsLib.removeMember).mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useLeaveOrganization(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current("acme", "user-1");
    });

    expect(store.get(organizationsAtom)).toEqual([]);
    expect(store.get(activeOrgSlugAtom)).toBeNull();
    expect(window.localStorage.getItem(ACTIVE_ORG_STORAGE_KEY)).toBeNull();
    expect(replace).toHaveBeenCalledWith("/dashboard");
  });

  it("leaves atoms and storage untouched and does not redirect when removeMember rejects", async () => {
    const store = createStore();
    store.set(organizationsAtom, [orgA, orgB]);
    store.set(activeOrgSlugAtom, "acme");
    window.localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, "acme");
    vi.mocked(orgsLib.removeMember).mockRejectedValueOnce(new Error("network down"));

    const { result } = renderHook(() => useLeaveOrganization(), { wrapper: storeWrapper(store) });

    await expect(
      act(async () => {
        await result.current("acme", "user-1");
      }),
    ).rejects.toThrow("network down");

    expect(store.get(organizationsAtom)).toEqual([orgA, orgB]);
    expect(store.get(activeOrgSlugAtom)).toBe("acme");
    expect(window.localStorage.getItem(ACTIVE_ORG_STORAGE_KEY)).toBe("acme");
    expect(replace).not.toHaveBeenCalled();
  });

  it("still repoints atoms and redirects when localStorage.setItem throws", async () => {
    const store = createStore();
    store.set(organizationsAtom, [orgA, orgB]);
    store.set(activeOrgSlugAtom, "acme");
    vi.mocked(orgsLib.removeMember).mockResolvedValueOnce(undefined);
    const setItemSpy = vi
      .spyOn(Storage.prototype, "setItem")
      .mockImplementationOnce(() => {
        throw new Error("quota exceeded");
      });

    const { result } = renderHook(() => useLeaveOrganization(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current("acme", "user-1");
    });

    expect(store.get(organizationsAtom)).toEqual([orgB]);
    expect(store.get(activeOrgSlugAtom)).toBe("beta");
    expect(replace).toHaveBeenCalledWith("/dashboard");

    setItemSpy.mockRestore();
  });

  it("commits atom writes before router.replace fires", async () => {
    const store = createStore();
    store.set(organizationsAtom, [orgA, orgB]);
    store.set(activeOrgSlugAtom, "acme");
    vi.mocked(orgsLib.removeMember).mockResolvedValueOnce(undefined);

    let activeSlugAtReplaceTime: string | null | undefined;
    let organizationsAtReplaceTime: string[] | undefined;
    replace.mockImplementationOnce(() => {
      activeSlugAtReplaceTime = store.get(activeOrgSlugAtom);
      organizationsAtReplaceTime = store.get(organizationsAtom).map((org) => org.slug);
    });

    const { result } = renderHook(() => useLeaveOrganization(), { wrapper: storeWrapper(store) });

    await act(async () => {
      await result.current("acme", "user-1");
    });

    expect(activeSlugAtReplaceTime).toBe("beta");
    expect(organizationsAtReplaceTime).toEqual(["beta"]);
  });
});
