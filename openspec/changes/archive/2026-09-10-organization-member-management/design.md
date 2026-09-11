# Design: Organization Member Management UI

## Technical Approach

Frontend-only, four existing layers reused unchanged: `apiFetch` transport →
`lib/organizations.ts` domain client → a page-scoped `useMembers` hook →
presentational `components/workspace/*`. The only genuinely new wiring is
self-removal repointing in `state/organizations.ts`. Backend untouched.

## Architecture Decisions

### DD1: Member clients are thin `apiFetch` wrappers, errors propagate

**Choice**: Four functions with no `try/catch`; `ApiError` reaches the caller,
exactly as `createOrganization` does today. `DELETE` returns 204 → `apiFetch`
yields `undefined`.
**Rejected**: normalizing 409/404 into result objects.
**Rationale**: the 409 `detail` must survive verbatim to a specific row; a
result-object seam would force every caller to re-derive it.

### DD2: `useMembers` uses local `useState`, not a Jotai atom

**Choice**: `useMembers(orgSlug: string | null)` owns `members/loading/error`
in component state; idle while `orgSlug` is null; refetches when it changes.
**Rejected**: a `membersAtom` mirroring `organizationsAtom`.
**Rationale**: `organizationsAtom` is shared because three components need it.
The roster has exactly one consumer (the container, per the proposal's
duplicate-fetch mitigation) and must reset per tenant — a module atom would
leak one org's roster into the next.
**Deviation**: adds `loading`/`error`, which `useOrganizations()` lacks. A
full page needs distinct empty vs. failed states; a switcher does not.

### DD3: Mutations never pre-update local state

**Choice**: each mutator awaits the response, then writes the returned row
into state (append / replace / drop). No optimistic pre-update, no rollback.
**Rejected**: optimistic updates with rollback (the `createOrganization`
append pattern).
**Rationale**: `POST /api/orgs` cannot fail an invariant after responding;
`PATCH`/`DELETE` on members can (409 last-owner). Not pre-updating makes
"list unchanged on failure" structural rather than a rollback we must test.

### DD4: Containers below the layout read atoms; only the layout fetches

**Choice**: the page reads `organizationsAtom`, `activeOrgSlugAtom`, and
`sessionAtom` via `useAtomValue`. It does not call `useOrganizations()` or
`useSession()`.
**Rejected**: calling `useOrganizations()` in the page.
**Rationale**: those hooks fetch on mount. `AppTopbar`/`SessionGuard` already
own one instance each; a third mount adds a third `listOrganizations()` GET.

### DD5: Single-slot row error, not a map or a toast

**Choice**: container holds `rowError: { userId, message } | null`; each
attempt clears it first; the row renders it when `userId` matches.
**Rejected**: `Record<userId, string>`; global toast (forbidden by proposal).
**Rationale**: one mutation per click, so concurrent per-row errors are
unreachable. The role `<select>` is controlled by `member.role` (never local
state), so a rejected PATCH leaves the displayed role unchanged for free.

### DD6: Viewer role comes from `Organization.my_role`

**Choice**: `canManage = activeOrg?.my_role === "OWNER"`, from the already
loaded `organizationsAtom`.
**Rejected**: deriving it from the viewer's own row in the members list; a new
endpoint.
**Rationale**: `my_role` is the established source (`OrgSwitcher` uses it) and
needs no request. Hiding is presentation only — backend `require_role` stays
the enforcement point; per multitenancy rules a hidden control is never
treated as authorization.

### DD7: OWNER transfer stays unreachable

**Choice**: add-form roles are `EDITOR`/`VIEWER`; the row `<select>` offers
only `EDITOR`/`VIEWER`, rendering a disabled current-value option when the row
is an OWNER (so the sole-owner demote attempt in the spec stays reachable
without ever offering `OWNER` as a target).
**Rationale**: confirmed out of scope; `RoleChangeIn` would accept `OWNER`, so
the constraint must be enforced by what the UI emits.

## Data Flow — self-removal (the new path)

    MemberRow ──onRemove(self)──→ page ──→ leaveOrganization(slug, userId)
                                              │
                        1. await removeMember(...)   ← throws ⇒ stop, nothing local changes
                        2. remaining = orgs.filter(≠ slug)
                        3. setOrganizations(remaining)          ┐ same
                           setActiveSlug(remaining[0]?.slug ?? null) │ sync
                           persistActiveOrgSlug(next)               ┘ batch
                        4. router.replace("/dashboard")

**Ordering is load-bearing.** `AppTopbar` lives in the `(app)` layout and
survives the navigation; redirecting first would land on `/dashboard` with the
dead org still in `organizationsAtom` and a stale `activeSlug` until reload.
Jotai writes are synchronous, so steps 3 land before navigation begins.

**Zero remaining orgs**: `useOrganizations()`'s selection effect returns early
on `organizations.length === 0`, so it cannot clear a stale slug. Step 3 must
therefore set `null` and *remove* the storage key explicitly.

**If persistence throws** (`setItem` quota/private mode): the DELETE already
succeeded, so there is nothing to roll back. `persistActiveOrgSlug` swallows
storage failure; the atom repoint and redirect still happen, and the existing
`stillMember` check self-heals the stale key on next load.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/lib/organizations.ts` | Modify | `Member` type + four clients |
| `frontend/src/state/members.ts` | Create | `useMembers(orgSlug)` |
| `frontend/src/state/organizations.ts` | Modify | `persistActiveOrgSlug` helper (also used by `useSetActiveOrg`) + `useLeaveOrganization()` |
| `frontend/src/app/(app)/settings/members/page.tsx` | Create | Container; `rowError`; role/self/permission derivation |
| `frontend/src/components/workspace/MembersList.tsx` | Create | `<ul aria-label="Miembros">`, props-in/callback-out |
| `frontend/src/components/workspace/MemberRow.tsx` | Create | Role control, remove/leave, inline row error |
| `frontend/src/components/workspace/AddMemberForm.tsx` | Create | `CreateOrgForm` clone: local state, `ApiError.detail` in `role="alert"` |
| `frontend/src/components/workspace/AppTopbar.tsx` | Modify | Right-side `<nav>`: `<Link href="/settings/members">Miembros</Link>` + existing logout, same `text-sm font-semibold underline` |

## Interfaces / Contracts

```ts
// lib/organizations.ts — shapes taken from backend MembershipOut/MemberAddIn
export type Member = {
  user_id: string; email: string; full_name: string;
  role: Role; created_at: string;
};
export function listMembers(orgSlug: string): Promise<Member[]>;
export function addMember(orgSlug: string,
  input: { email: string; role: "EDITOR" | "VIEWER" }): Promise<Member>;
export function changeMemberRole(orgSlug: string, userId: string,
  role: Exclude<Role, "OWNER">): Promise<Member>;
export function removeMember(orgSlug: string, userId: string): Promise<void>;
// paths: /api/orgs/${encodeURIComponent(orgSlug)}/members[/${userId}]

// state/members.ts
{ members: Member[]; loading: boolean; error: string | null;
  addMember; changeMemberRole; removeMember }  // mutators rethrow ApiError

// state/organizations.ts
export function useLeaveOrganization():
  (orgSlug: string, userId: string) => Promise<void>;
```

Presentational props follow `OrgSwitcher`/`CreateOrgForm` exactly: data in,
callbacks out, no fetch, no atom access.

## Testing Strategy (Strict TDD — RED first)

| Layer | What to Test | Approach |
|-------|--------------|----------|
| **New — highest risk** | `useLeaveOrganization`: repoint to first remaining; zero-org ⇒ `activeSlug null` + key removed; DELETE rejects ⇒ atoms/storage untouched, no redirect; `setItem` throws ⇒ repoint and redirect still occur; atoms final *before* `router.replace` | Extend `state/__tests__/organizations.test.ts`: `renderHook` + `<Provider>`, mock `@/lib/organizations` and `next/navigation` |
| **New** | `useMembers`: idle on null slug; refetch on slug change; add/change/remove update from the response with no refetch; rejection leaves `members` identical and rethrows | New `state/__tests__/members.test.ts`, same `renderHook`+`Provider` shape |
| **New** | 409 renders `ApiError.detail` inside the affected row only; row role unchanged; list length unchanged | New `app/(app)/settings/members/__tests__/page.test.tsx`, RTL |
| Established | Four clients: path/method/json + return | Mirror `lib/__tests__/organizations.test.ts` (mock `apiFetch`) |
| Established | `MembersList`/`MemberRow`/`AddMemberForm` props-and-callbacks; hidden (not disabled) controls for non-OWNER; self-leave always present | Mirror `OrgSwitcher.test.tsx` / `CreateOrgForm.test.tsx` |
| Established | Topbar link present/absent | Extend `AppTopbar.test.tsx` |

## Threat Matrix

N/A — no routing-authority, shell, subprocess, VCS/PR automation,
executable-file classification, or process-integration boundary. Tenant
authorization is unchanged and remains server-side.

## Migration / Rollout

No migration. Additive files plus three reverts; `modelia:active-org-slug`
keeps its existing contract (the new helper is a refactor of its only writer).

## Open Questions

- [ ] None blocking.
