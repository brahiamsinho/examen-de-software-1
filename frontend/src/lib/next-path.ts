/**
 * Predicate gate for the `next` query param used for post-login redirects
 * (design.md DD3, DV2). Only a single-leading-slash relative path is safe —
 * an absolute URL, a protocol-relative value (`//evil.com`), or a
 * `javascript:` URI is rejected. Next.js's `useRouter` docs warn that
 * unsanitized redirect targets passed to `push`/`replace` are an
 * open-redirect vector. Unlike `safe()`, this distinguishes "absent/invalid"
 * from "a real deep-link", which `LoginForm`'s precedence rule needs.
 */
export function isSafeNext(next: string | null | undefined): next is string {
  return typeof next === "string" && /^\/(?!\/)/.test(next);
}

/**
 * Sanitizes the `next` query param, falling back to `/dashboard` for
 * anything `isSafeNext` rejects. Byte-identical behavior to the pre-DV2
 * implementation.
 */
export function safe(next: string | null | undefined): string {
  return isSafeNext(next) ? next : "/dashboard";
}
