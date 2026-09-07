"use client";

import { useSetAtom } from "jotai";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError } from "@/lib/api";
import { register } from "@/lib/auth";
import { listOrganizations } from "@/lib/organizations";
import { sessionAtom } from "@/state/session";
import { useSetActiveOrg } from "@/state/organizations";

/**
 * On success writes the returned user directly to `sessionAtom` and
 * redirects to `/dashboard` (no `next` resolution for registration, per
 * spec's Registration requirement). On a duplicate email the backend's
 * `detail` is shown verbatim, unlike LoginForm's deliberately generic
 * message.
 *
 * The backend provisions exactly one organization per registration (D1);
 * since D2 forbids org data in `UserOut`, the newly provisioned org is
 * adopted via the `GET /api/orgs` response (design.md DD6) before the
 * redirect. That fetch sits outside this catch — a failed org fetch must
 * never surface as a bogus "email already registered" message; the
 * dashboard re-fetches on mount regardless.
 */
export function RegisterForm() {
  const router = useRouter();
  const setSession = useSetAtom(sessionAtom);
  const setActiveOrg = useSetActiveOrg();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await register({ email, password, full_name: fullName || undefined });
      setSession({ status: "authenticated", user });

      try {
        const organizations = await listOrganizations();
        if (organizations.length > 0) setActiveOrg(organizations[0]!.slug);
      } catch {
        // non-fatal: the dashboard re-fetches organizations on mount
      }

      router.replace("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="register-full-name" className="text-sm font-medium">
          Nombre completo
        </label>
        <Input
          id="register-full-name"
          type="text"
          autoComplete="name"
          value={fullName}
          onChange={(event) => setFullName(event.target.value)}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="register-email" className="text-sm font-medium">
          Correo electrónico
        </label>
        <Input
          id="register-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="register-password" className="text-sm font-medium">
          Contraseña
        </label>
        <PasswordInput
          id="register-password"
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
        Registrarse
      </Button>
    </form>
  );
}
