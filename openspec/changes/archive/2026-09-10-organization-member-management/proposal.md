# Proposal: Organization Member Management UI

## Intent

An organization OWNER has no way to see or manage who belongs to their
organization. The backend capability shipped complete in `multi-tenant-identity`
(`/api/orgs/{slug}/members`, spec `organization-membership`), but it is
unreachable from the product: today the only path to add a collaborator is a
manual DB/shell operation. This change exposes that capability in the web app.

## Scope

### In Scope

- Members screen at `/settings/members` (`app/(app)/settings/members/page.tsx`),
  scoped to the active organization, reached from a link in `AppTopbar`.
- Members list: email, role label (`ROLE_LABELS`), self marker.
- Add member by email; role selector limited to `EDITOR` / `VIEWER`.
- Change a member's role; remove a member (OWNER only).
- Leave organization (any role, self only), with active-org state repointing.
- `lib/organizations.ts`: `listMembers`, `addMember`, `changeMemberRole`,
  `removeMember`.

### Out of Scope

- Any backend change. Behavior is already specified and tested.
- Email invitations for unregistered addresses (closed prior decision:
  `add_member` resolves an existing `User` or returns `UserNotFoundError`).
- Assigning or transferring `OWNER` from the UI.
- A `/settings` index or broader settings shell.
- Per-org deep-linkable URLs (`/orgs/{slug}/members`) and live invalidation for
  a member removed by someone else while viewing.

## Capabilities

### New Capabilities

- `web-member-management`: viewing, adding, role-changing, and removing
  organization members from the web app, including OWNER-only affordances and
  last-owner error surfacing.

### Modified Capabilities

- `web-organization-workspace`: active-organization selection must repoint when
  the user leaves their active organization (a removal analog to the existing
  optimistic-append on creation).

## Approach

Frontend-only, following existing conventions: a container page owns a members
hook (fetch/mutate/state, `useOrganizations()`-shaped); presentational
components stay props-in/callback-out like `OrgSwitcher` / `CreateOrgForm`.

Settled product decisions:

1. **Placement** — single flat route `/settings/members` under `(app)`; the
   tenant stays implicit in UI state and explicit on the wire (`{slug}` URL
   segment), matching the documented rule that no request derives its org from
   client state.
2. **`LastOwnerError` (409)** — surfaced verbatim from `ApiError.detail` inline
   next to the affected member row; never collapsed into a generic error, and
   no local state mutation is applied.
3. **Self-removal** — on success, drop the org from `organizationsAtom`,
   repoint `activeOrgSlugAtom` and its `localStorage` key to the first
   remaining org (or none), then redirect to `/dashboard`, whose existing
   empty state absorbs the zero-org case.
4. **Non-OWNER view** — mutation controls are hidden, not disabled, with one
   explanatory line; the self-leave action stays visible for every role.

UI copy follows the app's existing Spanish convention.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/lib/organizations.ts` | Modified | Four member client functions + `Member` type |
| `frontend/src/state/members.ts` | New | Members hook: list, add, change role, remove |
| `frontend/src/state/organizations.ts` | Modified | Leave-org state repointing |
| `frontend/src/components/workspace/` | New | `MembersList`, `AddMemberForm`, row role/remove controls |
| `frontend/src/app/(app)/settings/members/page.tsx` | New | Container page |
| `frontend/src/components/workspace/AppTopbar.tsx` | Modified | Members link |
| `backend/` | None | No change |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 409 last-owner error swallowed as generic failure | Med | Explicit inline `detail` surfacing; scenario in spec |
| Stale active org after self-removal leaves a dead tenant selected | Med | Repoint atom + `localStorage` in the same handler; redirect |
| Hidden controls read as a bug by non-OWNER users | Low | One explanatory line on the screen |
| 422 from offering `OWNER` in the add form | Low | Selector limited to `EDITOR`/`VIEWER` |
| Duplicate `listMembers` fetch across sibling components | Low | Single container owns the hook |

## Rollback Plan

Revert the change branch. All new files are additive; the three modified files
(`lib/organizations.ts`, `state/organizations.ts`, `AppTopbar.tsx`) revert to
their current form with no data migration and no backend or schema impact. No
persisted state changes shape — the `modelia:active-org-slug` key keeps its
existing contract.

## Dependencies

- Shipped backend endpoints at `/api/orgs/{org_slug}/members` and the archived
  `organization-membership` spec (no work required).

## Success Criteria

- [ ] An OWNER can list, add (EDITOR/VIEWER), re-role, and remove members
      without leaving the web app.
- [ ] Attempting to remove or demote the last OWNER shows the backend's
      specific 409 message next to that member, and the list is unchanged.
- [ ] A user who leaves their active organization lands on a coherent
      dashboard with a valid (or empty) active organization, no manual reload.
- [ ] A non-OWNER member sees the roster and an explanation, with no
      non-functional management controls.
- [ ] No backend file is modified by this change.
