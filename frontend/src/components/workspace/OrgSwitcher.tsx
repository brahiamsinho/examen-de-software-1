import type { Organization } from "@/lib/organizations";

// Matches proposal.md Q2's established role-label convention ("Propietario
// / Editor / Lector"), not an ad hoc translation.
const ROLE_LABELS: Record<string, string> = {
  OWNER: "Propietario",
  EDITOR: "Editor",
  VIEWER: "Lector",
};

type OrgSwitcherProps = {
  organizations: Organization[];
  activeSlug: string | null;
  onSelect: (slug: string) => void;
};

/**
 * Presentational (design.md "components/workspace ... presentational, no
 * fetch"): receives state from its container (`AppTopbar`, which owns the
 * single `useOrganizations()` call) instead of fetching independently — this
 * also avoids a second `listOrganizations()` request from a sibling hook
 * instance.
 */
export function OrgSwitcher({ organizations, activeSlug, onSelect }: OrgSwitcherProps) {
  if (organizations.length === 0) {
    return null;
  }

  return (
    <ul className="flex items-center gap-2" aria-label="Organizaciones">
      {organizations.map((org) => (
        <li key={org.slug}>
          <button
            type="button"
            aria-pressed={org.slug === activeSlug}
            onClick={() => onSelect(org.slug)}
            className="flex flex-col items-start rounded-md px-2 py-1 text-left text-sm aria-pressed:bg-muted"
          >
            <span className="font-medium">{org.name}</span>
            <span className="text-xs text-muted-foreground">
              {ROLE_LABELS[org.my_role ?? ""] ?? org.my_role}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
