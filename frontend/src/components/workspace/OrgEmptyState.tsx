import type { ReactNode } from "react";

/**
 * Pure presentational banner (spec `web-organization-workspace` §
 * Zero-Organization Empty State / proposal Q1). A zero-membership visitor
 * still reaches `/dashboard`, which renders this prompt instead of
 * redirecting into a blocking onboarding flow. The container passes the
 * "Crear organización" control as `children`, so the creation form opens in
 * a dialog rather than sitting inline on the page.
 */
export function OrgEmptyState({ children }: { children?: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-dashed border-border px-6 py-14 text-center">
      <h2 className="font-heading text-lg font-semibold">Crea tu primera organización</h2>
      <p className="text-sm text-muted-foreground">
        Aún no perteneces a ninguna organización. Crea una para empezar a modelar.
      </p>
      {children ? <div className="mt-2 flex justify-center">{children}</div> : null}
    </div>
  );
}
