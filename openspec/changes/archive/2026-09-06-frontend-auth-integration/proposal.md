# Proposal: Cycle 3 — Frontend Auth Integration (Session, Panel, Organizations)

## Intent

Cycle 2 shipped a complete, session-authenticated multi-tenant backend (170 tests green:
`/api/auth/{csrf,register,login,logout,me}`, `/api/orgs`, `/api/orgs/{slug}/members`) and
closed with an explicit tech-debt item: *"No frontend or mobile authentication UI consumes
these endpoints yet."* Today the Next.js app has exactly one route — the marketing landing
page — and its only backend-facing code, `frontend/src/lib/api.ts`, is a four-line `fetch`
wrapper with **no `credentials: "include"`** and no CSRF handling. Any auth code written on
top of it today would silently never send or receive the session cookie.

The result is a product that promises "Organizaciones", "Owner / Editor / Lector" and
per-plan tiers on its landing page and cannot log anybody in. Section 5 of the frozen spec
requires "registro e inicio de sesión" as a user-visible capability, not an OpenAPI page.

This cycle closes the gap: a credentialed, CSRF-aware transport layer, real login and
registration screens, a client-side session contract, and a protected panel where a user
sees and creates their organizations.

## Scope

### In Scope (section 38 cycle shape)

**Objective**: a browser-usable authenticated shell — a visitor can register or log in, is
kept out of protected routes when anonymous, and once inside can see, switch between, and
create organizations.

Use cases (project-local identifiers):

- `FEA-C3-1` — Credentialed transport: every request carries the session cookie; unsafe
  requests carry a valid `X-CSRFToken`, primed automatically.
- `FEA-C3-2` — Register from `/register` and land authenticated (backend logs the user in on
  successful registration).
- `FEA-C3-3` — Log in from `/login`, log out from the panel; server-side session invalidation.
- `FEA-C3-4` — Client-side session gate: a protected route resolves identity via
  `GET /api/auth/me` and redirects anonymous users to `/login`.
- `FEA-C3-5` — List the current user's organizations with their role, and switch the active
  one (UI-level default only).
- `FEA-C3-6` — Create an organization from the panel; the creator becomes `OWNER`.

### Out of Scope

- **Server-side / middleware route gating and SSR-rendered protected content.** Explicitly
  deferred (D1); revisit when the UML canvas needs SSR.
- **Membership management UI** — invite, remove, change role. The endpoints exist
  (`/api/orgs/{slug}/members`); no screen consumes them this cycle.
- **Organization editing** — rename, plan change, delete. Read + create only.
- **Any UML, canvas, Cytoscape, project, or realtime work.** Untouched.
- **Tenant-scoped routes** (`/orgs/[slug]/...`). Nothing tenant-scoped is rendered yet, so no
  such route is created — see D5 on why the active org is deliberately *not* authoritative.
- **Password reset, email verification, MFA, social login, "remember me".** No backend
  support exists.
- **Flutter/mobile auth**, Cypress/E2E bootstrap, and MSW. No new runtime or dev dependency.
- **Backend changes.** The Cycle-2 contract (`UserOut`, `OrganizationOut`, error shape
  `{detail, code}`) is treated as frozen.
- **Role-gated UI behaviour.** `my_role` is displayed; nothing is hidden or disabled by it.

## Capabilities

> Contract with `sdd-spec`. Existing specs: `uml-domain-model`, `project-document`,
> `uml-validation`, `user-authentication`, `organization-tenancy`,
> `organization-membership`, `tenant-isolation`.

### New Capabilities

- `web-session`: the browser-side session contract — credentialed transport, CSRF priming
  and header echo, error normalization, the four session states
  (`loading | authenticated | anonymous | error`), route protection, redirect-on-anonymous,
  and login/register/logout screen behaviour.
- `web-organization-workspace`: the authenticated panel shell — organization list with role,
  active-organization selection and its persistence, the zero-organizations empty state, and
  organization creation.

### Modified Capabilities

None. No backend requirement changes. `user-authentication`, `organization-tenancy`, and
`organization-membership` describe the server contract this cycle *consumes*; the new
capabilities describe browser-side behaviour those specs deliberately say nothing about.

## Resolved Decisions

**D1 — Client-side session checking; no server gate this cycle (fixed by the project owner).**
Protected surfaces resolve identity by calling `GET /api/auth/me` on mount. Rationale: the
session cookie is `SESSION_COOKIE_HTTPONLY = True` (hardcoded in `settings.py`), so the
*only* way any client can know it is logged in is to ask the backend — a server-side check
would still make that same round trip while adding cookie-forwarding complexity across the
Next→Django server-to-server hop. The cost is a brief loading state on protected routes,
which D4 makes explicit rather than accidental. Middleware/server-layout gating is
**deferred, not rejected**: it becomes worth its complexity when SSR-rendered protected
content exists (the canvas), and layering it in later does not invalidate the
`/api/auth/me` contract established here.

**D2 — Route groups keep URLs flat while separating layouts.** `(auth)` for `/login` and
`/register` (centered card, no app chrome), `(app)` for the protected area (session guard +
topbar with org switcher and logout). The landing page stays at `/` in the root layout,
untouched. Rationale: route groups give two genuinely different shells without polluting the
URL with `/auth/login`, and put the guard in exactly one place — the `(app)` layout — so a
new protected page is protected by existing at the right path, not by remembering to add a
check. The panel's first page is `/dashboard`.

**D3 — `apiFetch` is the single transport seam and is fixed in place; domain calls live in
one module per backend app.** `frontend/src/lib/api.ts` gains, non-optionally:
`credentials: "include"`, automatic idempotent CSRF priming (`GET /api/auth/csrf` when the
`csrftoken` cookie is absent) before any unsafe method, the `X-CSRFToken` header, JSON
handling, and a typed `ApiError { status, code, detail }` thrown on non-2xx. Rationale:
these are not caller concerns — a caller that forgets `credentials` produces a silently
anonymous request, not an error, which is the worst possible failure mode. Priming belongs
here rather than in a root-layout effect because an effect is not guaranteed to have run
before the first unsafe request. On top of it, `lib/auth.ts` (`register`, `login`, `logout`,
`getMe`) and `lib/organizations.ts` (`listOrganizations`, `createOrganization`) mirror the
backend's `apps/users` + `apps/organizations` split, per the owner's one-domain-per-module
preference. **Rejected**: leaving `apiFetch` a dumb primitive and wrapping it — that makes
the unsafe path opt-in.

**D4 — Anonymous access to a protected route is a client redirect to `/login?next=<path>`.**
The `(app)` layout renders a skeleton while `me` is in flight and *never* renders protected
content before resolution. A `401` means anonymous → redirect. A network error or `5xx` is
**not** a redirect — it renders a retry state, so a backend outage does not masquerade as a
logout. After a successful login the user returns to `next` when it is a single-leading-slash
relative path (open-redirect guard), otherwise `/dashboard`.

**D5 — Session and organization state live in Jotai atoms; the active organization is a UI
default with no authority.** Atoms: `sessionAtom`, `organizationsAtom`, `activeOrgSlugAtom`,
consumed through a `useSession()` hook that owns the single `me` fetch per shell mount.
Rationale: `jotai` is already a dependency (installed for the canvas), the consumers (guard,
topbar, forms, pages) are structurally far apart, and a Context holding one object would
re-render every consumer on any field change. **Rejected**: React Context — workable, but it
reintroduces jotai's job as a second state idiom. The active slug is persisted in
`localStorage` and falls back to the first organization when the stored slug is absent from
the fetched list. Critically, this is **UI convenience only**: backend D3 fixed the tenant
key as a URL path segment, so when tenant-scoped pages arrive they will be `/orgs/[slug]/...`
and read the slug from the route, never from this atom.

**D6 — `frontend/env.local.example` is recreated in this cycle.** `README.md` step 3,
the `docker-compose.yml` comment, and the runtime error thrown by `frontend/src/lib/env.ts`
all instruct the reader to copy a file that does not exist in the repo. A new contributor —
or the instructor — following the README fails at step 3. One line
(`NEXT_PUBLIC_API_URL=http://localhost:8000`) closes a documented-but-broken setup path.

**D7 — No new dependency.** UI is built from the already-installed Tailwind 4 + shadcn
scaffold; any additional primitive (input, label, card, dropdown) is generated as local
source by the installed shadcn CLI, which adds files, not runtime packages. Forms use plain
React state and the existing `components/ui/button.tsx`.

**D8 — Testing is Vitest + RTL with `fetch` stubbed at the module boundary.** Strict TDD is
enabled project-wide (`openspec/config.yaml: strict_tdd: true`), so every unit is
RED-GREEN-REFACTOR. `apiFetch` gets direct tests asserting `credentials: "include"`, CSRF
priming, and the `X-CSRFToken` header — the three things that fail silently in production if
wrong. MSW is not introduced (new dependency); real cross-origin cookie behaviour is covered
by the backend's existing `test_cross_origin_session.py` plus a documented manual smoke
check.

## Approach

```
frontend/src/
├── lib/
│   ├── api.ts               # MODIFIED — credentials, CSRF priming + header, ApiError
│   ├── auth.ts              # NEW — register/login/logout/getMe (mirrors apps/users)
│   ├── organizations.ts     # NEW — list/create (mirrors apps/organizations)
│   └── env.ts               # unchanged
├── state/
│   ├── session.ts           # NEW — sessionAtom, useSession()
│   └── organizations.ts     # NEW — organizationsAtom, activeOrgSlugAtom
├── components/
│   ├── auth/                # NEW — LoginForm, RegisterForm, SessionGuard
│   ├── workspace/           # NEW — AppTopbar, OrgSwitcher, CreateOrgForm, OrgEmptyState
│   └── landing/             # unchanged
└── app/
    ├── page.tsx             # unchanged (landing)
    ├── (auth)/layout.tsx    # NEW — centered card shell
    ├── (auth)/login/page.tsx
    ├── (auth)/register/page.tsx
    ├── (app)/layout.tsx     # NEW — SessionGuard + AppTopbar
    └── (app)/dashboard/page.tsx
```

- Work order follows the dependency chain, so nothing is built on a broken foundation:
  transport (`api.ts`) → domain clients → session state → guard/layouts → screens → org panel.
- **`frontend/AGENTS.md` mandates reading `node_modules/next/dist/docs/` before writing App
  Router code** — this Next.js 16 differs from training data. `sdd-design` and the first
  routing work unit MUST consult those docs for route groups, layouts, and client navigation
  rather than assuming familiar APIs.
- Backend, `mobile/`, and all `uml_modeling` code are untouched. No migration, no new env var
  beyond restoring the documented `NEXT_PUBLIC_API_URL` example.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `frontend/src/lib/api.ts` | **Modified** | Credentials, CSRF priming + `X-CSRFToken`, JSON, `ApiError` |
| `frontend/src/lib/auth.ts`, `lib/organizations.ts` | New | Typed clients, one per backend app |
| `frontend/src/state/` | New | Jotai session + organization atoms, `useSession()` |
| `frontend/src/components/auth/`, `components/workspace/` | New | Forms, guard, topbar, switcher, empty state |
| `frontend/src/app/(auth)/`, `app/(app)/` | New | Route groups, layouts, `/login` `/register` `/dashboard` |
| `frontend/env.local.example` | New (restored) | Referenced by README/compose/`env.ts`; currently missing |
| `frontend/src/app/page.tsx`, `components/landing/` | Untouched* | *unless the question round changes the navbar answer |
| `frontend/package.json` | Untouched | No new dependency (D7) |
| `backend/` | Untouched | Cycle-2 contract is frozen |
| `openspec/specs/` | New | Two new capability specs |
| `docs/ai/CURRENT_STATE.md`, `DECISIONS_LOG.md`, `NEXT_STEPS.md` | Modified | Dual-documentation convention; D1–D8 |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Next.js 16 App Router APIs differ from assumed knowledge (`frontend/AGENTS.md` warns explicitly) | **High** | Design and the first routing unit read `node_modules/next/dist/docs/` before writing; no App Router API used from memory |
| A caller bypasses the credentialed path and silently makes an anonymous request | Medium | `credentials`/CSRF are non-optional inside `apiFetch` (D3), with direct tests; no second fetch path exists |
| CSRF token rotates on login/logout (Django rotates it with the session), leaving a cached token stale → 403 | Medium | Never cache the token in a module variable; read `document.cookie` at request time, and re-prime once on a CSRF 403 before failing (single retry, no loop) |
| `401` from `/api/auth/me` confused with a network/backend failure, logging users out on an outage | Medium | D4 separates the two states explicitly; error state renders retry, only `401` redirects |
| Flash of protected content, or of the login form, before session resolution | Medium | Guard renders a skeleton until `sessionAtom` leaves `loading`; asserted by test |
| Real cross-origin cookie behaviour (SameSite=Lax, ports 3000→8000) only verified against mocked fetch | Medium | Backend `test_cross_origin_session.py` already proves the server side; add a manual smoke checklist to `CURRENT_STATE.md`; Cypress remains deferred tech debt |
| Scope creep into membership management, org editing, or the canvas | **High** | Out-of-Scope is explicit; membership endpoints exist and are deliberately unconsumed |
| A user with zero organizations reaches a dead-end panel | Medium | The zero-org empty state is an in-scope deliverable, not an afterthought (see question round Q1) |

## Rollback Plan

Cheaper than Cycle 2 — this cycle adds no schema, no migration, no dependency, and no
backend change.

1. **Full**: `git revert` the cycle commits. The landing page, the backend, and the database
   are untouched by every path here.
2. **Partial (routes only)**: delete `src/app/(auth)/` and `src/app/(app)/`. The app returns
   to a single-route landing site; `lib/` improvements are harmless when unused.
3. **Partial (transport only)**: reverting `lib/api.ts` alone breaks the new screens but
   nothing else — the landing page never calls it.
4. `frontend/env.local.example` is additive and never needs reverting.

## Dependencies

- **No new package dependencies.** `jotai`, `tailwindcss`, `shadcn`, `vitest`,
  `@testing-library/react` are already installed.
- **A running backend** at `NEXT_PUBLIC_API_URL` with the Cycle-2 endpoints and the
  cross-origin cookie settings from `backend/env.example`
  (`CORS_ALLOW_CREDENTIALS=True`, `CORS_ALLOWED_ORIGINS=http://localhost:3000`,
  `SAMESITE=Lax`, `SECURE=False`) — required for manual verification, not for the unit tests.
- Builds on archived Cycle 2 (`multi-tenant-identity`) and **does not modify it**.
- **Blocks / is a prerequisite for**: every future authenticated frontend surface — the UML
  canvas, project listing, membership management, and realtime collaboration UI.

## Explicit Tech Debt (section 38)

1. **No server-side route protection.** A protected route ships its JS shell to anonymous
   visitors before redirecting (D1). Harmless while no protected content is SSR-rendered;
   must be revisited before the canvas.
2. **No E2E coverage of the real cookie flow.** Cypress is still not bootstrapped; the
   cross-origin session round trip is proven server-side and by hand, not in CI.
3. **Membership management UI absent** — the endpoints exist and nothing calls them.
4. **Organization rename/delete UI absent** despite existing endpoints.
5. **`my_role` is displayed but gates nothing** — no role-conditional UI.
6. **No token refresh / session-expiry UX.** An expired session surfaces as a redirect to
   login on the next request, with no warning and no in-flight-request recovery.
7. **No tenant-scoped route exists yet**, so backend D3's URL-path tenancy rule is stated in
   D5 but not exercised by any page.
8. **Password reset, email verification, MFA, social login** — absent frontend *and* backend.
9. **No loading/error design system.** Skeletons and retry states are built per-screen this
   cycle rather than as shared primitives.

## Success Criteria

- [ ] `apiFetch` sends `credentials: "include"` on every request; a test asserts it.
- [ ] An unsafe request with no `csrftoken` cookie primes it via `GET /api/auth/csrf` and
      sends `X-CSRFToken`; a test asserts both, and asserts priming is skipped when the
      cookie is already present.
- [ ] A visitor can register at `/register` and arrives authenticated in the panel.
- [ ] A registered user can log in at `/login` and log out from the panel; after logout,
      returning to a protected route redirects to `/login`.
- [ ] An anonymous visitor hitting `/dashboard` is redirected to `/login?next=/dashboard`
      and, after logging in, lands on `/dashboard`.
- [ ] A backend outage on `/api/auth/me` renders a retry state, **not** a redirect to login.
- [ ] Protected content is never rendered while the session is `loading`.
- [ ] The panel lists the user's organizations with name and role, and switching the active
      one persists across a reload.
- [ ] A user with zero organizations sees a purposeful empty state that leads to creation.
- [ ] Creating an organization succeeds and the new organization appears in the list as
      `OWNER` without a manual refresh.
- [ ] A duplicate slug (`409`) surfaces the backend's `detail` message on the form, not a
      generic crash.
- [ ] `frontend/env.local.example` exists and `cp frontend/env.local.example frontend/.env.local`
      (README step 3) works.
- [ ] `cd frontend && npm test` is green; `npm run lint` is clean; `backend/` is
      byte-for-byte unchanged.
- [ ] `docs/ai/CURRENT_STATE.md` and `DECISIONS_LOG.md` record the real post-cycle state and
      decisions D1–D8.

## Proposal question round (resolved)

Session strategy (D1) and cycle scope are already fixed by the project owner and were not
reopened here. The project owner confirmed all four stated assumptions below as written —
no changes to the approach.

1. **Zero-organization onboarding.** Registration authenticates the user immediately, but a
   brand-new user belongs to no organization. *Assumed*: `/dashboard` is reachable and shows
   a "create your first organization" empty state — creation is encouraged, never forced.
   The alternative is a blocking onboarding step that redirects to a dedicated
   `/onboarding/organization` until one exists. Which reads better for the demo?
2. **UI copy language.** Existing UI copy (landing page) and the backend's role labels
   (`Propietario` / `Editor` / `Lector`) are Spanish. *Assumed*: all new auth and panel copy
   is **Spanish**, while code, identifiers, and comments stay English per the project's
   artifact-language convention. Confirm — this is expensive to flip later.
3. **Landing page navbar.** The landing page currently has no way in. *Assumed*: the navbar
   gains "Iniciar sesión" and "Registrarse" links (a small, contained edit to
   `components/landing/Navbar.tsx`), and shows "Ir al panel" instead when a session exists.
   The stricter alternative leaves the landing page byte-for-byte untouched and makes
   `/login` reachable only by typing the URL — safer for the diff, worse for the demo.
4. **Where logout lands.** *Assumed*: logging out returns the user to the landing page `/`
   rather than to `/login`, on the grounds that a deliberate logout is an exit, not a
   prelude to logging back in.
