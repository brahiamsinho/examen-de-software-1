import { useCallback, useEffect, useState } from "react";

import {
  addMember as addMemberApi,
  changeMemberRole as changeMemberRoleApi,
  listMembers,
  removeMember as removeMemberApi,
  type Member,
  type Role,
} from "@/lib/organizations";

/**
 * Local `useState`, not a Jotai atom (design.md DD2): the roster has exactly
 * one consumer (the settings/members container) and must reset per tenant —
 * a module atom would leak one org's roster into the next. Idle while
 * `orgSlug` is null; fetches on mount and refetches when `orgSlug` changes.
 * Mutators never pre-update local state (DD3): each awaits the response,
 * then writes the returned row into `members` (append / replace / drop). A
 * rejection leaves `members` untouched and rethrows so the container can
 * render `ApiError.detail` inline against the affected row.
 */
export function useMembers(orgSlug: string | null) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(orgSlug !== null);
  const [error, setError] = useState<string | null>(null);
  const [trackedSlug, setTrackedSlug] = useState(orgSlug);

  /**
   * React's "adjusting state when a prop changes" pattern: reset
   * synchronously during render instead of inside the effect below, so
   * switching (or clearing) `orgSlug` never paints a stale roster from the
   * previous org for a frame. Keeps the effect's body limited to the actual
   * external synchronization (the fetch), satisfying the
   * `react-hooks/set-state-in-effect` rule.
   */
  if (orgSlug !== trackedSlug) {
    setTrackedSlug(orgSlug);
    setMembers([]);
    setError(null);
    setLoading(orgSlug !== null);
  }

  useEffect(() => {
    if (orgSlug === null) return;

    let cancelled = false;

    listMembers(orgSlug)
      .then((fetched) => {
        if (!cancelled) setMembers(fetched);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [orgSlug]);

  const addMember = useCallback(
    async (input: { email: string; role: "EDITOR" | "VIEWER" }) => {
      if (orgSlug === null) throw new Error("No active organization");
      const created = await addMemberApi(orgSlug, input);
      setMembers((prev) => [...prev, created]);
      return created;
    },
    [orgSlug],
  );

  const changeMemberRole = useCallback(
    async (userId: string, role: Exclude<Role, "OWNER">) => {
      if (orgSlug === null) throw new Error("No active organization");
      const updated = await changeMemberRoleApi(orgSlug, userId, role);
      setMembers((prev) => prev.map((member) => (member.user_id === userId ? updated : member)));
      return updated;
    },
    [orgSlug],
  );

  const removeMember = useCallback(
    async (userId: string) => {
      if (orgSlug === null) throw new Error("No active organization");
      await removeMemberApi(orgSlug, userId);
      setMembers((prev) => prev.filter((member) => member.user_id !== userId));
    },
    [orgSlug],
  );

  return { members, loading, error, addMember, changeMemberRole, removeMember };
}
