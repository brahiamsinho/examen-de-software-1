import Link from "next/link";
import { Suspense } from "react";

import { LoginForm } from "@/components/auth/LoginForm";

/**
 * `LoginForm` calls `useSearchParams()` to read `next`. Per Next's
 * `useSearchParams` docs, a static page that calls it from a Client
 * Component must be wrapped in a `Suspense` boundary or the production
 * build fails with "Missing Suspense boundary with useSearchParams" — this
 * was not called out in design.md and surfaced only from the doc gate read
 * (frontend/AGENTS.md).
 */
export default function LoginPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Iniciar sesión</h1>
      <Suspense fallback={null}>
        <LoginForm />
      </Suspense>
      <p className="text-center text-sm text-muted-foreground">
        ¿No tenés cuenta?{" "}
        <Link href="/register" className="font-medium text-primary hover:underline">
          Registrate
        </Link>
      </p>
      <p className="text-center text-sm text-muted-foreground">
        <Link href="/forgot-password" className="font-medium text-primary hover:underline">
          ¿Olvidaste tu contraseña?
        </Link>
      </p>
      {process.env.NODE_ENV === "development" ? <DemoCredentials /> : null}
    </div>
  );
}

/**
 * Dev-only convenience: `next dev` always sets `NODE_ENV=development`, so
 * this is stripped from any production build without needing a dedicated
 * env flag. Values must stay in sync with `seed_demo` (backend/apps/organizations/management/commands/seed_demo.py).
 */
function DemoCredentials() {
  return (
    <div className="rounded-md border border-border bg-muted/50 p-3 text-xs text-muted-foreground">
      <p className="font-medium text-foreground">Credenciales de prueba (desarrollo)</p>
      <ul className="mt-1.5 flex flex-col gap-0.5">
        <li>owner@demo.com / DemoPass123!</li>
        <li>editor@demo.com / DemoPass123!</li>
        <li>viewer@demo.com / DemoPass123!</li>
      </ul>
    </div>
  );
}
