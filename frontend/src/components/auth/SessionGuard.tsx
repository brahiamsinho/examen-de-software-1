"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { safe } from "@/lib/next-path";
import { useSession } from "@/state/session";

/**
 * Client Component receiving server `children` as a prop (design.md DD3).
 * Per Next's "Interleaving Server and Client Components" docs, `children`
 * is rendered on the server ahead of time and included in the RSC payload
 * even while this guard chooses not to display it — the guard only ever
 * decides whether that pre-rendered markup is shown, never whether it
 * exists on the server.
 */
export function SessionGuard({ children }: { children: ReactNode }) {
  const session = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (session.status === "anonymous") {
      router.replace(`/login?next=${encodeURIComponent(safe(pathname))}`);
    }
  }, [session.status, pathname, router]);

  if (session.status === "loading") {
    return (
      <div role="status" aria-live="polite" className="p-6 text-sm text-muted-foreground">
        Cargando…
      </div>
    );
  }

  if (session.status === "anonymous") {
    // Redirect is in flight (effect above); render nothing while it lands.
    return null;
  }

  if (session.status === "error") {
    return (
      <div role="alert" className="flex flex-col items-center gap-3 p-6 text-center">
        <p>No pudimos verificar tu sesión. Intenta de nuevo.</p>
        <button
          type="button"
          onClick={() => router.refresh()}
          className="text-sm font-semibold underline"
        >
          Reintentar
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
