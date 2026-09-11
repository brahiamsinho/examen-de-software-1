"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { requestPasswordReset } from "@/lib/auth";

const GENERIC_CONFIRMATION =
  "Si esa cuenta existe, enviamos un correo con instrucciones para restablecer tu contraseña.";

/**
 * `/forgot-password` screen (web-account-recovery spec § "Forgot-Password
 * Request Screen"). Always renders the same generic confirmation, whatever
 * the backend response is — even a rejected call — mirroring the backend's
 * own anti-enumeration contract (password-reset spec DD4): the frontend
 * must not reintroduce an oracle the backend deliberately closed.
 */
export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await requestPasswordReset({ email });
    } catch {
      // Intentionally ignored: the confirmation below never differentiates.
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  }

  if (submitted) {
    return (
      <p data-testid="forgot-password-confirmation" role="status" className="text-sm">
        {GENERIC_CONFIRMATION}
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="forgot-password-email" className="text-sm font-medium">
          Correo electrónico
        </label>
        <Input
          id="forgot-password-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </div>

      <Button type="submit" disabled={submitting}>
        Enviar instrucciones
      </Button>
    </form>
  );
}
