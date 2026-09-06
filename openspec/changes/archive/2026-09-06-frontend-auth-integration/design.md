# Design: Cycle 3 — Frontend Auth Integration (Session, Panel, Organizations)

> Size note: this document exceeds the default 800-word design budget, following the precedent set by
> `archive/2026-09-06-multi-tenant-identity/design.md` — this project's design artifacts carry a
> complete file architecture table.

## Technical Approach

One vertical slice through the Next.js app, layered so each layer has exactly one reason to change:

```
lib/api.ts        transport   credentials + CSRF + error normalization (the single seam)
      ↓
lib/auth.ts       domain      typed calls, one module per backend Django app
lib/organizations.ts
      ↓
state/session.ts  state       Jotai atoms + the one hook that owns the `me` fetch
state/organizations.ts
      ↓
components/       UI          presentational forms + guard, no fetch logic
      ↓
app/(auth)|(app)  routing     route groups; the guard lives in the `(app)` layout only
```

Nothing below `lib/` knows about cookies or CSRF; nothing above `state/` calls `fetch`. Implements
proposal D1–D8 and the FEA-C3-1..6 use cases the parallel spec formalizes.

**Backend contract (verified, frozen).** Mounted at `path("api/", api.urls)`:
`GET /api/auth/csrf` → `{csrf_token}`; `POST /api/auth/register` → 201 `UserOut`;
`POST /api/auth/login` → 200 `UserOut`; `POST /api/auth/logout` → 204; `GET /api/auth/me` → 200
`UserOut` (401 anonymous); `GET /api/orgs` → `OrganizationOut[]`; `POST /api/orgs` → 201.
`UserOut = {id, email, full_name}`; `OrganizationOut = {id, name, slug, plan, my_role}`.
`register`/`login` are anonymous **but still CSRF-checked** (`apps/users/api.py` calls
`ninja.utils.check_csrf` explicitly) — this is why priming is unconditional, not login-only.

---

## File Architecture

### New — transport and domain (`frontend/src/lib/`)

| Path | Responsibility |
|---|---|
| `lib/auth.ts` | `User` type + `register`, `login`, `logout`, `fetchMe`. Mirrors `backend/apps/users/`. Clears the CSRF cache after login/logout (Django rotates the token there). |
| `lib/organizations.ts` | `Organization` type + `listOrganizations`, `createOrganization`. Mirrors `backend/apps/organizations/`. |
| `lib/__tests__/api.test.ts` | The three silently-failing behaviours: `credentials: "include"`, priming (and its skip), `X-CSRFToken`; plus `ApiError` / `NetworkError` mapping and the single 403 retry. |
| `lib/__tests__/auth.test.ts`, `lib/__tests__/organizations.test.ts` | Path, method, body, and returned shape per call. |

### New — state (`frontend/src/state/`)

| Path | Responsibility |
|---|---|
| `state/session.ts` | `sessionAtom: Session` + `useSession()` — the only caller of `fetchMe`. |
| `state/organizations.ts` | `organizationsAtom`, `activeOrgSlugAtom` + `useOrganizations()` — list load, active-slug persistence, optimistic append on create. |
| `state/__tests__/session.test.tsx`, `state/__tests__/organizations.test.tsx` | State transitions under a per-test Jotai `Provider` (DD4). |

### New — components

| Path | Responsibility |
|---|---|
| `components/auth/SessionGuard.tsx` | `"use client"`. Renders skeleton \| `children` \| retry panel; redirects on `anonymous`. The only file that decides who sees `(app)`. |
| `components/auth/LoginForm.tsx`, `RegisterForm.tsx` | `"use client"`. Local `useState` fields, submit, inline error. No routing knowledge beyond a post-success `router.replace`. |
| `components/workspace/AppTopbar.tsx` | `"use client"`. Brand, `OrgSwitcher`, user email, logout button. |
| `components/workspace/OrgSwitcher.tsx` | `"use client"`. Select over `organizationsAtom`, writes `activeOrgSlugAtom`, shows `my_role`. |
| `components/workspace/CreateOrgForm.tsx` | `"use client"`. name + slug; surfaces the backend `detail` on 409. |
| `components/workspace/OrgEmptyState.tsx` | Zero-org prompt wrapping `CreateOrgForm` (confirmed: empty state, not a blocking wizard). |
| `components/{auth,workspace}/__tests__/*.test.tsx` | One file per component, RTL. |

### New — routes (`frontend/src/app/`)

| Path | Responsibility |
|---|---|
| `app/(auth)/layout.tsx` | Server Component. Centered-card shell. |
| `app/(auth)/login/page.tsx` → `/login` | Server Component rendering `<LoginForm />`. |
| `app/(auth)/register/page.tsx` → `/register` | Server Component rendering `<RegisterForm />`. |
| `app/(app)/layout.tsx` | Server Component: `<SessionGuard><AppTopbar />{children}</SessionGuard>`. |
| `app/(app)/dashboard/page.tsx` → `/dashboard` | Org list \| `OrgEmptyState`. **Fetches nothing on the server** (see DD3). |

### Modified / created

| Path | Change |
|---|---|
| `frontend/src/lib/api.ts` | Rewritten per DD1. Currently 4 lines with no `credentials` — the tech debt this cycle exists to close. |
| `frontend/src/components/landing/Navbar.tsx` | The dead `<a href="#">Iniciar sesión</a>` (line 30) becomes `<Link href="/login">`; a `Registrarse` link is added. The `Empezar gratis` CTA keeps `href="#precios"` so both existing `Navbar.test.tsx` assertions stay green. |
| `frontend/env.local.example` | Created: `NEXT_PUBLIC_API_URL=http://localhost:8000`. README step 3 and `lib/env.ts`'s error message both name a file absent from the repo. |

Untouched by contract: all of `backend/`, `mobile/`, `frontend/src/components/landing/*` except `Navbar.tsx`,
`app/layout.tsx`, `app/page.tsx`.

---

## Design Decisions

Continuing the proposal's D1–D8.

### DD1 — `apiFetch`: mandatory credentials, body-sourced CSRF, two error types

```ts
export class ApiError extends Error {          // a response arrived
  constructor(readonly status: number, readonly code: string, readonly detail: string) { super(detail); }
}
export class NetworkError extends Error {}     // no response at all

export async function apiFetch<T>(path: string, init?: ApiFetchInit): Promise<T>;
```

`credentials: "include"` is set by `apiFetch` and is not overridable by `init`. Unsafe methods get
`X-CSRFToken`. Non-2xx → `ApiError`; a rejected `fetch` → `NetworkError`. 204 → `undefined`.

**Error body normalization.** Domain errors return `{detail, code}`; `django_auth` 401 returns
`{detail: "Unauthorized"}` with no `code`; Ninja 422 returns `detail` as an **array**. `apiFetch`
therefore coerces: missing `code` → `"http_" + status`, non-string `detail` → `JSON.stringify`.

**Rejected**: leaving `apiFetch` a dumb primitive plus an opt-in wrapper — a forgotten `credentials`
is then a silent anonymous request rather than a compile or test failure.

### DD2 — CSRF token read from the response **body**, not `document.cookie` (supersedes the proposal's mitigation detail)

The proposal's mitigation said "read `document.cookie` per request". That is correct only in local
dev, where `:3000` and `:8000` share the host `localhost` and cookies ignore port. In the deployed
matrix the archived backend design documents (`app.example.com` → `api.example.com`), the `csrftoken`
cookie belongs to the API domain and JavaScript on the app domain **cannot read it** — priming would
appear to succeed and every unsafe request would 403.

```ts
let cachedCsrfToken: string | null = null;

async function csrfToken(): Promise<string> {
  const fromCookie = readCookie("csrftoken");            // fast path, dev only
  if (fromCookie) return fromCookie;
  if (cachedCsrfToken) return cachedCsrfToken;
  const { csrf_token } = await primeCsrf();              // GET /api/auth/csrf, credentials included
  return (cachedCsrfToken = csrf_token);
}
export function invalidateCsrfToken() { cachedCsrfToken = null; }
```

The cookie always wins when readable, so rotation on login/logout is picked up automatically in dev.
Cross-domain, `lib/auth.ts` calls `invalidateCsrfToken()` after login and logout, and a 403 on an
unsafe request invalidates + re-primes + retries **exactly once** (a boolean on the call frame, not a
loop). `GET /api/auth/csrf` is safe to repeat and returns the same value the cookie carries, because
`CSRF_USE_SESSIONS` is off.

### DD3 — The guard is a Client Component receiving server children; `(app)` pages fetch nothing server-side

`app/(app)/layout.tsx` stays a Server Component and passes `children` into `<SessionGuard>` as a prop.
Per `node_modules/next/dist/docs/01-app/01-getting-started/05-server-and-client-components.md`
("Interleaving Server and Client Components"), children passed as props are **not** pulled into the
client module graph, so `/dashboard` keeps its server rendering and the client bundle stays small.

The load-bearing consequence: `children` is rendered on the server before the guard resolves, so its
markup exists in the RSC payload even while hidden. Under D1 there is no server-side session, so any
protected data fetched in an `(app)` page would both fail (no cookie forwarding) **and** leak into that
payload. **Rule: every `(app)` page renders only static shell; all protected data arrives through
client hooks.** When SSR-protected content lands, D1's deferral must be revisited first.

### DD4 — Route-group layouts type `children` explicitly, not via `LayoutProps`

`frontend/.next/types/routes.d.ts` (generated) shows `type LayoutRoutes = "/"` and `ParamMap` keyed by
**URL path**. Route groups do not appear in the URL, so `app/(auth)/layout.tsx` and
`app/(app)/layout.tsx` would both key on `"/"` — the same key `app/layout.tsx` already uses. Both group
layouts therefore declare `{ children: React.ReactNode }` directly (the form the layout docs show for
the root layout). `app/layout.tsx` keeps its existing `LayoutProps<"/">` untouched. `next typegen`
runs as part of `next dev`/`next build`; a stale `.next/types` is a typecheck-only artifact.

**Jotai store.** Production uses jotai's default module store (no `Provider`), so no client boundary is
forced into `app/layout.tsx`. Tests wrap renders in `<Provider>` from `jotai` for per-test isolation —
without it the module store leaks session state between test files.

### DD5 — Session as a discriminated union; 401 and outage are different variants

```ts
export type Session =
  | { status: "loading" }
  | { status: "authenticated"; user: User }
  | { status: "anonymous" }
  | { status: "error"; message: string };
```

`useSession()` fires `fetchMe()` once per shell mount and maps `ApiError(401)` → `anonymous`, every
other `ApiError` and any `NetworkError` → `error`. `SessionGuard` renders a skeleton for `loading`, a
retry panel for `error`, and only redirects for `anonymous`. A union rather than
`{user, loading, error}` makes "backend outage logs the user out" unrepresentable instead of merely
untested.

**Redirect and return.** `anonymous` → `router.replace("/login?next=" + encodeURIComponent(pathname))`
via `useRouter`/`usePathname` from `next/navigation`. Post-login the target is sanitized before use:

```ts
const safe = (n: string | null) => (n && /^\/(?!\/)/.test(n) ? n : "/dashboard");
```

Single leading slash only — `//evil.com` and `https://evil.com` both fall back to `/dashboard`. The
`useRouter` docs warn explicitly that unsanitized URLs passed to `push`/`replace` are an XSS vector.
Logout → `router.replace("/")` (confirmed).

### DD6 — Active org: plain atom + explicit effect, not `atomWithStorage`

`activeOrgSlugAtom` is a plain `atom<string | null>(null)`; `useOrganizations()` reads
`localStorage` in an effect after mount and writes on change. `atomWithStorage` initializes from
storage during render, which mismatches the server-rendered HTML and would need version-specific
`getOnInit` behaviour this design refuses to assert from memory. Selection rule: persisted slug if it
is still in the list, else the first org, else `null`.

**This atom is a UI convenience only.** Backend D3 fixed the tenant key as a URL path segment; future
tenant-scoped pages read `/orgs/[slug]/...` from the route. No request may ever derive its
organization from this atom.

### DD7 — Optimistic-append on org creation, backend `detail` on conflict

`createOrganization` returns the created `OrganizationOut` with `my_role: "OWNER"` already set
(`apps/organizations/api.py` passes `Role.OWNER`), so `useOrganizations()` appends the response and
sets it active — no refetch, satisfying "appears as OWNER without manual refresh". A 409 surfaces
`ApiError.detail` verbatim under the slug field; the frontend does not invent duplicate-slug copy.

---

## Data Flow

```
/dashboard (anonymous)
  (app)/layout.tsx ──► SessionGuard ──► useSession ──► lib/auth.fetchMe
                            │                              └─► apiFetch GET /api/auth/me (cookies)
                            │                                      └─ 401 ─► ApiError
                            ├─ loading  ─► skeleton (children hidden)
                            ├─ error    ─► retry panel        (NetworkError / 5xx)
                            └─ anonymous ─► router.replace("/login?next=/dashboard")

/login submit
  LoginForm ─► lib/auth.login ─► apiFetch POST /api/auth/login
                                    ├─ csrfToken(): cookie → cache → GET /api/auth/csrf
                                    ├─ headers X-CSRFToken, credentials: "include"
                                    └─ 200 ─► sessionid cookie set + token rotated
              ─► invalidateCsrfToken() ─► sessionAtom = authenticated ─► replace(safe(next))

/dashboard (authenticated)
  useOrganizations ─► apiFetch GET /api/orgs ─► organizationsAtom
        ├─ [] ─► OrgEmptyState ─► CreateOrgForm ─► POST /api/orgs ─► append + set active
        └─ [..] ─► OrgSwitcher (localStorage slug ∩ list, else first)
```

---

## Interfaces

```ts
// lib/api.ts
type ApiFetchInit = Omit<RequestInit, "credentials"> & { json?: unknown };
export async function apiFetch<T>(path: string, init?: ApiFetchInit): Promise<T>;
export function invalidateCsrfToken(): void;
export class ApiError extends Error { status: number; code: string; detail: string }
export class NetworkError extends Error {}

// lib/auth.ts
export type User = { id: string; email: string; full_name: string };
export function register(input: { email: string; password: string; full_name?: string }): Promise<User>;
export function login(input: { email: string; password: string }): Promise<User>;
export function logout(): Promise<void>;
export function fetchMe(): Promise<User>;

// lib/organizations.ts
export type Role = "OWNER" | "EDITOR" | "VIEWER";
export type Organization = { id: string; name: string; slug: string; plan: string; my_role: Role | null };
export function listOrganizations(): Promise<Organization[]>;
export function createOrganization(input: { name: string; slug: string }): Promise<Organization>;
```

---

## Testing Strategy

Strict TDD: every work unit writes the RED test first. `fetch` is stubbed with `vi.stubGlobal` at the
module boundary — no MSW (new dependency, rejected by D8).

| Layer | What to test | Approach |
|---|---|---|
| Transport | `credentials: "include"` on every call; priming fires when no token and is skipped when the cookie exists; `X-CSRFToken` present on unsafe / absent on GET; 403 → one re-prime + one retry, never two; `ApiError` vs `NetworkError`; 422 array `detail` coerced | `vi.stubGlobal("fetch")`, assert on the captured `RequestInit`; cookie via `document.cookie` in jsdom |
| Domain client | Path, method, JSON body, parsed shape, 409 `detail` propagation | Same stub, one file per module |
| State | `loading → authenticated`; `401 → anonymous`; `NetworkError → error` (**not** anonymous); active-slug fallback when the persisted slug is stale; optimistic append | `renderHook` inside a fresh jotai `<Provider>`; `localStorage` cleared per test |
| Component | Guard renders no protected content while `loading`; retry panel on `error`; forms submit and surface inline errors; switcher shows `my_role`; empty state on `[]` | RTL + `userEvent`; `next/navigation` mocked with `vi.mock` to capture `replace` |
| Routing contract | `safe(next)` accepts `/dashboard`, rejects `//evil.com`, `https://evil.com`, `null` | Pure-function unit test — the open-redirect guard is tested apart from the component |
| Regression | Existing `Navbar.test.tsx` stays green after the link change; `app/__tests__/page.test.tsx` untouched | `npm test` |

Manual smoke checklist (the real cross-origin cookie flow, not covered by stubs): register → reload →
still authenticated; logout → `/`; stop the backend and load `/dashboard` → retry panel, not `/login`.

---

## Threat Matrix

**N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary.** ("Routing" in this matrix means process/command routing; the browser
routing here is ordinary application code.)

| Boundary | Applicability |
|---|---|
| Documentation-like paths | N/A — no file classification or execution of repository content. |
| Git repository selection | N/A — no VCS invocation. |
| Commit state | N/A — no index or worktree interaction. |
| Push state | N/A — no remote interaction. |
| PR commands | N/A — no PR automation. |

This cycle's real adversarial surface is browser-side and is covered by spec requirements plus the
tests above: open redirect via `?next=` (DD5), CSRF double-submit correctness (DD1/DD2), and no
protected data in the pre-guard RSC payload (DD3).

---

## Migration / Rollout

**No migration required.** No schema, no dependency (jotai `^2.20.3` is already installed for the
canvas work), no backend change. `next dev`/`next build` regenerates `.next/types/routes.d.ts` when
the new routes land; `AppRoutes` widens from `"/"` to include `/login`, `/register`, `/dashboard`.

Work order is the dependency chain and must not be reordered: `env.local.example` → `lib/api.ts` →
`lib/auth.ts` + `lib/organizations.ts` → `state/*` → `SessionGuard` + layouts → auth screens →
org panel → `Navbar.tsx`.

Rollback per the proposal, unchanged: `git revert`; or delete `app/(auth)/` + `app/(app)/`; or revert
`lib/api.ts` alone, which the landing page never calls.

---

## Open Questions

- [ ] DD2 corrects the proposal's `document.cookie` mitigation for the deployed cross-domain matrix.
      The correction is unverified against a real second domain — local dev exercises only the
      cookie fast path. The body-token path needs the manual smoke check once a deployed origin exists.
- [ ] `.next/types/routes.d.ts` was read as generated for the current single-route app. The claim that
      two route-group layouts collide on the `"/"` key is inferred from that file's shape, not observed
      after adding the groups. If typegen in fact emits distinct keys, DD4's explicit typing remains
      valid but stops being necessary.
- [ ] Session expiry mid-session (backend logs the user out while the tab is open) produces a 401 on
      the next org call, which this design surfaces as an inline error rather than re-running the
      guard. Recorded as tech debt by the proposal; not addressed here.
