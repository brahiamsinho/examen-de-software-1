/**
 * Pure presentational banner (spec `web-organization-workspace` §
 * Zero-Organization Empty State / proposal Q1). A zero-membership visitor
 * still reaches `/dashboard`, which renders this prompt alongside
 * `CreateOrgForm` instead of redirecting into a blocking onboarding flow.
 */
export function OrgEmptyState() {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-dashed border-border p-6 text-center">
      <h2 className="text-lg font-semibold">Crea tu primera organización</h2>
      <p className="text-sm text-muted-foreground">
        Aún no perteneces a ninguna organización. Crea una para empezar a modelar.
      </p>
    </div>
  );
}
