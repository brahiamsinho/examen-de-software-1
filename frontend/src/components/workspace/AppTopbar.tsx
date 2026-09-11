"use client";

import { useSetAtom } from "jotai";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { OrgSwitcher } from "@/components/workspace/OrgSwitcher";
import { logout } from "@/lib/auth";
import { useOrganizations } from "@/state/organizations";
import { sessionAtom } from "@/state/session";

/**
 * Rendered inside `SessionGuard` by `app/(app)/layout.tsx` (design.md
 * Technical Approach), sibling to the route's own `{children}`. Owns the
 * single `useOrganizations()` call for `OrgSwitcher`; `app/(app)/dashboard`
 * owns a second, separate instance for its own needs (empty-state check +
 * `CreateOrgForm`) since the two are siblings under the layout and cannot
 * share a hook instance — see Deviations for this documented tradeoff.
 *
 * The only logout affordance in the app (completes task 5.6, deferred from
 * PR2): clears `sessionAtom` directly instead of waiting for a `fetchMe()`
 * round trip, then redirects to `/` (spec `web-session` § Login and
 * Logout).
 */
export function AppTopbar() {
  const router = useRouter();
  const setSession = useSetAtom(sessionAtom);
  const { organizations, activeSlug, setActiveOrg } = useOrganizations();

  async function handleLogout() {
    await logout();
    setSession({ status: "anonymous" });
    router.replace("/");
  }

  return (
    <header className="flex items-center justify-between border-b border-border px-6 py-3">
      <OrgSwitcher organizations={organizations} activeSlug={activeSlug} onSelect={setActiveOrg} />
      <nav className="flex items-center gap-4">
        <Link href="/settings/members" className="text-sm font-semibold underline">
          Miembros
        </Link>
        <button type="button" onClick={handleLogout} className="text-sm font-semibold underline">
          Cerrar sesión
        </button>
      </nav>
    </header>
  );
}
