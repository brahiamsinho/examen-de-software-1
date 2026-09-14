import type { Organization } from "@/lib/organizations";
import { ROLE_LABELS } from "@/components/workspace/roleLabels";

type OrgSwitcherProps = {
  organizations: Organization[];
  activeSlug: string | null;
  onSelect: (slug: string) => void;
};

/**
 * Presentational (design.md "components/workspace ... presentational, no
 * fetch"): receives state from its container (`AppSidebar`, which owns the
 * single `useOrganizations()` call) instead of fetching independently — this
 * also avoids a second `listOrganizations()` request from a sibling hook
 * instance. Renders as a vertical list (sidebar redesign) with the active
 * org's own `aria-pressed` styling the row's background and, via `group`,
 * its child text color.
 */
export function OrgSwitcher({ organizations, activeSlug, onSelect }: OrgSwitcherProps) {
  if (organizations.length === 0) {
    return null;
  }

  return (
    <ul className="flex flex-col gap-0.5" aria-label="Organizaciones">
      {organizations.map((org) => (
        <li key={org.slug}>
          <button
            type="button"
            aria-pressed={org.slug === activeSlug}
            onClick={() => onSelect(org.slug)}
            className="group flex w-full flex-col items-start rounded-md px-2.5 py-1.5 text-left text-sm transition-colors hover:bg-background aria-pressed:bg-accent aria-pressed:hover:bg-accent"
          >
            <span className="font-medium text-foreground group-aria-pressed:text-accent-foreground">
              {org.name}
            </span>
            <span className="text-xs text-muted-foreground group-aria-pressed:text-accent-foreground/80">
              {ROLE_LABELS[org.my_role ?? ""] ?? org.my_role}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
