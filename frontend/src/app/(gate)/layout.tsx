import { SessionGuard } from "@/components/auth/SessionGuard";

/**
 * `(gate)` route group (design.md DD4, DV4): a one-time post-login gate.
 * `SessionGuard` + `(auth)`'s centered-card shell, no topbar — reusing
 * `(app)` would double-render the org list via `AppTopbar` → `OrgSwitcher`
 * (a dead-end trap), and `(auth)` has no session guard at all. Types
 * `children` explicitly rather than via the generated `LayoutProps` helper,
 * for the same reason `(auth)`/`(app)` do: route groups don't appear in the
 * URL, so `.next/types/routes.d.ts` keys every root-level group layout on
 * `"/"`.
 */
export default function GateLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionGuard>
      <div className="flex min-h-svh items-center justify-center bg-background px-4">
        <div className="w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-sm">
          {children}
        </div>
      </div>
    </SessionGuard>
  );
}
