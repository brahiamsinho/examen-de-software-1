import { Suspense } from "react";

import { ResetPasswordForm } from "@/components/auth/ResetPasswordForm";

/**
 * `ResetPasswordForm` calls `useSearchParams()` to read `token`, so this
 * page needs the same `Suspense` boundary as `(auth)/login/page.tsx` and
 * `(auth)/verify-email/page.tsx`.
 */
export default function ResetPasswordPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Restablecer contraseña</h1>
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
