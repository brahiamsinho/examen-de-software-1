# Exploration: SSR/Server-Side Hardening of Protected Routes

Scope: whether and how to harden `(app)`/`(gate)` route protection at the
server, so an unauthenticated request never has protected-route markup
enter the response in the first place. Does not implement anything — output
is options with tradeoffs for `sdd-propose`.

## Current State

Route protection today is 100% client-side via `SessionGuard.tsx` (a
`"use client"` component), rendered inside `app/(app)/layout.tsx` and
`app/(gate)/layout.tsx` (both Server Components passing `children` through
to it). This premise is not a fresh discovery: `SessionGuard.tsx`'s own
docblock and the archived `frontend-auth-integration` `design.md`'s DD3
already document that `children` passed as a prop to a Client Component is
pre-rendered server-side and exists in the RSC payload even while visually
hidden pending the client-side redirect — DD3 explicitly flagged this for
revisit: "When SSR-protected content lands, D1's deferral must be revisited
first."

Severity check (confirmed by reading `dashboard/page.tsx` and
`select-organization/page.tsx`): both are themselves `"use client"` and
fetch real organization data only after mount, so what leaks today is inert
shell markup (headings, empty containers), never real data. This is a
structural-disclosure/hardening issue, not a live data leak.

Stack fact with real design impact: this project's installed Next.js
(16.3.3) deprecated `middleware.ts`, renaming it to `proxy.ts`, and Proxy
now defaults to the Node.js runtime rather than the old edge runtime — this
removes the edge-latency objection that historically argued against a real
backend validity check at the gate layer.

Zero server-side auth-check precedent exists anywhere in `frontend/src`
today: no `next/headers`, no `cookies()`, no server-side `redirect()` usage.

## Affected Areas

- `frontend/src/components/auth/SessionGuard.tsx` — retained as a
  fallback/UX layer (handles client-side session-expiry-during-use, which a
  one-time server check at navigation time cannot cover).
- `frontend/src/app/(app)/layout.tsx`, `frontend/src/app/(gate)/layout.tsx`
  — become async Server Components if a layout-level check is chosen.
- `frontend/proxy.ts` (new, if a Proxy-based approach is chosen) — must be
  named `proxy.ts`, not `middleware.ts`, on this Next 16 install.
- `frontend/src/lib/auth.ts`, `frontend/src/lib/api.ts` — `apiFetch` is
  browser-only (reads `document.cookie` for the CSRF token); a parallel
  server-side fetch helper forwarding `next/headers`' `cookies()` would be
  new code, not a reuse of the existing one.
- `openspec/specs/web-session/spec.md` — re-verify the "Session State and
  Route Protection" requirement's wording; likely no MODIFIED delta needed
  since it does not currently mandate client-only enforcement, but
  `sdd-spec` should confirm whether an explicit "server-enforced" scenario
  is worth adding.
- `frontend/src/components/auth/__tests__/SessionGuard.test.tsx` — a new
  Server Component/Proxy test pattern would be needed; no precedent exists
  in this repo's Vitest/RTL setup today.

## Approaches

1. **Proxy cookie-presence check.** A `proxy.ts` blocks any request with no
   session cookie present before the page renders.
   - Pros: cheap, blocks the bulk unauthenticated case with no per-request
     backend call.
   - Cons: cannot validate Django's opaque session cookie — a stale,
     expired, or otherwise invalid cookie still passes the presence check,
     leaving exactly the gap DD3 flagged.
   - Effort: Low.
2. **Server Component / async-layout validity check.** The route group
   layout becomes an async Server Component that calls `GET /api/auth/me`
   with forwarded cookies before rendering `children`, calling
   `next/navigation`'s `redirect()` on failure.
   - Pros: genuinely validates the session, not just cookie presence;
     extends DD3's own already-documented pattern; no protected markup ever
     enters the payload for an invalid session.
   - Cons: adds a real per-navigation backend call (latency, and load on
     `/api/auth/me`); requires the first server-side data-fetch code in this
     repo; `apiFetch` is not reusable as-is server-side.
   - Effort: Medium. **Recommended.**
3. **Hybrid** (Proxy pre-check + Server Component validity check).
   - Pros: blocks bulk unauthenticated traffic cheaply before the more
     expensive validity check runs.
   - Cons: two new, currently-untested surfaces for marginal gain — once
     Option 2 exists and Next 16's Node.js-runtime Proxy has removed the old
     edge-latency reason to compromise on presence-only, the Proxy layer
     adds cost without adding real protection Option 2 doesn't already give.
   - Effort: Medium-High.
4. **Leave as-is, documented.**
   - Pros: zero cost; the severity check shows no real data currently leaks.
   - Cons: does not satisfy the explicit product ask; a JS-disabled visitor
     still receives shell HTML for a protected route.
   - Effort: None.

## Recommendation

Option 2. The severity check shows this is a structural/hardening issue, not
a live data leak — but Option 1/3's presence-only layer leaves open exactly
the gap (invalid/stale cookie) DD3 already flagged, and Next 16's
Node.js-runtime Proxy removes the old edge-latency reason to accept that
compromise. Recommend `sdd-propose` scope Option 2, deferring the
Proxy-vs-layout-only implementation-stage question to `sdd-design` if any
residual presence-only pre-check is still judged worthwhile there — both are
architecturally sound at this repo's current scale.

**Scope discipline**: this change must stay bounded to the auth *gate*.
DD3 explicitly deferred server-side protected-*data* fetching (i.e. making
`dashboard/page.tsx` itself a Server Component that fetches real
organization data server-side) as a separate future revisit, and this
change must not smuggle that in.

## Open Questions / Risks

- `apiFetch` cannot be reused server-side as-is; a new server-side fetch
  helper is needed, which is itself a small scope-creep risk to watch.
- Zero test precedent exists for exercising Server Components or Proxy
  under this project's current Vitest+jsdom setup; Next 16's
  `next/experimental/testing/server` is plausibly compatible but unverified
  — needs a spike before `sdd-design` commits to a test strategy.
- A new per-navigation backend call increases latency and backend load;
  needs an explicit caching/TTL strategy decided at design time (or an
  explicit decision to accept the cost, given this project's scale).
- `(gate)/select-organization`'s own independent org-count redirect logic
  (redirect away if the caller has fewer than 2 organizations) must not be
  conflated with the new auth gate — they are two different checks that
  happen to live in the same route group.
- `openspec/specs/web-session/spec.md`'s current wording is
  client/server-agnostic; `sdd-spec` should confirm whether an explicit
  "server-enforced" scenario is worth adding or whether the existing
  wording already covers this without a delta.

## Ready for Proposal

Yes — proceed to `sdd-propose`, scoped around Option 2 (Server Component /
async-layout session-validity check), with the Proxy-vs-layout-only
question available to revisit in `sdd-design` if desired, and explicit scope
discipline against also adding server-side protected-*data* fetching, which
is out of scope for this change.
