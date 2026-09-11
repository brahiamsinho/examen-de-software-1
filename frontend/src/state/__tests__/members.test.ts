import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as orgsLib from "@/lib/organizations";
import { useMembers } from "@/state/members";

/**
 * `useMembers` owns local `useState` (design.md DD2), not a shared atom: the
 * roster has exactly one consumer (the container page) and must reset per
 * tenant. Idle while `orgSlug` is null; fetches/refetches when it changes;
 * mutators update `members` from the awaited response with no refetch and
 * rethrow on rejection so the container can render the 409 inline (DD1/DD3).
 */
vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return {
    ...actual,
    listMembers: vi.fn(),
    addMember: vi.fn(),
    changeMemberRole: vi.fn(),
    removeMember: vi.fn(),
  };
});

const memberA = {
  user_id: "1",
  email: "owner@example.com",
  full_name: "Owner",
  role: "OWNER" as const,
  created_at: "2026-01-01T00:00:00Z",
};
const memberB = {
  user_id: "2",
  email: "editor@example.com",
  full_name: "Editor",
  role: "EDITOR" as const,
  created_at: "2026-01-02T00:00:00Z",
};

describe("state/members useMembers()", () => {
  beforeEach(() => {
    vi.mocked(orgsLib.listMembers).mockReset();
    vi.mocked(orgsLib.addMember).mockReset();
    vi.mocked(orgsLib.changeMemberRole).mockReset();
    vi.mocked(orgsLib.removeMember).mockReset();
  });

  it("stays idle and does not fetch when orgSlug is null", () => {
    const { result } = renderHook(() => useMembers(null));

    expect(result.current.members).toEqual([]);
    expect(result.current.loading).toBe(false);
    expect(orgsLib.listMembers).not.toHaveBeenCalled();
  });

  it("fetches members on mount when orgSlug is provided", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([memberA, memberB]);

    const { result } = renderHook(() => useMembers("acme"));

    await waitFor(() => expect(result.current.members).toEqual([memberA, memberB]));
    expect(orgsLib.listMembers).toHaveBeenCalledWith("acme");
  });

  it("refetches when orgSlug changes", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([memberA]);
    const { result, rerender } = renderHook(({ slug }) => useMembers(slug), {
      initialProps: { slug: "acme" as string | null },
    });
    await waitFor(() => expect(result.current.members).toEqual([memberA]));

    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([memberB]);
    rerender({ slug: "beta" });

    await waitFor(() => expect(result.current.members).toEqual([memberB]));
    expect(orgsLib.listMembers).toHaveBeenCalledWith("beta");
  });

  it("addMember appends the returned member without a refetch", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([memberA]);
    const { result } = renderHook(() => useMembers("acme"));
    await waitFor(() => expect(result.current.members).toEqual([memberA]));

    const newMember = {
      user_id: "3",
      email: "viewer@example.com",
      full_name: "Viewer",
      role: "VIEWER" as const,
      created_at: "2026-01-03T00:00:00Z",
    };
    vi.mocked(orgsLib.addMember).mockResolvedValueOnce(newMember);

    await act(async () => {
      await result.current.addMember({ email: "viewer@example.com", role: "VIEWER" });
    });

    expect(result.current.members).toEqual([memberA, newMember]);
    expect(orgsLib.listMembers).toHaveBeenCalledOnce();
  });

  it("changeMemberRole replaces the row with the returned member without a refetch", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([memberA, memberB]);
    const { result } = renderHook(() => useMembers("acme"));
    await waitFor(() => expect(result.current.members).toEqual([memberA, memberB]));

    const updated = { ...memberB, role: "VIEWER" as const };
    vi.mocked(orgsLib.changeMemberRole).mockResolvedValueOnce(updated);

    await act(async () => {
      await result.current.changeMemberRole(memberB.user_id, "VIEWER");
    });

    expect(result.current.members).toEqual([memberA, updated]);
    expect(orgsLib.listMembers).toHaveBeenCalledOnce();
  });

  it("removeMember drops the row without a refetch", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([memberA, memberB]);
    const { result } = renderHook(() => useMembers("acme"));
    await waitFor(() => expect(result.current.members).toEqual([memberA, memberB]));

    vi.mocked(orgsLib.removeMember).mockResolvedValueOnce(undefined);

    await act(async () => {
      await result.current.removeMember(memberB.user_id);
    });

    expect(result.current.members).toEqual([memberA]);
    expect(orgsLib.listMembers).toHaveBeenCalledOnce();
  });

  it("a rejected mutation leaves members unchanged and rethrows", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([memberA, memberB]);
    const { result } = renderHook(() => useMembers("acme"));
    await waitFor(() => expect(result.current.members).toEqual([memberA, memberB]));

    vi.mocked(orgsLib.removeMember).mockRejectedValueOnce(new Error("409"));

    await expect(
      act(async () => {
        await result.current.removeMember(memberA.user_id);
      }),
    ).rejects.toThrow("409");

    expect(result.current.members).toEqual([memberA, memberB]);
  });
});
