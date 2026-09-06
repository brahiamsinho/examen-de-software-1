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
    </div>
  );
}
