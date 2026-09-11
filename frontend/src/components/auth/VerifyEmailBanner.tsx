"use client";

import { X } from "lucide-react";
import { useAtom, useAtomValue } from "jotai";

import { Button } from "@/components/ui/button";
import { sessionAtom, verifyBannerDismissedAtom } from "@/state/session";

/**
 * Dismissible reminder for an unverified authenticated user
 * (web-account-recovery spec § "Dismissible Verify-Email Banner on
 * Dashboard"). Renders `null` for a verified user, an anonymous/loading
 * session, or once dismissed this session (design.md DD6).
 *
 * Self-contained: reads `sessionAtom` directly rather than receiving the
 * user as a prop, matching `OrgSwitcher`/`AppTopbar`'s existing
 * self-fetching convention — the dashboard mounts it with no wiring.
 */
export function VerifyEmailBanner() {
  const session = useAtomValue(sessionAtom);
  const [dismissed, setDismissed] = useAtom(verifyBannerDismissedAtom);

  if (session.status !== "authenticated") return null;
  if (session.user.is_verified) return null;
  if (dismissed) return null;

  return (
    <div
      role="region"
      aria-label="Recordatorio de verificación de correo"
      className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted/50 p-3 text-sm"
    >
      <p className="text-foreground">
        Verificá tu correo electrónico para asegurar el acceso a tu cuenta.
      </p>
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="size-11 shrink-0"
        aria-label="Descartar recordatorio"
        onClick={() => setDismissed(true)}
      >
        <X />
      </Button>
    </div>
  );
}
