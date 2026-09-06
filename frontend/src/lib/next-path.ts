/**
 * Sanitizes the `next` query param used for post-login redirects
 * (design.md DD5). Only a single-leading-slash relative path is honored —
 * an absolute or protocol-relative value (`//evil.com`, `https://evil.com`)
 * falls back to `/dashboard`. Next.js's `useRouter` docs warn that
 * unsanitized redirect targets passed to `push`/`replace` are an
 * open-redirect vector.
 */
export function safe(next: string | null | undefined): string {
  return next && /^\/(?!\/)/.test(next) ? next : "/dashboard";
}
