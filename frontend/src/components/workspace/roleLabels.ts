// Matches proposal.md Q2's established role-label convention ("Propietario
// / Editor / Lector"), not an ad hoc translation. Shared by `OrgSwitcher`
// and `OrgPicker` (design.md DV3) so the translation table never drifts.
export const ROLE_LABELS: Record<string, string> = {
  OWNER: "Propietario",
  EDITOR: "Editor",
  VIEWER: "Lector",
};
