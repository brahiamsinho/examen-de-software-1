import { atom, useAtom, useSetAtom } from "jotai";
import { useCallback, useEffect } from "react";

import {
  createOrganization as createOrganizationApi,
  listOrganizations,
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
      window.localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, slug);
    },
    [setActiveSlug],
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
