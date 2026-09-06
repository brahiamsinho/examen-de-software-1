# Tasks: Cycle 3 — Frontend Auth Integration (Session, Panel, Organizations)

Strict TDD (`openspec/config.yaml: strict_tdd: true`). Test command: `cd frontend && npm test`
(`vitest run`). This change is frontend-only; `backend/` is not touched and no backend test
runs. Work order follows design.md's dependency chain — do not reorder:
`env.local.example` → `lib/api.ts` → `lib/auth.ts` + `lib/organizations.ts` → `state/*` →
`SessionGuard` + layouts → auth screens → org panel → `Navbar.tsx` → docs.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1500–1700 (1 restored config file, 2 modified files, ~18 new source/test files; ~650–750 authored source + ~850–950 test lines) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (env + transport + domain clients) → PR 2 (state + guard/layouts + auth screens) → PR 3 (org panel + navbar + docs) |
| Delivery strategy | ask-on-risk |
| Chain strategy | Not yet resolved for this change — ask before `sdd-apply` starts, mirroring how Cycle 2 (`multi-tenant-identity`) resolved `stacked-to-main` for its own 3-PR split |

Decision needed before apply: **Yes** — confirm chained-PR strategy (stacked-to-main vs. independent) before starting Phase 1.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Rollback boundary |
|------|------|-----------|----------------------|--------------------|
| 1 | `env.local.example`, `lib/api.ts` transport rewrite, `lib/auth.ts`, `lib/organizations.ts` | PR 1 | `cd frontend && npx vitest run src/lib` | Revert `lib/api.ts` alone (landing page never calls it); delete `lib/auth.ts`, `lib/organizations.ts`; `env.local.example` is additive, never needs reverting |
| 2 | `state/session.ts`, `state/organizations.ts`, `SessionGuard`, `(auth)`/`(app)` layouts, `LoginForm`, `RegisterForm`, `/login`, `/register` | PR 2 | `cd frontend && npx vitest run src/state src/components/auth src/app/\(auth\)` | Delete `app/(auth)/`; `state/` and `components/auth/` become unused but harmless — PR 1 stays valid standalone |
| 3 | `AppTopbar`, `OrgSwitcher`, `CreateOrgForm`, `OrgEmptyState`, `/dashboard`, `Navbar.tsx` edit, docs | PR 3 | `cd frontend && npx vitest run src/components/workspace src/app/\(app\) src/components/landing/__tests__/Navbar.test.tsx` | Delete `app/(app)/` and `components/workspace/`; revert `Navbar.tsx` to its pre-cycle diff (existing `Empezar gratis` test stays green either way) |

## Phase 0: Environment Setup (blocks the documented `npm run dev` flow, not tests)

- [x] 0.1 Create `frontend/env.local.example` with one line: `NEXT_PUBLIC_API_URL=http://localhost:8000` (D6). Not a TDD unit — plain config file, no test asserts its contents.
- [x] 0.2 Verify `cp frontend/env.local.example frontend/.env.local` matches README step 3 and `lib/env.ts`'s expected variable name.

## Phase 1: Transport Seam — `lib/api.ts` (blocks every later phase; FEA-C3-1, spec `web-session` § Credentialed CSRF-Aware Transport)

- [x] 1.1 RED: `frontend/src/lib/__tests__/api.test.ts` — credentialed request asserts `credentials: "include"` on every call (`fetch` stubbed via `vi.stubGlobal`).
- [x] 1.2 RED (same file): CSRF priming fires (`GET /api/auth/csrf`) before an unsafe request when no `csrftoken` cookie is present, and is skipped when the cookie already exists.
- [x] 1.3 RED (same file): `X-CSRFToken` header attached on unsafe methods (POST/PUT/PATCH/DELETE), absent on GET.
- [x] 1.4 RED (same file): a 403 on an unsafe request triggers exactly one re-prime + retry (`invalidateCsrfToken()` then re-fetch token); a second 403 surfaces as `ApiError`, no loop.
- [x] 1.5 RED (same file): non-2xx response normalizes into typed `ApiError { status, code, detail }` — missing `code` on a django_auth 401 becomes `"http_401"`; a Ninja 422 array `detail` is coerced via `JSON.stringify`; a fetch rejection (no response) becomes `NetworkError`, distinct from `ApiError`; a 204 resolves to `undefined`.
- [x] 1.6 GREEN: rewrite `frontend/src/lib/api.ts` — `apiFetch<T>(path, init: Omit<RequestInit,"credentials">)`, `ApiError`, `NetworkError`, `csrfToken()` (cookie fast path → module cache → `GET /api/auth/csrf` body token, DD2), `invalidateCsrfToken()`. Confirm 1.1–1.5 all pass.
- [x] 1.7 REFACTOR: extract cookie-read and JSON-detail-normalization helpers if `apiFetch` grows past one clear responsibility per block; re-run 1.1–1.5 after each extraction. (Already one responsibility per block — `readCsrfCookie`/`toApiError`/`primeCsrfToken` were extracted directly during GREEN; no further extraction needed.)

## Phase 2: Domain Clients — `lib/auth.ts`, `lib/organizations.ts` (depends on Phase 1; FEA-C3-2, FEA-C3-3, FEA-C3-5, FEA-C3-6)

- [x] 2.1 RED: `frontend/src/lib/__tests__/auth.test.ts` — `register(...)` posts to `/api/auth/register` and returns `User`; `login(...)` posts to `/api/auth/login`; `logout()` posts to `/api/auth/logout`; `fetchMe()` gets `/api/auth/me`; `login`/`logout` each call `invalidateCsrfToken()` after resolving (Django rotates the token on both). **Deviation**: used design.md's "Interfaces" contract (object-arg signatures, `fetchMe` name) over tasks.md's prose (positional args, `getMe` name) — see Deviations note below.
- [x] 2.2 GREEN: `frontend/src/lib/auth.ts` implementing all four functions on top of `apiFetch`.
- [x] 2.3 RED: `frontend/src/lib/__tests__/organizations.test.ts` — `listOrganizations()` gets `/api/orgs` returning `Organization[]`; `createOrganization({name, slug})` posts `/api/orgs`, returns the created `Organization` (`my_role: "OWNER"`). **Deviation**: `slug` is required — backend `OrganizationIn` has no slug default — matching design.md's Interfaces signature, not tasks.md's `createOrganization(name)` shorthand.
- [x] 2.4 GREEN: `frontend/src/lib/organizations.ts` implementing both functions.

## Phase 3: Jotai State (depends on Phase 2; FEA-C3-4, FEA-C3-5)

- [ ] 3.1 RED: `frontend/src/state/__tests__/session.test.ts` (fresh `jotai` `<Provider>` per test) — `useSession()` fires `getMe()` once per mount; `ApiError` with `status: 401` → `{status:"anonymous"}`; `NetworkError` or any other `ApiError` → `{status:"error", message}` (an outage must not resolve to `anonymous`); success → `{status:"authenticated", user}`.
- [ ] 3.2 GREEN: `frontend/src/state/session.ts` — `sessionAtom` discriminated union (`loading|authenticated|anonymous|error`), `useSession()` hook owning the single fetch.
- [ ] 3.3 RED: `frontend/src/state/__tests__/organizations.test.ts` (localStorage cleared per test) — `useOrganizations()` reads persisted active slug in a post-mount effect; persisted slug still present in the fetched list stays active; persisted slug absent/stale falls back to the first listed org; creating an org appends it optimistically to `organizationsAtom` and sets it active without a refetch (DD7).
- [ ] 3.4 GREEN: `frontend/src/state/organizations.ts` — `organizationsAtom`, `activeOrgSlugAtom`, `useOrganizations()` hook (plain atom + explicit effect, not `atomWithStorage`, per DD6).

## Phase 4: Guard + Route-Group Layouts (depends on Phase 3; FEA-C3-4, spec `web-session` § Session State and Route Protection)

- [ ] 4.1 Read `node_modules/next/dist/docs/` — specifically the "Interleaving Server and Client Components" section of `05-server-and-client-components.md` and the generated `frontend/.next/types/routes.d.ts` shape — before writing any route-group code (mandated by `frontend/AGENTS.md`; this is the first App Router work unit in the cycle). Confirm DD3 (children-as-prop keeps the client boundary out of the RSC payload for children) and DD4 (route groups both key on `"/"` in `LayoutRoutes`) against what's actually generated; note any divergence as a deviation before proceeding.
- [ ] 4.2 RED: `frontend/src/lib/__tests__/next-path.test.ts` (or colocated with the guard test) — pure function `safe(next)` accepts only a single-leading-slash relative path (`/dashboard`) and falls back to `/dashboard` for absolute/protocol-relative input (`//evil.com`, `https://evil.com`), tested apart from any component per the design's routing-contract testing strategy.
- [ ] 4.3 GREEN: implement `safe()` (colocated with `SessionGuard` or in `lib/`).
- [ ] 4.4 RED: `frontend/src/components/auth/__tests__/SessionGuard.test.tsx` (`next/navigation` mocked to capture `router.replace`) — renders a skeleton and no protected `children` while `sessionAtom.status === "loading"`; on `anonymous`, calls `router.replace("/login?next=" + encodeURIComponent(pathname))` and renders nothing else; on `error`, renders a retry panel and does **not** call `router.replace`; on `authenticated`, renders `children`.
- [ ] 4.5 GREEN: `frontend/src/components/auth/SessionGuard.tsx` as a Client Component receiving `children` as a prop (DD3).
- [ ] 4.6 Create `frontend/src/app/(auth)/layout.tsx` (Server Component, centered card shell, explicit `{children: React.ReactNode}` typing per DD4, no guard).
- [ ] 4.7 Create `frontend/src/app/(app)/layout.tsx` (Server Component rendering `<SessionGuard><AppTopbar/>{children}</SessionGuard>`, explicit `{children: React.ReactNode}` typing).

## Phase 5: Auth Screens (depends on Phase 4; FEA-C3-2, FEA-C3-3, spec `web-session` § Registration, § Login and Logout)

- [ ] 5.1 RED: `frontend/src/components/auth/__tests__/LoginForm.test.tsx` — successful login (correct credentials) transitions session to authenticated and redirects per `next`-resolution; invalid credentials render one generic inline error and session stays anonymous (no field-level leakage of which field was wrong).
- [ ] 5.2 GREEN: `frontend/src/components/auth/LoginForm.tsx` (plain React state, existing `components/ui/button.tsx`, no new dependency per D7).
- [ ] 5.3 RED: `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` — successful registration (unique email + valid password) authenticates and redirects to `/dashboard`; duplicate email shows the backend's `detail` inline and session stays anonymous.
- [ ] 5.4 GREEN: `frontend/src/components/auth/RegisterForm.tsx`.
- [ ] 5.5 Wire `frontend/src/app/(auth)/login/page.tsx` rendering `LoginForm`, and `frontend/src/app/(auth)/register/page.tsx` rendering `RegisterForm`. Copy in Spanish (proposal Q2: "Iniciar sesión" / "Registrarse" / error text), identifiers/comments in English.
- [ ] 5.6 RED: logout — extend an existing panel-adjacent test (or a small `AppTopbar` smoke test introduced early) asserting a logout action calls `logout()`, clears session state, and redirects to `/` (D4/proposal Q4). This may be folded into Phase 6's `AppTopbar` tests if the topbar is the only logout affordance — do not duplicate coverage.

## Phase 6: Organization Panel (depends on Phase 3 state + Phase 4 guard + Phase 5 screens landing the routing pattern; FEA-C3-5, FEA-C3-6, spec `web-organization-workspace`)

- [ ] 6.1 RED: `frontend/src/components/workspace/__tests__/OrgSwitcher.test.tsx` — given two memberships, both list with their role; selecting one persists the active slug (mock/read `localStorage`); a stale persisted slug (matching no membership) falls back to the first listed org.
- [ ] 6.2 GREEN: `frontend/src/components/workspace/OrgSwitcher.tsx`.
- [ ] 6.3 RED: `frontend/src/components/workspace/__tests__/OrgEmptyState.test.tsx` — zero-membership state renders a non-blocking "create your first organization" prompt (proposal Q1), not a redirect.
- [ ] 6.4 GREEN: `frontend/src/components/workspace/OrgEmptyState.tsx`.
- [ ] 6.5 RED: `frontend/src/components/workspace/__tests__/CreateOrgForm.test.tsx` — successful creation (unique name) appears in the list with role `OWNER` and becomes active without a manual refetch; duplicate slug (409) surfaces `ApiError.detail` verbatim under the name/slug field, no org added.
- [ ] 6.6 GREEN: `frontend/src/components/workspace/CreateOrgForm.tsx`.
- [ ] 6.7 RED: `frontend/src/components/workspace/__tests__/AppTopbar.test.tsx` — renders `OrgSwitcher`, a logout control that calls `logout()` and redirects to `/` on click (completes 5.6 if not already covered).
- [ ] 6.8 GREEN: `frontend/src/components/workspace/AppTopbar.tsx`.
- [ ] 6.9 Wire `frontend/src/app/(app)/dashboard/page.tsx` — renders `OrgEmptyState` when `organizationsAtom` is empty, otherwise the org list/detail view plus `CreateOrgForm`. A component-level test (or extension of 6.5/6.3) asserts the empty-state vs. populated branching.
- [ ] 6.10 REFACTOR: if `OrgSwitcher`/`CreateOrgForm`/`OrgEmptyState` duplicate list-rendering or role-label logic, extract a shared presentational helper; re-run Phase 6 tests after each extraction.

## Phase 7: Landing Navbar Integration (depends on Phase 3 state + Phase 5 routes existing; proposal Q3)

- [ ] 7.1 RED: extend `frontend/src/components/landing/__tests__/Navbar.test.tsx` — anonymous session renders "Iniciar sesión" (→ `/login`) and "Registrarse" (→ `/register`) links; authenticated session renders "Ir al panel" (→ `/dashboard`) instead. Confirm both pre-existing assertions (the `Empezar gratis` → `#precios` anchor) still pass unchanged.
- [ ] 7.2 GREEN: edit `frontend/src/components/landing/Navbar.tsx` — replace the dead `<a href="#">Iniciar sesión</a>` at line 30 with `<Link href="/login">`, add the `Registrarse` link, and the session-aware `Ir al panel` branch. Read `sessionAtom` via `useSession()`/`useAtomValue` — landing stays outside `(app)`, so this is the one place outside the guard that reads session state.

## Phase 8: Full-Suite Verification & Docs

- [ ] 8.1 Run `cd frontend && npm test` — full suite green, including every existing landing/button test untouched by this cycle.
- [ ] 8.2 Run `cd frontend && npm run lint` — clean.
- [ ] 8.3 Confirm `backend/` is byte-for-byte unchanged (`git status backend/` empty for this change).
- [ ] 8.4 Update `docs/ai/CURRENT_STATE.md` and `docs/ai/DECISIONS_LOG.md` with D1–D8 (and any DD-level deviations discovered during apply, following the Cycle 2 deviation-note convention).
- [ ] 8.5 Document the manual smoke checklist in `docs/ai/CURRENT_STATE.md` (real cross-origin cookie flow, not automated this cycle): register → reload → still authenticated; logout → `/`; backend stopped + load `/dashboard` → retry panel, not `/login`.
