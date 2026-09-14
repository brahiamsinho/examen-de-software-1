"use client";

import { useSetAtom } from "jotai";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { OrgSwitcher } from "@/components/workspace/OrgSwitcher";
import { Button } from "@/components/ui/button";
import { logout } from "@/lib/auth";
import { useOrganizations } from "@/state/organizations";
import { sessionAtom } from "@/state/session";

/**
 * Rendered inside `SessionGuard` by `app/(app)/layout.tsx`, sibling to the
 * route's own `{children}` — replaces the prior horizontal `AppTopbar`
 * (design.md's original Technical Approach) with a persistent left sidebar,
 * per the user's explicit redesign request. Owns the single
 * `useOrganizations()` call for `OrgSwitcher`; `app/(app)/dashboard` owns a
 * second, separate instance for its own needs (empty-state check +
 * `CreateOrgForm`) since the two are siblings under the layout and cannot
 * share a hook instance — see `AppLayout`'s docblock for this documented
 * tradeoff, unchanged by this redesign.
 *
 * The only logout affordance in the app: clears `sessionAtom` directly
 * instead of waiting for a `fetchMe()` round trip, then redirects to `/`
 * (spec `web-session` § Login and Logout).
 */
export function AppSidebar() {
  const router = useRouter();
  const setSession = useSetAtom(sessionAtom);
  const { organizations, activeSlug, setActiveOrg } = useOrganizations();

  async function handleLogout() {
    await logout();
    setSession({ status: "anonymous" });
    router.replace("/");
  }

  return (
    <aside className="flex h-screen w-64 shrink-0 flex-col border-r border-border bg-muted">
      <div className="flex-1 overflow-y-auto p-3">
        <nav className="flex flex-col gap-0.5">
          <Link
            href="/dashboard"
            className="rounded-md px-2.5 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-background"
          >
            Diagramas
          </Link>
          <Link
            href="/settings/members"
            className="rounded-md px-2.5 py-1.5 text-sm font-medium text-foreground transition-colors hover:bg-background"
          >
            Miembros
          </Link>
        </nav>

        <p className="mt-4 border-t border-border px-2.5 pt-4 text-xs font-medium text-muted-foreground">
          Organizaciones
        </p>
        <OrgSwitcher organizations={organizations} activeSlug={activeSlug} onSelect={setActiveOrg} />
      </div>

      <div className="border-t border-border p-3">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="w-full justify-start px-2.5 font-medium"
          onClick={handleLogout}
        >
          Cerrar sesión
        </Button>
      </div>
    </aside>
  );
}
