"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/lib/api";
import { confirmPasswordReset } from "@/lib/auth";

/**
 * `/reset-password` screen (web-account-recovery spec § "Reset-Password
 * Confirm Screen"). Reads `token` from `searchParams`, collects a new
 * password, and submits both. On success redirects via `router.replace()`
 * to a fixed literal path — never a caller-controlled destination
 * (design.md threat matrix: open redirect).
 */
export function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await confirmPasswordReset({ token, password });
      router.replace("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="reset-password-new" className="text-sm font-medium">
          Nueva contraseña
        </label>
        <PasswordInput
          id="reset-password-new"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          required
        />
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Button type="submit" disabled={submitting}>
        Restablecer contraseña
      </Button>
    </form>
  );
}
