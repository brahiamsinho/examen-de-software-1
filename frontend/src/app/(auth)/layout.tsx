/**
 * Server Component, no guard (route groups are for auth screens only —
 * anonymous visitors must reach `/login` and `/register`). Types `children`
 * explicitly rather than via the generated `LayoutProps` helper: route
 * groups don't appear in the URL, so `.next/types/routes.d.ts` keys both
 * `(auth)/layout.tsx` and `(app)/layout.tsx` on `"/"` — the same key
 * `app/layout.tsx` already uses (design.md DD4).
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-sm">
        {children}
      </div>
    </div>
  );
}
