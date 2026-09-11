import Link from "next/link";

import { ForgotPasswordForm } from "@/components/auth/ForgotPasswordForm";

/**
 * `ForgotPasswordForm` does not call `useSearchParams()`, so no `Suspense`
 * boundary is required here (matches `(auth)/register/page.tsx`'s
 * precedent — `Suspense` is only needed where `useSearchParams` is
 * actually called, see `(auth)/login/page.tsx`'s docblock).
 */
export default function ForgotPasswordPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold">Recuperar contraseña</h1>
      <ForgotPasswordForm />
      <p className="text-center text-sm text-muted-foreground">
        <Link href="/login" className="font-medium text-primary hover:underline">
          Volver a iniciar sesión
        </Link>
      </p>
    </div>
  );
}
