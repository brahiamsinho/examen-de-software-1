# Tasks: Organization Member Management UI

Strict TDD. Test command: `cd frontend && npx vitest run <path>`. Frontend-only; `backend/` untouched.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~950–1050 (2 modified files, 6 new source files, 8 new/extended test files) |
| 400-line budget risk | High |
| Project budget (800) | Also projected to exceed |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (clients + state + repointing) → PR 2 (presentational components) → PR 3 (container page + topbar) |
| Delivery strategy | single-pr |
| Chain strategy | pending — decision required before `sdd-apply` |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

Given `delivery_strategy: single-pr`, this High estimate (~950–1050 lines, over both the 400-line default and this project's 800-line budget) means `sdd-apply` must not start until the orchestrator gets an explicit decision: accept `size:exception` for one ~1000-line PR, or override to a chained split using the work units below.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | `lib/organizations.ts` member clients + `state/organizations.ts` repointing + `state/members.ts` | PR 1 | `npx vitest run src/lib/__tests__/organizations.test.ts src/state/__tests__/organizations.test.ts src/state/__tests__/members.test.ts` | N/A — pure client/hook logic, no live backend call in tests (mocked `apiFetch`) | Revert all three files; no other file depends on them yet |
| 2 | `MembersList`, `MemberRow`, `AddMemberForm` | PR 2 | `npx vitest run src/components/workspace/__tests__/MembersList.test.tsx src/components/workspace/__tests__/MemberRow.test.tsx src/components/workspace/__tests__/AddMemberForm.test.tsx` | N/A — presentational, props-in/callback-out, no wiring yet | Delete the three new component files; unused but harmless if PR 1 already merged |
| 3 | `app/(app)/settings/members/page.tsx` + `AppTopbar.tsx` link | PR 3 | `npx vitest run "src/app/(app)/settings/members/__tests__/page.test.tsx" src/components/workspace/__tests__/AppTopbar.test.tsx` | Manual: `npm run dev`, log in as an OWNER, visit `/settings/members`, add/re-role/remove a member | Delete `app/(app)/settings/members/`; revert the `AppTopbar.tsx` link line only |

## Phase 1: Member Client (`lib/organizations.ts`)

- [x] 1.1 RED: extend `frontend/src/lib/__tests__/organizations.test.ts` with `listMembers` (GET `/api/orgs/{slug}/members`), `addMember` (POST, `{email,role}`), `changeMemberRole` (PATCH `/api/orgs/{slug}/members/{userId}`, `{role}`), `removeMember` (DELETE → `undefined` on 204).
- [x] 1.2 GREEN: add `Member` type + the four functions to `frontend/src/lib/organizations.ts` as thin `apiFetch` wrappers, no `try/catch` (DD1).

## Phase 2: Self-Removal Repointing (`state/organizations.ts`) — highest risk

- [x] 2.1 RED: extend `frontend/src/state/__tests__/organizations.test.ts` — extract `persistActiveOrgSlug(slug: string | null)`; `useSetActiveOrg` still sets/persists correctly through it.
- [x] 2.2 RED: `useLeaveOrganization()` repoints active org to the first remaining org (two-org case).
- [x] 2.3 RED: `useLeaveOrganization()` zero-remaining-org case ⇒ `activeOrgSlugAtom` becomes `null` and the storage key is removed (fixes the selection effect's early-return gap).
- [x] 2.4 RED: `useLeaveOrganization()` — `removeMember` rejection leaves atoms and storage untouched, no `router.replace` call.
- [x] 2.5 RED: `useLeaveOrganization()` — `localStorage.setItem` throwing still repoints atoms and redirects.
- [x] 2.6 RED: `useLeaveOrganization()` — atom writes are committed before `router.replace("/dashboard")` fires (mock `next/navigation`, assert call order).
- [x] 2.7 GREEN: implement `persistActiveOrgSlug` + `useLeaveOrganization(orgSlug, userId): Promise<void>` in `frontend/src/state/organizations.ts`; fix the zero-org early return.

## Phase 3: Members Hook (`state/members.ts`)

- [x] 3.1 RED: new `frontend/src/state/__tests__/members.test.ts` — `useMembers(null)` idle, no fetch; `useMembers(slug)` fetches on mount and refetches on slug change.
- [x] 3.2 RED (same file): `addMember`/`changeMemberRole`/`removeMember` update `members` from the awaited response, no refetch; rejection leaves `members` unchanged and rethrows.
- [x] 3.3 GREEN: `frontend/src/state/members.ts` — `useMembers(orgSlug: string | null)`, local `useState` per DD2.

## Phase 4: Presentational Components

- [x] 4.1 RED: `frontend/src/components/workspace/__tests__/MembersList.test.tsx` — email/role/self-marker per row, `aria-label="Miembros"`.
- [x] 4.2 GREEN: `frontend/src/components/workspace/MembersList.tsx`.
- [x] 4.3 RED: `frontend/src/components/workspace/__tests__/MemberRow.test.tsx` — OWNER row: role `<select>` shows current value disabled, never offers OWNER; EDITOR/VIEWER row: enabled `<select>` limited to EDITOR/VIEWER; remove-other hidden for non-owner and on own row; self-leave always rendered; row error shown only when `rowError.userId` matches.
- [x] 4.4 GREEN: `frontend/src/components/workspace/MemberRow.tsx`.
- [x] 4.5 RED: `frontend/src/components/workspace/__tests__/AddMemberForm.test.tsx` — role selector offers only EDITOR/VIEWER; submit calls `onAdd({email,role})`; rejection renders `ApiError.detail` in `role="alert"`, form not cleared.
- [x] 4.6 GREEN: `frontend/src/components/workspace/AddMemberForm.tsx` (`CreateOrgForm` clone).

## Phase 5: Container Page

- [x] 5.1 RED: new `frontend/src/app/(app)/settings/members/__tests__/page.test.tsx` — OWNER sees add form + role/remove controls; non-OWNER sees roster + explanatory line, no mutation controls, self-leave present.
- [x] 5.2 RED (same file): 409 on role-change/remove renders `ApiError.detail` inline on the affected row only; row role and list length unchanged.
- [x] 5.3 RED (same file): successful add/change/remove update the list without a manual refetch.
- [x] 5.4 GREEN: `frontend/src/app/(app)/settings/members/page.tsx` — reads `organizationsAtom`/`activeOrgSlugAtom`/`sessionAtom` via `useAtomValue` (DD4); `canManage = activeOrg?.my_role === "OWNER"` (DD6); wires `useMembers`/`useLeaveOrganization`; single-slot `rowError` (DD5).

## Phase 6: Topbar Wiring

- [x] 6.1 RED: extend `frontend/src/components/workspace/__tests__/AppTopbar.test.tsx` — a "Miembros" link to `/settings/members` renders alongside logout.
- [x] 6.2 GREEN: add `<Link href="/settings/members">Miembros</Link>` to `AppTopbar.tsx`'s right-side `<nav>`, matching existing `text-sm font-semibold underline` styling.

## Phase 7: Verification

- [x] 7.1 Run `cd frontend && npm test` — full suite green.
- [x] 7.2 Run `cd frontend && npm run lint` — clean.
- [x] 7.3 Confirm `git status backend/` is empty for this change.
