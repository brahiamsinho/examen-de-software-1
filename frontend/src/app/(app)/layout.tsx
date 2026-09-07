import { SessionGuard } from "@/components/auth/SessionGuard";
import { requireUser } from "@/lib/server-session";
import { AppTopbar } from "@/components/workspace/AppTopbar";

/**
 * Server Component; the guard lives only here (design.md DD3/DD4).
 * `await requireUser("/dashboard")` (ssr-protected-routes D2) validates the
 * session server-side, before any protected markup is ever emitted — an
 * anonymous or invalid-session request is redirected to `/login` here and
 * never reaches the `return` below. `SessionGuard` still runs afterwards on
 * the client: it owns the loading skeleton, the error/retry UI, and
 * mid-session expiry, none of which this navigation-time check can see (D4).
 *
 * `<AppTopbar/>` (Phase 6, PR3) is a Client Component authored directly
 * here — no "children as prop" indirection needed for it, that trick is
 * only required for `{children}` itself (arbitrary Server-rendered route
 * content passed through the `SessionGuard` client boundary, DD3).
 */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  await requireUser("/dashboard");

  return (
    <SessionGuard>
      <AppTopbar />
      {children}
    </SessionGuard>
  );
}
