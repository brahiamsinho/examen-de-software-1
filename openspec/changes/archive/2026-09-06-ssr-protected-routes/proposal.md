# Proposal: Server-Enforced Protected Routes

## Intent

Route protection is **100% client-side** today. `(app)/layout.tsx` and `(gate)/layout.tsx`
pass `children` as a prop into `SessionGuard`, a `"use client"` component — and per Next's
"Interleaving Server and Client Components" rule (already documented in `SessionGuard.tsx`'s
own docblock and archived `frontend-auth-integration` **DD3**), that `children` tree is
rendered on the server and shipped in the RSC payload *regardless* of what the guard later
decides to display. A visitor with no session, with JS disabled, or reading the raw response
receives protected-route shell HTML before any redirect fires.

Severity, verified: `dashboard/page.tsx` and `select-organization/page.tsx` are themselves
`"use client"` and fetch organization data only after mount, so what leaks is **inert shell
markup, never real data**. This is structural hardening, not a live breach. It is also the
exact revisit DD3 scheduled: *"When SSR-protected content lands, D1's deferral must be
revisited first."* Success = an unauthenticated request never receives protected-route markup
at all, because the server refuses to render it.

## Scope

### In Scope

- New server-only module `frontend/src/lib/server-session.ts` exposing `getServerUser()` and
  `requireUser()` — the first server-side data fetch in this repo (D2).
- `(app)/layout.tsx` and `(gate)/layout.tsx` become `async` Server Components that `await
  requireUser()` before rendering `children` (D2).
- New server-only env var `INTERNAL_API_URL` in `lib/env.ts`, defaulting to `apiUrl` (D2).
- Unit tests for `server-session.ts` under the existing Vitest setup (D6).
- MODIFIED delta on `web-session § Session State and Route Protection` (D7).
- Docs: `frontend/env.local.example`, README, `docs/ai/CURRENT_STATE.md`, `DECISIONS_LOG.md`.

### Out of Scope — Non-Goals (explicit, so `sdd-spec`/`sdd-design` do not scope-creep)

- **N1 — No server-side protected-*data* fetching.** `dashboard/page.tsx` and
  `select-organization/page.tsx` stay `"use client"` and keep fetching orgs client-side. DD3's
  deferral of server-fetched org data stands; this change gates *access*, not *data*.
- **N2 — No backend change.** `GET /api/auth/me`, `UserOut`, `django_auth`, and every
  `apps/users` module stay byte-for-byte untouched. No migration.
- **N3 — No session-cookie or CSRF changes.** `SESSION_COOKIE_*`, `CSRF_COOKIE_*`, and
  `apiFetch`'s priming/one-shot-retry logic are all unchanged.
- **N4 — No `(app)`/`(gate)` semantic changes** beyond the shared auth gate. No route moves,
  no group merges, no topbar or shell changes.
- **N5 — No `proxy.ts`** (D1). **N6 — No E2E/Playwright harness** (separately deprioritized).
- **N7 — No caching infrastructure** (no Redis, `unstable_cache`, or `cacheComponents`).
- **N8 — `SessionGuard.tsx` and its test are not modified** (D4).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `web-session`: the `Session State and Route Protection` requirement gains server-side
  enforcement; its current wording is client-shaped and does not forbid shipping protected
  markup to an anonymous request. Exact delta in **D7**.

## Resolved Decisions

**D1 — No `proxy.ts`. The async-layout check alone is the gate.** (Exploration Options 1/3
rejected.) Three reasons, not one: (a) a presence-only pre-check cannot validate Django's
opaque `sessionid`, so a stale or revoked cookie passes it — exactly the gap DD3 flagged, and
the layout check has to run anyway; (b) Next's own Proxy guide states Proxy "should not be
used as a full session management or authorization solution" and is for *optimistic* checks;
(c) **strict TDD makes Proxy near-untestable here** — verified at
`frontend/node_modules/next/dist/experimental/testing/server/*.d.ts`, Next's testing module
exports only `unstable_doesMiddlewareMatch`, `getRedirectUrl`, `getRewrittenUrl`, `isRewrite`
and config helpers. It asserts *whether a matcher matched*, never proxy behavior. Adding
Proxy would add an untestable surface for zero protection Option 2 does not already give.
Logged as tech debt #1, revisitable only if unauthenticated load ever becomes real.

**D2 — Server fetch mechanics: a new module, not a reuse of `apiFetch`.**
New file `frontend/src/lib/server-session.ts`:

- `getServerUser(): Promise<User | null>` — reads `await cookies()` from `next/headers`,
  forwards the whole cookie jar verbatim as a `cookie` request header, and calls
  `GET /api/auth/me` with `cache: "no-store"`. `200` → `User`; `401`/`403` → `null`; network
  failure or `5xx` → **throws**, so an outage is never mistaken for a logout.
- `requireUser()` wraps it and calls `next/navigation`'s `redirect("/login?next=<path>")` on
  `null`, reusing `lib/next-path.ts`'s `safe()` so the open-redirect guard stays single-sourced.
- **Why not `apiFetch`**: it is browser-only by construction — `readCsrfCookie()` touches
  `document.cookie`, and `credentials: "include"` is meaningless server-side. Forcing reuse
  would mean injecting a cookie source into a module whose docblock guarantees "nothing below
  this module knows about cookies". A parallel server module is the honest seam.
- **CSRF: not needed, confirmed.** `/api/auth/me` is a `GET`. Django's `CsrfViewMiddleware`
  enforces unsafe methods only, and `backend/apps/users/api.py` calls
  `_reject_unless_csrf_valid` **only** inside `login_view`. Empirically confirmed by
  `backend/apps/users/tests/test_api_auth.py`, which calls `auth_client.get("/api/auth/me")`
  with no CSRF header and passes, and by `apiFetch` itself only attaching `X-CSRFToken` on
  unsafe methods while `fetchMe()` is a plain GET.
- **New `INTERNAL_API_URL` is mandatory, not optional polish.** `NEXT_PUBLIC_API_URL` is
  `http://localhost:8000` — correct in the *browser* thanks to the published port, but inside
  the `frontend` container in `docker-compose.yml` `localhost` is the container itself, so a
  server-side fetch would `ECONNREFUSED`. `lib/env.ts` gains `internalApiUrl = process.env
  .INTERNAL_API_URL ?? apiUrl`, so bare `npm run dev` keeps working unchanged while Compose
  sets `INTERNAL_API_URL=http://backend:8000`. *(Not identified in exploration.)*

**D3 — React `cache()` per-request memoization; explicitly NO cross-request caching.**
This is a correctness decision before it is a performance one: `/api/auth/me` responses are
keyed on a per-user session cookie, so any cross-request cache is a session-confusion bug that
could serve user A's identity to user B. `cache: "no-store"` is set explicitly (any route
reading `cookies()` is dynamic anyway). Deduplication comes from wrapping `getServerUser` in
React's `cache()` — precisely the `verifySession` shape Next's own authentication guide
prescribes — so one render pass costs exactly one call no matter how many callers. **Accepted
cost**: one extra intra-host HTTP round trip per protected *server* navigation. Client-side
navigations inside the same layout segment do not re-run the layout, and this is a
docker-compose course project on a single host, not multi-region SaaS. A TTL cache would trade
a real security property for latency this project does not measure.

**D4 — `SessionGuard.tsx` is kept, entirely unchanged.** The two layers answer different
questions and neither subsumes the other. The server gate is navigation-time only: it cannot
see a session that expires *while* a page sits open, and it never runs for client-side
transitions within an already-mounted segment. `SessionGuard` also owns the `loading` skeleton
and the `error` retry UI, both of which are **already specified scenarios** in `web-session`;
deleting it would silently delete specified behavior the server check does not replicate.
Keeping it at zero edits also keeps the diff and the rollback minimal. Defense in depth here
is free, not redundant.

**D5 — `(gate)/select-organization`'s org-count redirect is untouched, and here is why.**
It answers a *routing* question ("does this caller have ≥2 organizations?") from
`useOrganizations()` / `GET /orgs`, and is owned by
`web-organization-workspace § Post-Login Organization Picker`. The new gate answers an
*authentication* question ("is there a valid session?") from `GET /api/auth/me`, owned by
`web-session`. They merely share a route group. Folding org count into the server layout would
force the layout to fetch organization data server-side — which is exactly **N1**, the boundary
this change is forbidden to cross. The page's `useEffect` redirect and its
`organizations.length < 2` early return stay byte-for-byte identical.

**D6 — Test the extracted function, not the Server Component. No spike.** The spike the
exploration proposed is already resolved as a dead end: `next/experimental/testing/server`
cannot render or execute a Server Component (D1's evidence). So all behavior lives in
`server-session.ts` as a plain async function, unit-tested under the **existing** Vitest+jsdom
setup by `vi.mock`-ing `next/headers` and `next/navigation` and stubbing `fetch` — structurally
identical to the existing `lib/__tests__/api.test.ts` and `auth.test.ts`. This yields a real
RED-GREEN-REFACTOR sequence for `sdd-tasks`: no cookie → `null`; `401` → `null`; `200` → user;
`5xx`/network → throws rather than redirecting; redirect target carries an escaped, `safe()`-d
`next`; `INTERNAL_API_URL` overrides `apiUrl`. Each layout then holds one `await requireUser()`
line — below the meaningful-test threshold, since asserting "the layout calls the helper" is a
tautology. **Stated honestly**: no automated test proves the layouts are wired. `sdd-tasks`
MUST therefore include a manual verification unit (`curl -i http://localhost:3000/dashboard`
with no cookie → `307` to `/login?next=%2Fdashboard`, body free of dashboard markup). That
check *is* the product ask, so it belongs in Success Criteria regardless.

**D7 — Yes, a MODIFIED delta is required.** The current requirement is client-shaped: it
mandates a skeleton while `loading` (a client-only state) and says protected content must not
*render before resolution* — wording a purely client-side guard already satisfies, which is why
today's leak is spec-compliant. Without a delta, a future reader could delete the server gate
and break nothing. Delta for `sdd-spec`, precise enough to need no re-investigation:

| Spec | Operation | Requirement | Migration |
|---|---|---|---|
| `web-session` | **MODIFIED** | `Session State and Route Protection` | All four existing scenarios survive **verbatim** (D4 keeps the client layer). Prose gains: the server MUST validate session validity before emitting protected-route markup. ADD three scenarios: (1) anonymous server request → redirect response, body contains no protected markup; (2) a *present but invalid/expired* cookie is rejected server-side (presence ≠ validity); (3) backend unreachable during the server check does not redirect to `/login` — it falls through to the client `error`/retry state. |
| `web-organization-workspace`, `user-authentication`, `organization-tenancy`, `tenant-isolation` | *no delta* | all | D5/N1/N2: picker semantics, auth endpoints, and the URL-path tenant-key rule are all untouched. |

**D8 — Non-goals are enumerated as N1–N8 under "Out of Scope" above** and are binding on
`sdd-spec`, `sdd-design`, and `sdd-apply`.

## Approach

`lib/env.ts` gains `internalApiUrl`. `lib/server-session.ts` is authored test-first (D6) and is
the only file with real logic. Both layouts become `async` and gain one `await requireUser()`
call above their existing JSX, which is otherwise unchanged — `SessionGuard` stays wrapped
around `children` exactly as today (D4). Strict TDD is enabled project-wide, so `sdd-apply`
drives `server-session.ts` RED-GREEN-REFACTOR one behavior at a time before touching either
layout.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/src/lib/server-session.ts` | **New** | `getServerUser()` + `requireUser()`; the only real logic |
| `frontend/src/lib/__tests__/server-session.test.ts` | **New** | Full behavior coverage (D6) |
| `frontend/src/lib/env.ts` | Modified (additive) | `internalApiUrl` with `apiUrl` fallback (D2) |
| `frontend/src/app/(app)/layout.tsx`, `(gate)/layout.tsx` | Modified | `async` + one `await requireUser()` line each |
| `frontend/env.local.example`, `docker-compose.yml` | Modified | Document/set `INTERNAL_API_URL` |
| `frontend/src/components/auth/SessionGuard.tsx` + its test | **Untouched** | D4 |
| `frontend/src/lib/api.ts`, `lib/auth.ts` | **Untouched** | D2 — new module, no reuse |
| `frontend/src/app/(app)/dashboard/page.tsx`, `(gate)/select-organization/page.tsx` | **Untouched** | N1, D5 |
| `backend/**` | **Untouched** | N2 — no endpoint, schema, or migration change |
| `openspec/specs/web-session/spec.md` | Modified | D7 delta |
| `docs/ai/CURRENT_STATE.md`, `DECISIONS_LOG.md`, `README` | Modified | Dual-documentation convention; D1–D8 |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| **Cross-domain deploy breaks the gate for everyone.** The gate only works if the browser sends `sessionid` to the *Next.js* origin. True today (a cookie from `localhost:8000` is sent to `localhost:3000` — cookies ignore ports) and for shared-parent-domain deploys; **false** for `app.x.com`/`api.y.com`, where every authenticated user would be bounced to `/login`. | **Medium** | Documented as an explicit deployment precondition in `env.local.example`, README and `ARCHITECTURE.md`; verified manually on the Compose stack in Success Criteria. Tech debt #2. *(Not identified in exploration.)* |
| Server fetch hits `localhost:8000` inside the frontend container and `ECONNREFUSED`s | **High if unhandled** | D2's `INTERNAL_API_URL`, with a dedicated test asserting the override |
| Layout wiring has no automated test | Medium | D6's mandatory manual verification unit; the layouts are one line each |
| `/api/auth/me` outage turns into a mass logout | Medium | D2: non-`401` failures throw instead of redirecting; D7 scenario 3 pins it; the client `error`/retry path (D4) remains the fallback |
| Added per-navigation latency | Low | D3: one intra-host call, `cache()`-deduped, single-host project |
| Reviewer reads the retained `SessionGuard` as dead code | Medium | D4 states the two layers' distinct jobs; `SessionGuard.tsx` is deliberately a zero-line diff |
| Double redirect (server 307 then client `router.replace`) | Low | The server redirect lands on `(auth)/login`, which has no guard, so the client guard never re-fires |

## Rollback Plan

Cheap and partial-revert-safe, because **no backend, model, migration, or existing frontend
module changes**.

1. `git revert` the change commits: both layouts return to synchronous Server Components and
   `server-session.ts` disappears. `SessionGuard` is already untouched, so client-side
   protection is fully intact at every point of the revert — there is **no window with no
   protection at all**.
2. Partial rollback: reverting only the two layout files restores the old behavior while the
   tested helper stays in the tree, unused and harmless.
3. `INTERNAL_API_URL` is additive with a fallback; leaving it set after a revert is inert.
4. The `web-session` delta reverts with the same commits.

## Dependencies

- **No new package dependency.** `next/headers`, `next/navigation`, and React's `cache()` all
  ship with the installed Next 16.3.3.
- A reachable backend at `INTERNAL_API_URL` *from the Next.js server process* — a new runtime
  requirement this change introduces (D2).
- Builds on archived `frontend-auth-integration` (DD3) and `tenant-aware-registration-login`.

## Explicit Tech Debt

1. No `proxy.ts` (D1): unauthenticated traffic still reaches the Next.js server and costs one
   backend call before being rejected. Acceptable at this scale; revisit only under real load.
2. The gate assumes the session cookie reaches the Next.js origin (see Risks). A truly
   cross-domain deployment would need a token forwarded another way — out of scope here.
3. The layouts' wiring is covered only by a manual check (D6).
4. Protected *data* is still fetched client-side (N1); DD3's deferral remains open.

## Success Criteria

- [x] `curl -i http://localhost:3000/dashboard` with **no** cookie returns a redirect to
      `/login?next=%2Fdashboard`, and the response body contains **no** real dashboard/org/user
      data — only Next.js's own inert redirect scaffolding (verified during `sdd-apply`/
      `sdd-verify`: Next 16.3.3 always streams a small `<html id="__next_error__">` shell
      alongside a `redirect()`-triggered 307, so a literal "no `<html>` in the body" check is
      the wrong proxy for this property; "no protected markup" means no protected *content*,
      per this proposal's own Intent framing).
- [ ] The same request with a **present but invalid/expired** `sessionid` is redirected too.
- [ ] The same request with a **valid** session renders the dashboard shell as it does today.
- [ ] `/select-organization` behaves identically for an authenticated user with ≥2 orgs, and
      still redirects to `/dashboard` at <2 orgs (D5).
- [ ] With the backend stopped, an authenticated visit does **not** redirect to `/login`.
- [ ] `getServerUser()` uses `INTERNAL_API_URL` when set and `apiUrl` when not (unit-tested).
- [ ] `SessionGuard.tsx` and `SessionGuard.test.tsx` show a zero-line diff.
- [x] `git diff --stat backend/` is limited to `backend/env.example` documenting the
      `ALLOWED_HOSTS` addition required for the frontend container's server-side fetch to reach
      `backend:8000` (discovered during `sdd-apply`'s mandatory manual verification, D6/DD8) —
      no Django app code, model, schema, endpoint, or migration file changed. This is a narrower,
      honest restatement of N2's actual intent (frozen application behavior), not a violation of
      it; the original "empty" wording was too literal.
- [ ] No new migration file exists.
- [ ] `cd frontend && npm test` and `cd backend && pytest` are both green.
- [ ] `docs/ai/CURRENT_STATE.md` and `DECISIONS_LOG.md` record D1–D8.
