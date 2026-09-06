import { SessionGuard } from "@/components/auth/SessionGuard";
import { AppTopbar } from "@/components/workspace/AppTopbar";

/**
 * Server Component; the guard lives only here (design.md DD3/DD4). Under
 * D1 there is no server session, so every `(app)` page renders only a
 * static shell — protected data arrives via client hooks once the guard
 * resolves to `authenticated`.
 *
 * `<AppTopbar/>` (Phase 6, PR3) is a Client Component authored directly
 * here — no "children as prop" indirection needed for it, that trick is
 * only required for `{children}` itself (arbitrary Server-rendered route
 * content passed through the `SessionGuard` client boundary, DD3).
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionGuard>
      <AppTopbar />
      {children}
    </SessionGuard>
  );
}
