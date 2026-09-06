import { SessionGuard } from "@/components/auth/SessionGuard";

/**
 * Server Component; the guard lives only here (design.md DD3/DD4). Under
 * D1 there is no server session, so every `(app)` page renders only a
 * static shell — protected data arrives via client hooks once the guard
 * resolves to `authenticated`.
 *
 * `<AppTopbar/>` is added inside `<SessionGuard>` when Phase 6 (org panel,
 * PR3) lands — not part of this batch.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return <SessionGuard>{children}</SessionGuard>;
}
