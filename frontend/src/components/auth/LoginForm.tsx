"use client";

import { useSetAtom } from "jotai";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { isSafeNext } from "@/lib/next-path";
import { login } from "@/lib/auth";
import { listOrganizations } from "@/lib/organizations";
import { sessionAtom } from "@/state/session";
import { useSetActiveOrg } from "@/state/organizations";

/**
 * On success writes the returned user directly to `sessionAtom` instead of
 * forcing a redundant `fetchMe()` round trip. On failure a single generic
 * message is shown regardless of `ApiError.detail` — spec requires no
 * field-level leakage of which field was wrong (web-session § Login and
 * Logout).
 *
 * Post-login destination (design.md DD3): a precedence-winning `next` wins
 * unconditionally; otherwise the caller's organizations are resolved via
 * `listOrganizations()` directly — never `useOrganizations()`, whose mount
 * effect would fire an anonymous fetch on this page — and the destination
 * branches 0 → `/dashboard` (unchanged), 1 → set active + `/dashboard`,
 * 2+ → `/select-organization`. A post-login org-fetch failure degrades to
 * `/dashboard` without reusing the login `catch` (login already succeeded).
 */
export function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setSession = useSetAtom(sessionAtom);
  const setActiveOrg = useSetActiveOrg();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const user = await login({ email, password });
      setSession({ status: "authenticated", user });

      const rawNext = searchParams.get("next");
      if (isSafeNext(rawNext)) {
        router.replace(rawNext);
        return;
      }

      let organizations;
      try {
        organizations = await listOrganizations();
      } catch {
        router.replace("/dashboard");
        return;
      }

      if (organizations.length === 1) {
        setActiveOrg(organizations[0]!.slug);
        router.replace("/dashboard");
        return;
      }
      if (organizations.length >= 2) {
        router.replace("/select-organization");
        return;
      }
      router.replace("/dashboard");
    } catch {
      setError("No pudimos iniciar sesión. Verifica tus datos e intenta de nuevo.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label htmlFor="login-email" className="text-sm font-medium">
          Correo electrónico
        </label>
        <Input
          id="login-email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="login-password" className="text-sm font-medium">
          Contraseña
        </label>
        <PasswordInput
          id="login-password"
          autoComplete="current-password"
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
        Iniciar sesión
      </Button>
    </form>
  );
}
