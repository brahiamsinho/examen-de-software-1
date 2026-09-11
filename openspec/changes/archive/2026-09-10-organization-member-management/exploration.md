# Exploration: Organization Member Management UI

Scope: whether/how to build a frontend UI for inviting, changing the role
of, and removing organization members. Does not implement anything — output
is options with tradeoffs for `sdd-propose`.

## Current State

**Scope correction from the initial framing**: the backend is not a partial
or unwired implementation. It is fully complete, fully HTTP-exposed, fully
tested, and already covered by an archived canonical spec, shipped in the
`multi-tenant-identity` cycle.

Confirmed directly (not just via sub-agent report — spot-checked by reading
`services.py` and `api.py`):

- `backend/apps/organizations/services.py` defines `add_member`,
  `change_member_role`, `remove_member`, and `list_memberships`, all
  invariant-bearing via `_assert_not_last_owner`.
- `backend/apps/organizations/api.py` mounts `memberships_router` at
  `/api/orgs/{org_slug}/members` with `GET ""`, `POST ""`,
  `PATCH "/{user_id}"`, `DELETE "/{user_id}"` — real, tested HTTP endpoints.
- `permissions.py`: `resolve_membership()` (404 for unknown slug or
  non-member, indistinguishable by design) + `require_role(membership,
  Role.OWNER)`. Every endpoint requires OWNER except `remove_member`, which
  explicitly allows self-removal for any role.
- `constants.Role` = `OWNER | EDITOR | VIEWER`. `MemberAddIn.role` is
  restricted to `Literal["EDITOR", "VIEWER"]` — a member cannot be added
  directly as OWNER.
- Test coverage: `test_api_memberships.py`, `test_services_memberships.py`,
  `test_permissions.py`, `test_models_membership.py`.
- Canonical spec already exists and matches the implementation exactly:
  `openspec/specs/organization-membership/spec.md` (archived from
  `2026-09-06-multi-tenant-identity`).

**Invitation flow — closed prior decision, not an open question for this
cycle**: there is no invite/email/pending-token flow. `add_member` does an
`email__iexact` lookup against existing `User` rows and raises
`UserNotFoundError` on a miss. The spec text is explicit: "MUST NOT invite
unregistered addresses ... rather than starting an invitation flow."

**Frontend — confirmed genuinely missing** (spot-checked via `Glob
**/member*` under `frontend/src` → no matches):

- `frontend/src/lib/organizations.ts` only has `listOrganizations()` /
  `createOrganization()`; no member-related client functions.
- No member-related file exists anywhere under `frontend/src`.
- `app/(app)/` has only `dashboard/page.tsx` — no members/settings route.

Existing frontend patterns to follow for consistency:

- `state/organizations.ts` — Jotai atoms + `useOrganizations()` hook owning
  fetch/optimistic-update side effects.
- `components/workspace/OrgSwitcher.tsx` / `CreateOrgForm.tsx` — pure
  presentational, props-in/callback-out, no fetch inside.
- `AppTopbar.tsx` — container wiring a hook to a presentational component.
- `roleLabels.ts` (`ROLE_LABELS` map), `ApiError.detail` for form error
  surfacing.

## Affected Areas

- `frontend/src/lib/organizations.ts` — add `listMembers`, `addMember`,
  `changeMemberRole`, `removeMember` client functions.
- `frontend/src/state/organizations.ts` (or a new `state/members.ts`) —
  members-list atom/hook scoped to the active organization.
- New presentational components under `frontend/src/components/workspace/`
  — members list, invite-by-email form, role control, remove-member action.
- A new route (e.g. `app/(app)/settings/members/page.tsx`) — no existing
  entry point today; needs a decision on where this lives in the app shell
  and how it's reached from navigation.
- No backend changes anticipated.

## Approaches

1. **Frontend-only change, reuse existing endpoints.** Build the UI and
   `lib/organizations.ts` extensions against the already-shipped
   `/api/orgs/{slug}/members` endpoints.
   - Pros: no backend risk, matches existing container/presentational
     conventions, backend already tested and specified.
   - Cons: none significant — the invite-by-email-only restriction (no
     email invitations for unregistered users) must be communicated to the
     user as a fixed constraint, not treated as an open design choice.
   - Effort: Low–Medium. **Recommended.**
2. **Re-scope as a full-stack change (backend + frontend).**
   - Pros: none.
   - Cons: would duplicate already-shipped, already-tested work and risks
     drifting from the existing invariants (last-owner protection,
     self-removal semantics) and the archived spec.
   - Effort: rejected — not recommended.

## Recommendation

Option 1. Scope `organization-member-management` as **frontend-only**. No
backend proposal/design/tasks needed. Reference
`openspec/specs/organization-membership/spec.md` as the already-authoritative
behavior spec. `sdd-propose` should define: the members list view, the
invite-by-email form (role limited to EDITOR/VIEWER), the change-role
control (OWNER-only, disabled/hidden for non-owners), the remove-member
action (OWNER-only for others, always allowed for self), and where in the
app shell this screen lives.

## Open Questions / Risks

- Last-owner removal/demotion is already rejected server-side
  (`LastOwnerError`, 409) — the frontend must surface this clearly to the
  user, not swallow it as a generic error.
- Self-removal from the currently active organization: `useOrganizations()`
  only refetches on mount today; there is no existing invalidation pattern
  for "I just removed my own membership" (unlike `createOrganization`'s
  optimistic-append, there is no removal analog yet). This needs new state
  wiring.
- The frontend must hide/disable add/role-change affordances for non-OWNER
  viewers — a UX concern only, since authorization is already fully
  enforced server-side via `require_role`.
- The invite form must not offer "OWNER" as an assignable role (schema-
  enforced server-side via `Literal["EDITOR","VIEWER"]`, but the UI should
  match it to avoid a confusing 422).
- No live session invalidation exists today if a member is removed while
  actively viewing that organization — out of scope unless explicitly
  requested.

## Ready for Proposal

Yes — proceed to `sdd-propose`, scoped as frontend-only work against an
already-complete, already-specified backend.
