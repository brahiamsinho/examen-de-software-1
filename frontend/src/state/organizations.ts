import { atom, useAtom, useSetAtom } from "jotai";
import { useRouter } from "next/navigation";
import { useCallback, useEffect } from "react";

import {
  createOrganization as createOrganizationApi,
  listOrganizations,
  removeMember,
  type Organization,
} from "@/lib/organizations";

/**
 * Plain atom + explicit effect, not `atomWithStorage` (design.md DD6):
 * `atomWithStorage` initializes from storage during render, which would
 * cause an SSR hydration mismatch. `useOrganizations()` instead reads
 * localStorage in a post-mount effect and writes only on explicit
 * selection. This is a UI convenience only — no request may derive its
 * org from this atom; the backend fixes the tenant key as a URL segment.
 */
const ACTIVE_ORG_STORAGE_KEY = "modelia:active-org-slug";

export const organizationsAtom = atom<Organization[]>([]);
export const activeOrgSlugAtom = atom<string | null>(null);

/**
 * Single writer for the persisted active-org key (extracted from
 * `useSetActiveOrg`'s inline call so `useLeaveOrganization` can reuse it for
 * the `null` case — "no organization" — that `useSetActiveOrg` never needed).
 * Swallows storage failure (quota/private mode, design.md's self-removal
 * data-flow note): the atom repoint is the source of truth for this render,
 * and the existing `stillMember` check in `useOrganizations()` self-heals a
 * stale key on next load.
 */
export function persistActiveOrgSlug(slug: string | null): void {
  try {
    if (slug === null) {
      window.localStorage.removeItem(ACTIVE_ORG_STORAGE_KEY);
    } else {
      window.localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, slug);
    }
  } catch {
    // Storage failure is not fatal — see docblock.
  }
}

/**
 * The write half of `useOrganizations` (design.md DD5, DV1), extracted so
 * `LoginForm`/`RegisterForm` can set the active org after login/register
 * without calling `useOrganizations()` itself — that hook's mount effect
 * would fire an anonymous `listOrganizations()` on the auth page and 401.
 */
export function useSetActiveOrg() {
  const setActiveSlug = useSetAtom(activeOrgSlugAtom);
  return useCallback(
    (slug: string) => {
      setActiveSlug(slug);
      persistActiveOrgSlug(slug);
    },
    [setActiveSlug],
  );
}

/**
 * Self-removal repointing (design.md "Data Flow — self-removal"). Ordering
 * is load-bearing: `removeMember` first (a rejection — e.g. the 409
 * last-owner invariant — leaves every atom and the storage key untouched,
 * verbatim `ApiError` rethrown to the caller); then organizations/active-slug
 * atoms are written synchronously in the same tick as the `persistActiveOrgSlug`
 * call; only then does `router.replace("/dashboard")` fire, so `AppTopbar`
 * (which survives the navigation, living in the `(app)` layout) never renders
 * a stale org.
 */
export function useLeaveOrganization() {
  const [organizations, setOrganizations] = useAtom(organizationsAtom);
  const setActiveSlug = useSetAtom(activeOrgSlugAtom);
  const router = useRouter();

  return useCallback(
    async (orgSlug: string, userId: string) => {
      await removeMember(orgSlug, userId);

      const remaining = organizations.filter((org) => org.slug !== orgSlug);
      const nextSlug = remaining[0]?.slug ?? null;
      setOrganizations(remaining);
      setActiveSlug(nextSlug);
      persistActiveOrgSlug(nextSlug);

      router.replace("/dashboard");
    },
    [organizations, setOrganizations, setActiveSlug, router],
  );
}

export function useOrganizations() {
  const [organizations, setOrganizations] = useAtom(organizationsAtom);
  const [activeSlug, setActiveSlug] = useAtom(activeOrgSlugAtom);
  const setActiveOrg = useSetActiveOrg();

  useEffect(() => {
    let cancelled = false;

    listOrganizations().then((orgs) => {
      if (!cancelled) setOrganizations(orgs);
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (organizations.length === 0) return;

    const persisted = window.localStorage.getItem(ACTIVE_ORG_STORAGE_KEY);
    const stillMember = persisted && organizations.some((org) => org.slug === persisted);
    setActiveSlug(stillMember ? persisted : organizations[0]!.slug);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizations]);

  /** Optimistic append (design.md DD7): `POST /api/orgs` already returns
   * the creator as `my_role: "OWNER"`, so the new org is appended and made
   * active directly from the response — no refetch. */
  const createOrganization = useCallback(
    async (input: { name: string; slug: string }) => {
      const org = await createOrganizationApi(input);
      setOrganizations((prev) => [...prev, org]);
      setActiveOrg(org.slug);
      return org;
    },
    [setOrganizations, setActiveOrg],
  );

  return { organizations, activeSlug, setActiveOrg, createOrganization };
}
