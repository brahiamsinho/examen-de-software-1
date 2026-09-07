# Tasks: Server-Enforced Protected Routes

Strict TDD. Frontend-only change (N2). Test runner: `cd frontend && npm test -- --run`.

## Review Workload Forecast

Session budget for this change is **800** changed lines.

| Field | Value |
|---|---|
| Estimated changed lines | ~400–500 (2 new files ~285 lines incl. tests, 2 new test files ~50 lines, 2 modified layouts ~30 lines, `env.ts` +14, `env.test.ts` ~50 new, docker-compose/env.local.example ~10, docs ~60) |
| 400-line budget risk (vs. 800 threshold) | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | `internalApiUrl` config (foundation) | Single PR | `cd frontend && npx vitest run src/lib/__tests__/env.test.ts` | N/A — pure unit test, no server needed | Revert `env.ts` addition; additive, no callers yet |
| 2 | `server-session.ts` core logic | Single PR | `cd frontend && npx vitest run src/lib/__tests__/server-session.test.ts` | N/A — `next/headers`/`next/navigation`/`fetch` fully mocked (DD7) | Delete `server-session.ts` + its test; unused until Unit 3 wires it |
| 3 | Layout wiring, config, docs, manual verification | Single PR | `cd frontend && npm test -- --run` (full regression) | `docker compose up -d --build` + `docker compose exec backend python manage.py seed_demo`, then DD8's 8-step `curl` checklist — no automated substitute exists (D6) | Revert both layout files to synchronous; `SessionGuard` stays untouched so client-side protection is never absent (proposal Rollback step 1) |

## Phase 1: `lib/env.ts` — `internalApiUrl` (Foundation, DD5)

- [x] 1.1 RED: `frontend/src/lib/__tests__/env.test.ts` (new) — 2 cases (DV3): `internalApiUrl` equals `INTERNAL_API_URL` when set; equals `apiUrl` when unset. Use `vi.stubEnv` + `vi.resetModules()` + dynamic `await import("@/lib/env")`.
- [x] 1.2 GREEN: add `readInternalApiUrl()` + `export const internalApiUrl` to `frontend/src/lib/env.ts`, appended after `apiUrl` per DD5's exact code. Never throws.

## Phase 2: `lib/server-session.ts` — `getServerUser()` (Core Implementation, DD1)

- [x] 2.1 RED: `frontend/src/lib/__tests__/server-session.test.ts` (new) — scaffold `vi.hoisted` mocks for `next/navigation` (`redirect` throws `NEXT_REDIRECT:<url>`), `next/headers` (`cookies().toString()` returns a controllable jar), `@/lib/env` (DD7). Cases 1–9: whole jar forwarded verbatim as `cookie`; no `cookie` header when jar empty; always `cache: "no-store"`; targets `internalApiUrl`, not `apiUrl`; `200` → parsed `User`; `401` → `null`; `403` → `null`; `500` → throws; `fetch` rejects → throws.
- [x] 2.2 GREEN: implement `getServerUser` in `frontend/src/lib/server-session.ts` per design DD1's exact code (React `cache()`-wrapped, `(await cookies()).toString()`, `fetch(new URL("/api/auth/me", internalApiUrl), { cache: "no-store" })`, status branching). Cases 1–9 pass.

## Phase 3: `lib/server-session.ts` — `requireUser()` (Core Implementation, DD1/DV1/DV2)

- [x] 3.1 RED: extend `server-session.test.ts` — cases 10–13: `requireUser` returns the user on `200`; redirects to `/login?next=%2Fdashboard` on `401`; a hostile `nextPath` (`//evil.com`) collapses to `%2Fdashboard` via `safe()` (threat matrix — open redirect); does NOT redirect when `getServerUser` throws, returns `null` instead (threat matrix — outage misread as logout).
- [x] 3.2 GREEN: implement `requireUser(nextPath: string)` in `server-session.ts` per DD1 — `try/catch` around `getServerUser` returning `null` on throw (DV2), `redirect` call outside the `try/catch`, target built with `encodeURIComponent(safe(nextPath))`. All 13 cases pass.
- [x] 3.3 REFACTOR: verify `server-session.ts`'s docblock and imports (`cookies`, `redirect`, `cache`, `User` from `@/lib/auth`, `internalApiUrl`, `safe`) match DD1 exactly; no behavior change.

## Phase 4: Layout Wiring (Integration, DD6 — no automated test possible, D6)

- [x] 4.1 Modify `frontend/src/app/(app)/layout.tsx`: import `requireUser`, make the component `async`, add `await requireUser("/dashboard")` as the first statement; rewrite the docblock per DV4 (its current "Under D1 there is no server session" assertion is now false). JSX (`<SessionGuard><AppTopbar />{children}</SessionGuard>`) stays byte-identical (D4/N8).
- [x] 4.2 Modify `frontend/src/app/(gate)/layout.tsx`: same pattern with `await requireUser("/select-organization")`. No docblock rewrite needed.

## Phase 5: Config

- [x] 5.1 Modify `docker-compose.yml`: add `INTERNAL_API_URL: http://backend:8000` under `frontend.environment`.
- [x] 5.2 Modify `frontend/env.local.example`: add commented `INTERNAL_API_URL` plus a note on the cross-domain deployment precondition (browser must send `sessionid` to the Next.js origin).

## Phase 6: Manual Verification (Mandatory, D6/DD8 — layout wiring has no automated test)

- [x] 6.1 With `docker compose up -d --build` healthy and `docker compose exec backend python manage.py seed_demo` run once, execute DD8's 8 steps verbatim and confirm each expected result (7/8 literal checks match; step 3 diverges from DD8's literal `rg -c` check — see apply-progress/report deviation DV6, the underlying spec property still holds on manual inspection):
  1. `curl -s -o body.txt -w "%{http_code}\n" http://localhost:3000/dashboard` → `307`.
  2. `curl -sI http://localhost:3000/dashboard | rg -i '^location:'` → `location: /login?next=%2Fdashboard`.
  3. `rg -c "<html" body.txt` → no match.
  4. Repeat 1–3 with `-H "Cookie: sessionid=deadbeefdeadbeefdeadbeefdeadbeef"` → identical `307`.
  5. Repeat 1–3 for `/select-organization` → `307`, `next=%2Fselect-organization`.
  6. Log in a `seed_demo` account into `jar.txt` against `localhost:8000`, then `curl -s -o body.txt -w "%{http_code}\n" -b jar.txt http://localhost:3000/dashboard` → `200`, body contains `<html`.
  7. `curl -s -w "%{http_code}\n" -b jar.txt http://localhost:3000/select-organization` → `200`.
  8. `docker compose stop backend`, repeat 6, then `docker compose start backend` → not `307`, a rendered document.

## Phase 7: Documentation

- [x] 7.1 Update `docs/ai/CURRENT_STATE.md` — record server-enforced route protection is live.
- [x] 7.2 Update `docs/ai/DECISIONS_LOG.md` — record D1–D8 and DV1–DV5.
- [x] 7.3 Update `README.md` and `docs/ai/ARCHITECTURE.md` (repo has no root `ARCHITECTURE.md`; the project's architecture doc lives at `docs/ai/ARCHITECTURE.md`) — document the cross-domain deployment precondition (proposal Risks; design Migration/Rollout).

## Phase 8: Final Verification

- [x] 8.1 Run `cd frontend && npm test -- --run` — full suite green, including all 15 new cases and the unmodified `SessionGuard.test.tsx`, `api.test.ts`, `auth.test.ts`. Result: 29/29 files, 102/102 tests pass.
- [x] 8.2 Confirm `git diff --stat -- frontend/src/components/auth/SessionGuard.tsx frontend/src/components/auth/__tests__/SessionGuard.test.tsx` is empty (D4/N8). Confirmed empty.
- [x] 8.3 Confirm `git diff --stat -- backend/` is empty and no new file exists under any `migrations/` directory (N2). **Not literally empty**: `backend/env.example` gained 7 lines documenting `ALLOWED_HOSTS=localhost,127.0.0.1,backend` (see Phase 6 deviation — required to unblock the Docker-network `Host: backend:8000` rejection found during manual verification). Zero Django app code, models, schemas, or migrations changed; no file under any `migrations/` directory was added (confirmed via `git status`). 186/186 backend `pytest` tests pass unchanged.
- [x] 8.4 Walk proposal.md's Success Criteria checklist and confirm every item is satisfied by Phases 1–7. See apply-progress / final report for the full item-by-item walk (all satisfied; item "`git diff --stat backend/` is empty" is satisfied for app code but not literally for `backend/env.example`, called out above).
