# Design: Server-Enforced Protected Routes

> Size note: this document exceeds the default 800-word design budget, following the precedent set by
> `archive/2026-09-06-tenant-aware-registration-login/design.md` and
> `archive/2026-09-06-frontend-auth-integration/design.md` — this project's design artifacts carry a
> complete file architecture table and exact code shapes.

## Technical Approach

One new module holds all the logic; the two layouts each gain one `await` line. Nothing else moves.

```
GET /dashboard  (no cookie, no JS)
        │
        ▼
app/layout.tsx            sync, no Suspense, no loading.tsx  ──▶ nothing flushed yet
        │
        ▼
app/(app)/layout.tsx      async
        │  await requireUser("/dashboard")
        │        │
        │        ▼
        │   lib/server-session.ts
        │        getServerUser()  = cache(async () => …)
        │           cookies().toString()  ──cookie header──▶  GET {internalApiUrl}/api/auth/me
        │                                                      cache: "no-store"
        │           200 → User      401/403 → null      else/network → throw
        │        │
        │        ├─ null   → redirect("/login?next=%2Fdashboard")   ──▶ 307, empty body ✔
        │        ├─ throw  → caught → return null → render normally ──▶ client SessionGuard error/retry
        │        └─ User   → return
        ▼
   <SessionGuard><AppTopbar/>{children}</SessionGuard>      ← byte-identical to today (D4)
```

The 307 is real, not a client meta-refresh: `redirect()` emits a meta tag only in a streaming context
(`node_modules/next/dist/docs/01-app/03-api-reference/04-functions/redirect.md` L12), and the root
layout is synchronous with no `<Suspense>` and no `loading.tsx` anywhere under `src/app/`.

**Correction (found during `sdd-apply`'s mandatory manual verification, confirmed independently at
`sdd-verify`)**: "nothing has flushed" is not quite right — Next.js 16.3.3 always streams a small
inert `<html id="__next_error__">` shell alongside the redirect (script tags, an internal RSC
route-tree description, a `NEXT_REDIRECT` digest/stack trace), even with zero `<Suspense>` boundaries.
The 307 status and `Location` header are unaffected, and the shell carries no real dashboard/org/user
data — only Next's own internal scaffolding — so the property this change actually needs ("no
protected content reaches an anonymous request") still holds. DD8's Step 3 below is corrected to
match.

---

## Architecture Decisions

### DD1 — `server-session.ts`: exact module contents

Reuses the existing `User` type from `lib/auth.ts` (verified: `id`/`email`/`full_name`) rather than
redeclaring it — a duplicate would drift from `UserOut`.

```ts
// frontend/src/lib/server-session.ts
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import type { User } from "@/lib/auth";
import { internalApiUrl } from "@/lib/env";
import { safe } from "@/lib/next-path";

/**
 * Server-side half of route protection (proposal D2). The client-side
 * `SessionGuard` is NOT replaced by this (D4): it owns the loading skeleton,
 * the error/retry UI, and mid-session expiry, none of which a navigation-time
 * server check can see.
 *
 * Deliberately does NOT reuse `apiFetch`: that module is browser-only by
 * construction (`document.cookie`, `credentials: "include"`), and its docblock
 * guarantees that nothing below it knows about cookies.
 *
 * No CSRF header: `/api/auth/me` is a GET and Django's `CsrfViewMiddleware`
 * only enforces unsafe methods (D2).
 */
export const getServerUser = cache(async (): Promise<User | null> => {
  const cookieHeader = (await cookies()).toString();

  const response = await fetch(new URL("/api/auth/me", internalApiUrl), {
    headers: cookieHeader ? { cookie: cookieHeader } : {},
    cache: "no-store",
  });

  if (response.ok) return (await response.json()) as User;
  if (response.status === 401 || response.status === 403) return null;

  throw new Error(`GET /api/auth/me failed with status ${response.status}`);
});

/**
 * `nextPath` is the caller's own route (DV1 — Next 16 has no server-side
 * pathname API). Returns `null` ONLY when session validity could not be
 * determined; an anonymous caller never returns at all.
 */
export async function requireUser(nextPath: string): Promise<User | null> {
  let user: User | null;

  try {
    user = await getServerUser();
  } catch {
    // Outage ≠ logout (D2, web-session scenario 3). Render normally and let
    // SessionGuard's existing error/retry state own the failure.
    return null;
  }

  // Outside the try/catch on purpose: `redirect` works by throwing NEXT_REDIRECT.
  if (user === null) redirect(`/login?next=${encodeURIComponent(safe(nextPath))}`);

  return user;
}
```

`(await cookies()).toString()` forwards the **whole jar verbatim** (`cookies.md` L41), so `sessionid`
plus anything else Django set travels unmodified. `encodeURIComponent(safe(...))` is character-for-character
the same expression `SessionGuard.tsx` L24 already uses, so both layers produce the identical target.

### DD2 — The redirect target is an explicit argument, not a derived pathname

| Option | Tradeoff | Decision |
|---|---|---|
| Derive from `usePathname` | Client-only. `layout.md` L242: "To access the current pathname, you can read it inside a Client Component" | Rejected |
| Derive from `headers()` | No documented path header exists on a hard document GET. `next-url`/`Next-Router-State-Tree` are sent only by the client router on RSC navigations — absent in exactly the `curl` case this change exists for. `x-matched-path` is an internal adapter header (`next/dist/server/lib/server-ipc/utils.js` L70 filters it) | Rejected |
| Set `x-current-path` in `proxy.ts` | Next's own documented workaround, but D1 forbids `proxy.ts` | Rejected |
| **Required `nextPath: string` parameter** | Each group passes its canonical route literal. Required (no default) so a new route group cannot silently forget it | **Chosen** |

Exact today: `(app)` contains only `dashboard/`, `(gate)` only `select-organization/` (verified). If a
second route is ever added under `(app)`, an anonymous deep link redirects to `/login?next=%2Fdashboard`
instead of that route — degraded UX, never a protection hole, and `SessionGuard` still uses the real
`usePathname`. Tech debt #5.

### DD3 — `cache()` wraps `getServerUser`; memoization is untestable under Vitest, stated honestly

Wrapping at the export site (not inside `requireUser`) matches the `verifySession` shape Next's own
authentication guide prescribes. **Verified**: `node_modules/react/cjs/react.development.js` L917-921 —
the non-`react-server` build of `cache(fn)` is a plain pass-through with no memoization. Consequences,
both load-bearing:

- Tests need no cache reset between cases; every call reaches the stubbed `fetch`.
- The dedup itself has **no automated test** — it only exists under Next's `react-server` condition.
  Same honesty as D6's layout admission. Cost of being wrong is one extra intra-host call, not a
  correctness bug, so no mitigation is warranted.

`cache: "no-store"` is explicit anyway (D3): the value is keyed on a per-user cookie, so any
cross-request cache is a session-confusion bug.

### DD4 — No `server-only` package; `next/headers` is the guard

`server-only` is **not installed** (verified: absent from `node_modules/` and `package.json`), and the
proposal commits to "no new package dependency". Importing `next/headers` already makes Next fail the
build if this module is ever pulled into a Client Component, which is the same protection for free.

### DD5 — `env.ts`: private reader + exported const, matching the file's existing convention

Appended **after** `apiUrl` (it reads it as the fallback). Never `NEXT_PUBLIC_*` — this value must not
reach the browser bundle.

```ts
/**
 * Base URL the *Next.js server process* uses to reach the API. Inside the
 * frontend container `localhost` is the container itself, so a server-side
 * fetch to `apiUrl` would ECONNREFUSED; Compose sets INTERNAL_API_URL=
 * http://backend:8000. Falls back to `apiUrl` so bare `npm run dev` and
 * Vitest keep working unchanged.
 */
function readInternalApiUrl(): string {
  return process.env.INTERNAL_API_URL ?? apiUrl;
}

export const internalApiUrl = readInternalApiUrl();
```

Unlike `readApiUrl`, it never throws — an unset value is a valid, correct configuration.

### DD6 — Layout wiring: `async` + one `await`, JSX byte-identical

Both files: add `import { requireUser } from "@/lib/server-session";`, add `async`, insert the await as
the first statement, leave the entire `return (...)` block unchanged.

```tsx
export default async function AppLayout({ children }: { children: React.ReactNode }) {
  await requireUser("/dashboard");

  return ( /* unchanged: <SessionGuard><AppTopbar />{children}</SessionGuard> */ );
}
```

`(gate)/layout.tsx` is identical with `await requireUser("/select-organization");`.

**One non-JSX edit is mandatory**: `(app)/layout.tsx`'s docblock currently asserts *"Under D1 there is
no server session"* — that sentence becomes false and must be rewritten (DV4). `SessionGuard.tsx` and
`SessionGuard.test.tsx` keep a **zero-line diff** (D4/N8).

### DD7 — Test strategy: 15 RED cases across two files

Runner: `cd frontend && npm test -- --run`. `vitest.setup.ts` sets `NEXT_PUBLIC_API_URL` but **not**
`INTERNAL_API_URL`, so the fallback branch is the ambient default.

Mocking pattern follows `lib/__tests__/api.test.ts` (`vi.stubGlobal("fetch", …)` + real `Response`) and
`auth.test.ts` (`vi.mock` on a `@/lib/*` path), plus `vi.hoisted` holders so each case can vary inputs:

```ts
const nav = vi.hoisted(() => ({
  // The real `redirect` throws NEXT_REDIRECT. A silent mock would let execution
  // fall through to `return user`, masking a mis-ordered guard.
  redirect: vi.fn((url: string) => { throw new Error(`NEXT_REDIRECT:${url}`); }),
}));
vi.mock("next/navigation", () => nav);

const jar = vi.hoisted(() => ({ value: "" }));
vi.mock("next/headers", () => ({ cookies: async () => ({ toString: () => jar.value }) }));

const env = vi.hoisted(() => ({ apiUrl: "http://localhost:8000", internalApiUrl: "http://backend:8000" }));
vi.mock("@/lib/env", () => env);
```

`server-session.test.ts` (13): (1) forwards the whole jar verbatim as `cookie`; (2) sends no `cookie`
header when the jar is empty; (3) always sends `cache: "no-store"`; (4) targets `internalApiUrl`, not
`apiUrl`; (5) `200` → parsed `User`; (6) `401` → `null`; (7) `403` → `null`; (8) `500` → throws;
(9) `fetch` rejects → throws; (10) `requireUser` returns the user on `200`; (11) `requireUser` redirects
to `/login?next=%2Fdashboard` on `401`; (12) a hostile `nextPath` (`//evil.com`) is collapsed to
`%2Fdashboard` by `safe()`; (13) `requireUser` does **not** redirect when `getServerUser` throws and
returns `null`.

`env.test.ts` (2, new file — DV3): `internalApiUrl` equals `INTERNAL_API_URL` when set, and equals
`apiUrl` when unset. Requires `vi.stubEnv` + `vi.resetModules()` + `await import("@/lib/env")` because
the export is evaluated at import time.

### DD8 — Mandatory manual verification unit (proposal D6)

Layout wiring has no automated test, so this checklist is a **work unit for `sdd-tasks`**, not a note.
From the repo root, with `docker compose up -d --build` healthy and
`docker compose exec backend python manage.py seed_demo` run once:

| # | Command | Expected |
|---|---|---|
| 1 | `curl -s -o body.txt -w "%{http_code}\n" http://localhost:3000/dashboard` | `307` |
| 2 | `curl -sI http://localhost:3000/dashboard \| rg -i '^location:'` | `location: /login?next=%2Fdashboard` |
| 3 | Inspect `body.txt` for real content (not a literal `<html>` grep — corrected post-verification, see note below): `rg -i "dashboard-page\|organization\|AppTopbar\|SessionGuard\|Acme" body.txt` | no match — the body may legitimately contain Next's own `<html id="__next_error__">` redirect scaffolding (scripts, RSC route-tree strings, the `NEXT_REDIRECT` digest), just no real protected content |
| 4 | Repeat 1-3 with `-H "Cookie: sessionid=deadbeefdeadbeefdeadbeefdeadbeef"` | identical `307` (presence ≠ validity) |
| 5 | Repeat 1-3 for `/select-organization` | `307`, `next=%2Fselect-organization` |
| 6 | Log in with a `seed_demo` account into `jar.txt` against `localhost:8000`, then `curl -s -o body.txt -w "%{http_code}\n" -b jar.txt http://localhost:3000/dashboard` | `200`, `body.txt` contains `<html` |
| 7 | `curl -s -w "%{http_code}\n" -b jar.txt http://localhost:3000/select-organization` | `200` (picker's `<2`-orgs redirect stays client-side — D5) |
| 8 | `docker compose stop backend`, repeat 6, then `docker compose start backend` | **not** `307`; a rendered document — `SessionGuard` shows "No pudimos verificar tu sesión" client-side |

The `localhost:8000` → `localhost:3000` cookie hand-off in step 6 works because cookies ignore ports —
the exact assumption the proposal's cross-domain risk documents. If step 1 returns `200` with a
`<meta http-equiv="refresh">` instead of `307`, that is a **failure**, not an acceptable variant: it
means streaming began before the gate resolved and a document reached the client.

---

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/src/lib/server-session.ts` | **Create** | `getServerUser()` + `requireUser()` (DD1) |
| `frontend/src/lib/__tests__/server-session.test.ts` | **Create** | 13 cases (DD7) |
| `frontend/src/lib/__tests__/env.test.ts` | **Create** | 2 cases (DD7, DV3) |
| `frontend/src/lib/env.ts` | Modify | + `readInternalApiUrl` / `internalApiUrl` (DD5) |
| `frontend/src/app/(app)/layout.tsx` | Modify | `async` + `await requireUser("/dashboard")` + docblock (DD6) |
| `frontend/src/app/(gate)/layout.tsx` | Modify | `async` + `await requireUser("/select-organization")` (DD6) |
| `docker-compose.yml` | Modify | `frontend.environment: INTERNAL_API_URL: http://backend:8000` (takes precedence over `env_file`) |
| `frontend/env.local.example` | Modify | Commented `INTERNAL_API_URL` + cross-domain deployment precondition |
| `frontend/src/components/auth/SessionGuard.tsx` + its test | **Untouched** | D4 / N8 — zero-line diff is a success criterion |
| `frontend/src/lib/api.ts`, `lib/auth.ts`, `lib/next-path.ts` | **Untouched** | D2; `User` and `safe` are imported, not edited |
| `frontend/src/app/(app)/dashboard/page.tsx`, `(gate)/select-organization/page.tsx` | **Untouched** | N1, D5 |
| `backend/env.example` | Modify (config only, DV6) | `ALLOWED_HOSTS` gains `,backend`; discovered during manual verification |
| `backend/**` (app code) | **Untouched** | N2 — no Django app code, model, endpoint, schema, or migration change |
| `openspec/specs/web-session/spec.md` | Modify | D7 delta (already authored by `sdd-spec`) |
| `docs/ai/CURRENT_STATE.md`, `DECISIONS_LOG.md`, `README`, `ARCHITECTURE.md` | Modify | D1-D8 + cross-domain precondition |

---

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit (config) | `internalApiUrl` override / fallback | `vi.stubEnv` + `vi.resetModules()` + dynamic import |
| Unit (logic) | Status branching, cookie forwarding, `no-store`, target URL, redirect target, outage fall-through | Vitest + `vi.stubGlobal("fetch")`, `vi.mock` on `next/headers` / `next/navigation` (DD7) |
| Integration | None | The layouts hold one `await` each; asserting "the layout calls the helper" is a tautology (D6) |
| E2E | None | N6 — no Playwright harness. Replaced by DD8's manual unit |
| Regression | `SessionGuard.test.tsx`, `api.test.ts`, `auth.test.ts`, backend `pytest` | Must stay green **and unmodified** |

---

## Threat Matrix

This change adds a routing boundary (a server-issued redirect), so the matrix applies. The five
canonical rows are shell/VCS/PR-shaped and are all `N/A` here — no task or test is created for them.

| Boundary | Applicability | Design response | Planned RED test |
|---|---|---|---|
| Documentation-like paths | **N/A** — no file is classified or executed | — | — |
| Git repository selection | **N/A** — no VCS invocation | — | — |
| Commit state | **N/A** | — | — |
| Push state | **N/A** | — | — |
| PR commands | **N/A** — no PR automation | — | — |
| **Open redirect via the server-issued `next`** | **Applicable** — `requireUser` composes a redirect URL from a caller-supplied string | `safe()` (the same single source `SessionGuard` uses) collapses anything without a single leading slash to `/dashboard`; the result is `encodeURIComponent`-escaped | DD7 case 12: `requireUser("//evil.com")` must redirect to `/login?next=%2Fdashboard` |
| **Outage misread as logout** | **Applicable** — a failure mode that would mass-log-out every user | Non-`401`/`403` and network failures throw in `getServerUser` and are caught in `requireUser`, which renders instead of redirecting | DD7 cases 8, 9, 13 |
| **Cookie forwarding leaks to a third party** | **Applicable** — the whole jar is forwarded verbatim | The destination is `internalApiUrl`, a server-only const with no request-derived input; no user-controlled value reaches the URL | DD7 case 4 pins the target host |

---

## Migration / Rollout

**No migration required.** No model, schema, or migration file changes. Rollout is a plain deploy plus
one env var. `INTERNAL_API_URL` is additive with a fallback, so an un-updated environment keeps the old
(correct-for-localhost) behavior rather than breaking. The proposal's partial rollback stays coherent:
reverting only the two layouts restores today's behavior while the tested helper sits unused.

**Deployment precondition** (documented, not enforced): the browser must send the Django `sessionid`
cookie to the Next.js origin. True for localhost and shared-parent-domain deploys; **false** for a split
`app.x.com` / `api.y.com` deployment, where every authenticated user would be bounced to `/login`.

---

## Deviations

| # | Deviation | Justification |
|---|---|---|
| **DV1** | D2 writes `redirect("/login?next=<path>")`, implying the current path is derived; this design makes `nextPath` a **required parameter** of `requireUser` | Verified against the installed Next 16.3.3 docs: there is no server-side pathname API, and the only documented workaround sets a header in `proxy.ts`, which D1 forbids (DD2) |
| **DV2** | `requireUser` returns `Promise<User \| null>` and catches `getServerUser`'s throw, rather than propagating it | D2 says non-`401` failures "throw"; the `web-session` delta's third scenario says the request "falls through to render normally". Both hold only if the throw is raised at the data layer and absorbed at the gate. An uncaught throw would hit Next's error boundary — there is no `error.tsx` in this app — and produce a 500, contradicting the scenario |
| **DV3** | Adds `frontend/src/lib/__tests__/env.test.ts`, not listed in the proposal's Affected Areas | `internalApiUrl` is evaluated at import time, so the override/fallback branches cannot be exercised from `server-session.test.ts` (which mocks `@/lib/env` wholesale). The proposal makes that override a success criterion |
| **DV4** | The proposal says the layouts gain "one line each"; `(app)/layout.tsx` also needs a docblock rewrite | Its current text asserts *"Under D1 there is no server session, so every `(app)` page renders only a static shell"* — false after this change. Leaving a comment that contradicts the code is worse than a two-line diff |
| **DV5** | The spec delta counts differ from D7's "all four existing scenarios" — the live spec has three | Already identified by `sdd-spec` as a harmless miscount in the proposal. All pre-existing scenarios survive verbatim; no behavior is dropped |
| **DV6** | `backend/env.example` gains a documented `ALLOWED_HOSTS` addition (`,backend`), the only backend-side change | Discovered during `sdd-apply`'s mandatory manual verification: the frontend container's server-side fetch to `http://backend:8000` was rejected `400` by Django's `CommonMiddleware` until `backend` was added to `ALLOWED_HOSTS`. This is framework config, not application code — no model, schema, endpoint, or migration changed — so it satisfies N2's actual intent even though it makes the proposal's literal "`git diff --stat backend/` is empty" wording false. `sdd-verify` independently assessed this as COMPLIANT-as-is (a Docker-internal service name in `ALLOWED_HOSTS` is not internet-resolvable, so it weakens no real Host-header protection); proposal Success Criteria corrected accordingly |
| **DV7** | The Technical Approach's "nothing has flushed when the gate throws" claim and DD8 Step 3's literal `<html>` check were both wrong | Independently reproduced at both `sdd-apply` and `sdd-verify`: Next.js 16.3.3 always streams a small inert `<html id="__next_error__">` redirect shell, even synchronously. The response body was read in full at `sdd-verify` and confirmed to carry zero real dashboard/org/user data — only Next's own internal scaffolding. The underlying `web-session` spec scenario ("no protected markup") holds; only the literal grep-based proxy for that property was incorrect. Corrected in the Technical Approach note and DD8 Step 3 above |

---

## Open Questions

None blocking. Three accepted residuals, all carried into the proposal's tech-debt list:

1. `cache()`'s deduplication is a no-op under Vitest and therefore unverified by any automated test (DD3).
2. A future second route under `(app)` would redirect to `/login?next=%2Fdashboard` rather than its own path (DD2) — degraded UX, never a protection hole.
3. Layout wiring is proven only by DD8's manual checklist (D6).
