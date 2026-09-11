"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { verifyEmail } from "@/lib/auth";

/**
 * `/verify-email` screen (web-account-recovery spec § "Verify-Email
 * Screen"). Reads `token` from `searchParams` and auto-submits it exactly
 * once; falls back to a manual paste-token field when the param is absent.
 * On success redirects via `router.replace()` to a fixed literal path —
 * never a caller-controlled destination (design.md threat matrix: open
 * redirect). The token is never written back to the URL or resubmitted
 * after the initial POST (token-in-logs/Referer threat-matrix row).
 */
export function VerifyEmailForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tokenFromLink = searchParams.get("token");

  const [manualToken, setManualToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const autoSubmitted = useRef(false);

  async function submit(token: string) {
    setError(null);
    setSubmitting(true);
    try {
      await verifyEmail({ token });
      router.replace("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.");
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (!tokenFromLink || autoSubmitted.current) return;
    autoSubmitted.current = true;
    void submit(tokenFromLink);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tokenFromLink]);

  if (tokenFromLink) {
    return error ? (
      <p role="alert" className="text-sm text-destructive">
        {error}
      </p>
    ) : (
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
        Verificando tu correo…
      </p>
    );
  }

  function handleManualSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit(manualToken);
  }

  return (
    <form onSubmit={handleManualSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="verify-token" className="text-sm font-medium">
          Token de verificación
        </label>
        <Input
          id="verify-token"
          type="text"
          value={manualToken}
          onChange={(event) => setManualToken(event.target.value)}
          required
        />
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Button type="submit" disabled={submitting}>
        Verificar
      </Button>
    </form>
  );
}
