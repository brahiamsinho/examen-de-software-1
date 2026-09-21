import { SessionGuard } from "@/components/auth/SessionGuard";
import { requireUser } from "@/lib/server-session";
import { AppSidebar } from "@/components/workspace/AppSidebar";

/**
 * Server Component; the guard lives only here (design.md DD3/DD4).
 * `await requireUser("/dashboard")` (ssr-protected-routes D2) validates the
 * session server-side, before any protected markup is ever emitted — an
 * anonymous or invalid-session request is redirected to `/login` here and
 * never reaches the `return` below. `SessionGuard` still runs afterwards on
 * the client: it owns the loading skeleton, the error/retry UI, and
 * mid-session expiry, none of which this navigation-time check can see (D4).
 * Its loading/error states render standalone (no sidebar) — unchanged
 * behavior from before this redesign, since the sidebar (like the former
 * topbar) only ever rendered on the success path, inside `{children}`'s
 * sibling slot.
 *
 * `<AppSidebar/>` (persistent left sidebar, replacing the prior horizontal
 * `AppTopbar`) is a Client Component authored directly here — no "children
 * as prop" indirection needed for it, that trick is only required for
 * `{children}` itself (arbitrary Server-rendered route content passed
 * through the `SessionGuard` client boundary, DD3).
 */
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  await requireUser("/dashboard");

  return (
    <SessionGuard>
      <div className="flex min-h-screen flex-col md:flex-row">
        <AppSidebar />
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </SessionGuard>
  );
}
