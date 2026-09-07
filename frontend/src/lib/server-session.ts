import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import type { User } from "@/lib/auth";
import { internalApiUrl } from "@/lib/env";
import { safe } from "@/lib/next-path";

/**
 * Server-side half of route protection (proposal D2). The client-side
 * `SessionGuard` is NOT replaced by this (D4): it owns the loading skeleton,
 * the error/retry UI, and mid-session expiry, none of which a navigation-time
 * server check can see.
 *
 * Deliberately does NOT reuse `apiFetch`: that module is browser-only by
 * construction (`document.cookie`, `credentials: "include"`), and its docblock
 * guarantees that nothing below it knows about cookies.
 *
 * No CSRF header: `/api/auth/me` is a GET and Django's `CsrfViewMiddleware`
 * only enforces unsafe methods (D2).
 */
export const getServerUser = cache(async (): Promise<User | null> => {
  const cookieHeader = (await cookies()).toString();

  const response = await fetch(new URL("/api/auth/me", internalApiUrl), {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });

  if (response.ok) return (await response.json()) as User;
  if (response.status === 401 || response.status === 403) return null;

  throw new Error(`GET /api/auth/me failed with status ${response.status}`);
});

/**
 * `nextPath` is the caller's own route (DV1 — Next 16 has no server-side
 * pathname API). Returns `null` ONLY when session validity could not be
 * determined; an anonymous caller never returns at all.
 */
export async function requireUser(nextPath: string): Promise<User | null> {
  let user: User | null;

  try {
    user = await getServerUser();
  } catch {
    // Outage ≠ logout (D2, web-session scenario 3). Render normally and let
    // SessionGuard's existing error/retry state own the failure.
    return null;
  }

  // Outside the try/catch on purpose: `redirect` works by throwing NEXT_REDIRECT.
  if (user === null) redirect(`/login?next=${encodeURIComponent(safe(nextPath))}`);

  return user;
}
