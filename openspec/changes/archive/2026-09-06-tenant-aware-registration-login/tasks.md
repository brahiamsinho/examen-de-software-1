# Tasks: Tenant-Aware Registration & Login

Strict TDD (`strict_tdd: true`). Backend: `cd backend && pytest`. Frontend: `cd frontend && npm test -- --run`.
Backend (Phases 1–4) and Frontend (Phases 5–8) are independent file sets and MAY be worked in parallel;
Phase 9 depends on both. Within each track, phases are strictly sequential (dependency chain per design.md).

## Review Workload Forecast

Session budget for this change is **800** changed lines (not the tool default of 400).

| Field | Value |
|---|---|
| Estimated changed lines | ~600–750 (backend ~215: 3 new helpers, 1 new property-test file, 3 modified test files; frontend ~380: 3 new files, 6 modified files, tests) |
| 400-line budget risk (using the 800 threshold) | Medium — no migration, no schema change, but close enough to the budget that a diff-count check before merge is warranted |
| Chained PRs recommended | No — estimate stays under the 800-line budget with headroom |
| Suggested split | Single PR (backend + frontend); optional informal split below for reviewer ergonomics only |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Backend slug helpers + atomic registration provisioning | Single PR | `cd backend && pytest apps/organizations apps/users` | `django_db` fixture; PostgreSQL already required | Revert `organizations/services.py` additions + `users/services.py` decorator; `create_organization` untouched |
| 2 | Frontend safe-next + login/register branching + picker route | Single PR | `cd frontend && npx vitest run src/lib src/state src/components/auth src/components/workspace src/app/\(gate\)` | RTL + mocked `lib/auth`/`lib/organizations` | Revert `LoginForm`/`RegisterForm`; delete `app/(gate)/`, `OrgPicker.tsx`, `roleLabels.ts` import in `OrgSwitcher.tsx` |

## Phase 1: Backend — Pure Slug/Name Helpers (organization-tenancy § Server-Generated Organization Slug)

- [x] 1.1 RED: `backend/apps/organizations/tests/test_slug_properties.py` (new) — `hypothesis` properties: `build_slug_base` always 1–40 chars, url-safe; `derive_workspace_name` always ends with `"'s Workspace"`, ≤120 chars.
- [x] 1.2 GREEN: add `derive_workspace_name`, `build_slug_base` to `backend/apps/organizations/services.py`.
- [x] 1.3 RED: `test_services_organizations.py` — `"Acme Corp"` → base `acme-corp`; a non-Latin source → literal `workspace` base.
- [x] 1.4 GREEN: confirm 1.3 passes against 1.2's implementation; refactor only if duplication appears.

## Phase 2: Backend — DB-Touching Slug Generator (organization-tenancy § Server-Generated Organization Slug)

- [x] 2.1 RED: `test_services_organizations.py` — first attempt is never a bare base; 4 pre-existing collisions force a 5th attempt; all 5 collide → attempt-6 `workspace-{16hex}` fallback; total exhaustion raises `OrganizationError`; length always ≤47 chars. Patch `secrets.token_hex` to a fixed sequence.
- [x] 2.2 GREEN: add `generate_unique_slug` to `organizations/services.py` (`.exists()` pre-check, no retry-around-`IntegrityError`).

## Phase 3: Backend — Transactional Registration (user-authentication: Registration Provisions One Organization; Registration)

- [x] 3.1 RED: `backend/apps/users/tests/test_services_auth.py` — registration creates exactly one `Organization` + `OWNER` `Membership`; monkeypatching `generate_unique_slug` to raise `OrganizationError` rolls back the `User` (assert `User.objects.count() == 0`).
- [x] 3.2 GREEN: decorate `register_user` with `@transaction.atomic`; call `create_organization(owner=user, name=derive_workspace_name(...), slug=generate_unique_slug(...))` in `backend/apps/users/services.py`.
- [x] 3.3 RED→GREEN: invert `test_registration_does_not_auto_create_an_organization` in `backend/apps/users/tests/test_api_auth.py` to assert exactly one organization exists after registration.

## Phase 4: Backend — seed_demo Consistency (Affected Area: seed_demo)

- [x] 4.1 RED: `backend/apps/organizations/tests/test_management_seed_demo.py` — add assertion that each demo user owns exactly one auto-provisioned personal workspace in addition to `acme-demo`.
- [x] 4.2 GREEN: update `seed_demo.py` docstring/`help` text only (no logic change); re-run `call_command` twice to confirm idempotency still holds (no duplicate personal orgs).

## Phase 5: Frontend — Safe Next-Path Predicate (web-session § Login and Logout precedence; Threat Matrix: open redirect)

- [x] 5.1 RED: `frontend/src/lib/__tests__/next-path.test.ts` — `isSafeNext` accepts a single-leading-slash path; rejects `//evil.com`, `https://evil.com`, `javascript:...`, `null`.
- [x] 5.2 GREEN: add `isSafeNext` to `frontend/src/lib/next-path.ts`; re-express `safe()` through it, byte-identical behavior.

## Phase 6: Frontend — Active-Org Write Hook (DD5, DV1)

- [x] 6.1 RED: `frontend/src/state/__tests__/organizations.test.ts` — `useSetActiveOrg(slug)` sets `activeOrgSlugAtom` and writes `localStorage`.
- [x] 6.2 GREEN: add `useSetActiveOrg` to `frontend/src/state/organizations.ts`; `useOrganizations` consumes it (no duplicated logic).

## Phase 7: Frontend — Login/Register Branching (web-session § Login and Logout 0/1/2+/next precedence; § Registration adoption scenario)

- [x] 7.1 RED: `frontend/src/components/auth/__tests__/LoginForm.test.tsx` — 0 orgs → `/dashboard`; 1 org → `setActiveOrg` + `/dashboard`, no picker; 2+ orgs → `/select-organization`; a precedence-winning `next` beats all branches; org-fetch failure after successful login falls back to `/dashboard` without reusing the login error.
- [x] 7.2 GREEN: rewrite `LoginForm.tsx`'s submit handler per DD3 — call `listOrganizations()` directly, never `useOrganizations()`.
- [x] 7.3 RED: `frontend/src/components/auth/__tests__/RegisterForm.test.tsx` — the sole provisioned org (from `listOrganizations()` post-register) becomes active before redirect.
- [x] 7.4 GREEN: update `RegisterForm.tsx` per DD6, fetch failure outside the existing error `catch`.

## Phase 8: Frontend — Post-Login Organization Picker (web-organization-workspace: Post-Login Organization Picker)

- [x] 8.1 Extract `frontend/src/components/workspace/roleLabels.ts` (new) from `OrgSwitcher.tsx`'s private `ROLE_LABELS` (DV3); `OrgSwitcher.tsx` imports it — no behavior change.
- [x] 8.2 RED: `frontend/src/components/workspace/__tests__/OrgPicker.test.tsx` (new) — every organization lists with its role label; `onSelect` fires with the chosen slug.
- [x] 8.3 GREEN: create `OrgPicker.tsx` (presentational, props `{organizations, onSelect}`, no `activeSlug`).
- [x] 8.4 Create `frontend/src/app/(gate)/layout.tsx` (new) — `SessionGuard` + centered-card shell, no topbar (DD4); explicit `{children: React.ReactNode}` typing.
- [x] 8.5 RED: `frontend/src/app/(gate)/select-organization/__tests__/page.test.tsx` (new) — selection sets active org and persists across a reload; a list with `<2` orgs redirects to `/dashboard`.
- [x] 8.6 GREEN: create `(gate)/select-organization/page.tsx` — `useOrganizations()` + `OrgPicker` + `setActiveOrg` then `router.replace("/dashboard")`.

## Phase 9: Verification & Docs

- [x] 9.1 Run `cd backend && pytest` — full suite green; confirm no new file under any `migrations/` directory.
- [x] 9.2 Run `cd frontend && npm test -- --run` — full suite green, including all pre-existing tests.
- [x] 9.3 Update `docs/ai/CURRENT_STATE.md` and `docs/ai/DECISIONS_LOG.md` recording D1–D8 (dual-documentation convention).
