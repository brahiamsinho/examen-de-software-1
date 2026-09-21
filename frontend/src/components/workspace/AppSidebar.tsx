"use client";

import { useAtomValue, useSetAtom } from "jotai";
import { LogOut, Menu as MenuIcon, Users, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { NewDocumentDialog } from "@/components/workspace/NewDocumentDialog";
import { OrgSwitcher } from "@/components/workspace/OrgSwitcher";
import { SidebarDiagrams } from "@/components/workspace/SidebarDiagrams";
import { logout } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { useDocumentActions, useDocuments } from "@/state/documents";
import { useOrganizations } from "@/state/organizations";
import { sessionAtom } from "@/state/session";

/**
 * Rendered inside `SessionGuard` by `app/(app)/layout.tsx`. Pure navigation,
 * top to bottom: the organization switcher (which also hosts "Crear
 * organización"), the current organization's diagrams, the Miembros link,
 * and the account footer with logout. Owns the single `useOrganizations()`
 * and `useDocuments()` instances for the shell; `app/(app)/dashboard` keeps
 * its own (siblings under the layout cannot share a hook instance — the
 * organization list converges on the shared atom, and the document list
 * stays fresh through the shared invalidation counter in `state/documents`).
 *
 * Below `md` the sidebar stacks above the page as a slim bar whose menu
 * toggles open — the simplest responsive behavior that keeps every control
 * reachable.
 *
 * The only logout affordance in the app: clears `sessionAtom` directly
 * instead of waiting for a `fetchMe()` round trip, then redirects to `/`
 * (spec `web-session` § Login and Logout).
 */
export function AppSidebar() {
  const router = useRouter();
  const pathname = usePathname() ?? "";
  const session = useAtomValue(sessionAtom);
  const setSession = useSetAtom(sessionAtom);
  const { organizations, activeSlug, setActiveOrg, createOrganization } = useOrganizations();
  const activeOrg = organizations.find((org) => org.slug === activeSlug) ?? null;
  const canCreateDocument = activeOrg?.my_role === "OWNER" || activeOrg?.my_role === "EDITOR";
  const { documents, loading } = useDocuments(activeOrg?.slug ?? null);
  const { createDiagram } = useDocumentActions(activeOrg?.slug ?? null);
  const [newDiagramOpen, setNewDiagramOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  const activeDocId = /^\/documents\/([^/]+)/.exec(pathname)?.[1] ?? null;
  const membersActive = pathname.startsWith("/settings/members");
  const user = session.status === "authenticated" ? session.user : null;

  async function handleLogout() {
    await logout();
    setSession({ status: "anonymous" });
    router.replace("/");
  }

  return (
    <aside className="flex shrink-0 flex-col border-b border-border bg-sidebar text-sidebar-foreground md:sticky md:top-0 md:h-screen md:w-64 md:border-r md:border-b-0">
      <div className="flex items-center justify-between px-3 pt-3 md:hidden">
        <span className="font-heading text-base font-semibold">Modelia</span>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={menuOpen ? "Cerrar menú" : "Abrir menú"}
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X /> : <MenuIcon />}
        </Button>
      </div>

      <div className={cn("min-h-0 flex-1 flex-col gap-4 p-3 md:flex", menuOpen ? "flex" : "hidden")}>
        <OrgSwitcher
          organizations={organizations}
          activeSlug={activeSlug}
          onSelect={setActiveOrg}
          onCreate={createOrganization}
        />

        <div className="flex max-h-72 min-h-0 flex-col md:max-h-none md:flex-1">
          <SidebarDiagrams
            documents={documents}
            loading={loading}
            activeDocId={activeDocId}
            onNew={canCreateDocument ? () => setNewDiagramOpen(true) : undefined}
          />
        </div>

        <nav aria-label="Organización" className="flex flex-col gap-0.5 border-t border-border pt-3">
          <Link
            href="/settings/members"
            aria-current={membersActive ? "page" : undefined}
            className={cn(
              "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
              membersActive
                ? "bg-accent text-accent-foreground"
                : "text-foreground hover:bg-background",
            )}
          >
            <Users className="size-4" aria-hidden="true" />
            Miembros
          </Link>
        </nav>

        <div className="flex flex-col gap-1 border-t border-border pt-3">
          {user ? (
            <p className="truncate px-2.5 text-xs text-muted-foreground" title={user.email}>
              {user.full_name || user.email}
            </p>
          ) : null}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="w-full justify-start px-2.5 font-medium"
            onClick={handleLogout}
          >
            <LogOut />
            Cerrar sesión
          </Button>
        </div>
      </div>

      {activeOrg ? (
        <NewDocumentDialog
          open={newDiagramOpen}
          onOpenChange={setNewDiagramOpen}
          onCreate={createDiagram}
        />
      ) : null}
    </aside>
  );
}
