"use client";

import { Menu } from "@base-ui/react/menu";
import { Check, ChevronsUpDown, Plus } from "lucide-react";
import { useState } from "react";

import { CreateOrgDialog } from "@/components/workspace/CreateOrgDialog";
import { ROLE_LABELS } from "@/components/workspace/roleLabels";
import type { Organization } from "@/lib/organizations";

type OrgSwitcherProps = {
  organizations: Organization[];
  activeSlug: string | null;
  onSelect: (slug: string) => void;
  onCreate: (input: { name: string; slug: string }) => Promise<Organization>;
};

/** The API does not forbid an empty name; keep the row readable. */
const orgName = (org: Organization) => org.name.trim() || "Sin nombre";

const ITEM_CLASS =
  "flex cursor-default items-center gap-2 rounded-md px-2 py-1.5 text-sm outline-none select-none data-highlighted:bg-muted";

/**
 * Sidebar header: shows the current organization (name + role) and opens a
 * menu to switch or to create another one. Presentational — its container
 * (`AppSidebar`) owns the single `useOrganizations()` call and passes the
 * state and both callbacks down. Base UI's Menu supplies the keyboard model
 * (arrows, Home/End, typeahead, Escape, focus return); the active
 * organization is a `menuitemradio`, so assistive tech announces which one is
 * current. "Crear organización" opens a modal that hosts the existing form.
 */
export function OrgSwitcher({ organizations, activeSlug, onSelect, onCreate }: OrgSwitcherProps) {
  const [createOpen, setCreateOpen] = useState(false);
  const active = organizations.find((org) => org.slug === activeSlug) ?? null;
  const activeRole = active ? (ROLE_LABELS[active.my_role ?? ""] ?? active.my_role) : null;

  return (
    <>
      <Menu.Root>
        <Menu.Trigger
          className="flex w-full items-center gap-2.5 rounded-lg border border-border bg-background px-2.5 py-2 text-left shadow-xs transition-colors outline-none hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 data-popup-open:bg-muted"
        >
          <span
            aria-hidden="true"
            className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground"
          >
            {(active ? orgName(active) : "?").charAt(0).toUpperCase()}
          </span>
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-sm font-semibold text-foreground">
              {active ? orgName(active) : "Sin organización"}
            </span>
            <span className="truncate text-xs text-muted-foreground">
              {activeRole ?? "Crea una para empezar"}
            </span>
          </span>
          <ChevronsUpDown className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        </Menu.Trigger>

        <Menu.Portal>
          <Menu.Positioner sideOffset={6} align="start" className="z-40">
            <Menu.Popup className="w-(--anchor-width) min-w-56 rounded-lg border border-border bg-popover p-1 text-popover-foreground shadow-lg outline-none">
              {organizations.length > 0 ? (
                <Menu.RadioGroup value={activeSlug ?? ""} onValueChange={(slug) => onSelect(slug)}>
                  {organizations.map((org) => (
                    <Menu.RadioItem
                      key={org.slug}
                      value={org.slug}
                      closeOnClick
                      className={ITEM_CLASS}
                    >
                      <span className="flex min-w-0 flex-1 flex-col">
                        <span className="truncate font-medium">{orgName(org)}</span>
                        <span className="truncate text-xs text-muted-foreground">
                          {ROLE_LABELS[org.my_role ?? ""] ?? org.my_role}
                        </span>
                      </span>
                      <Menu.RadioItemIndicator>
                        <Check className="size-4 text-primary" aria-hidden="true" />
                      </Menu.RadioItemIndicator>
                    </Menu.RadioItem>
                  ))}
                </Menu.RadioGroup>
              ) : null}
              {organizations.length > 0 ? (
                <Menu.Separator className="my-1 h-px bg-border" />
              ) : null}
              <Menu.Item className={ITEM_CLASS} onClick={() => setCreateOpen(true)}>
                <Plus className="size-4 text-muted-foreground" aria-hidden="true" />
                Crear organización
              </Menu.Item>
            </Menu.Popup>
          </Menu.Positioner>
        </Menu.Portal>
      </Menu.Root>

      <CreateOrgDialog open={createOpen} onOpenChange={setCreateOpen} onCreate={onCreate} />
    </>
  );
}
