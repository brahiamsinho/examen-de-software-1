import type { Organization } from "@/lib/organizations";
import { ROLE_LABELS } from "@/components/workspace/roleLabels";

type OrgPickerProps = {
  organizations: Organization[];
  onSelect: (slug: string) => void;
};

/**
 * Presentational one-time picker (design.md DD4, web-organization-workspace
 * § Post-Login Organization Picker). No `activeSlug`/`aria-pressed`: nothing
 * is active yet, so a "current" affordance would be a lie — this is what
 * makes it a distinct component from `OrgSwitcher` rather than an overload
 * of it. Vertical full-width buttons instead of the switcher's horizontal
 * inline row.
 */
export function OrgPicker({ organizations, onSelect }: OrgPickerProps) {
  return (
    <ul className="flex flex-col gap-2" aria-label="Selecciona una organización">
      {organizations.map((org) => (
        <li key={org.slug}>
          <button
            type="button"
            onClick={() => onSelect(org.slug)}
            className="flex w-full flex-col items-start rounded-md border border-border px-4 py-3 text-left text-sm hover:bg-muted"
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
