import { Suspense } from "react";

import { VerifyEmailForm } from "@/components/auth/VerifyEmailForm";

/**
 * `VerifyEmailForm` calls `useSearchParams()` to read `token`. Per Next's
 * `useSearchParams` docs, a static page that calls it from a Client
 * Component must be wrapped in a `Suspense` boundary or the production
 * build fails with "Missing Suspense boundary with useSearchParams"
 * (matches `(auth)/login/page.tsx`'s precedent).
 */
export default function VerifyEmailPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Verificar correo electrónico</h1>
      <Suspense fallback={null}>
        <VerifyEmailForm />
      </Suspense>
    </div>
  );
}
