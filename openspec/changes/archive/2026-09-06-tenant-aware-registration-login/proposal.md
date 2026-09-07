# Proposal: Tenant-Aware Registration & Login

## Intent

Today a person can register and end up with **no workspace at all**, then create an
unbounded number of organizations from a `CreateOrgForm` that renders unconditionally on
`/dashboard`. Login is completely tenant-blind: `login_view` returns `UserOut` with zero
organization awareness and `LoginForm.tsx` redirects to `next` or `/dashboard` before any
org data is fetched. The result is a product where "which tenant am I in?" is answered by
accident — by whatever `localStorage` happened to hold — rather than by the sign-up and
sign-in flows themselves.

This change makes tenancy a property of the identity lifecycle: **registration provisions
exactly one organization**, and **login resolves the caller's organizations and routes
accordingly** — straight in when there is one, through an explicit choice when there are
several. Multi-org stays a first-class feature; what changes is that it becomes a
deliberate choice rather than a side effect of an empty dashboard.

## Scope

### In Scope

- `register_user` provisions one `Organization` + `OWNER` `Membership` in the same
  transaction as the `User`, reusing `create_organization` unchanged.
- A backend slug-generation utility with a bounded, non-sequential collision-retry scheme
  (D4/D5) — this does not exist anywhere in the repo today.
- Post-login redirect branching on the caller's organization count: `0` → unchanged
  `/dashboard` empty state, `1` → set active org and go, `2+` → a new one-time picker
  screen (D2).
- Registration success sets the newly provisioned org as the active org before redirect.
- Spec deltas superseding the archived requirements enumerated in D7.
- Rewriting `test_registration_does_not_auto_create_an_organization` into its inverse, and
- re-verifying `seed_demo` and its test against the new registration side effect (D8).

### Out of Scope — Non-Goals (explicit, so `sdd-spec`/`sdd-design` do not scope-creep)

- **No slug-scoped frontend routes** (`/orgs/[slug]/...`) and no subdomain routing infra (D3).
- **No changes to `Membership`, the `Role` set, or the last-owner invariant.**
- **No changes to the invite / `add_member` path** or to token invitations (D8).
- **No cap on organization count.** `CreateOrgForm` stays as-is and unconditional.
- **No slug mutability.** `rename_organization` still renames the `name` only.
- **No data migration and no login-time backfill** for existing zero-org users (D6).
- **No changes to `tenant-isolation`**, `resolve_membership`, or the backend URL-path
  tenant-key rule.
- **No org data embedded in the login/register response schema** (Axis 2 Option 2 rejected:
  it couples tenancy into `UserOut` for a round trip `useOrganizations()` already makes).
- No `Plan` changes, no org deletion changes, no password reset / email verification.

## Capabilities

> Contract with `sdd-spec`. No new capability is introduced — this change re-shapes four
> existing ones. Exact requirement-level deltas are enumerated in **D7**.

### New Capabilities

None.

### Modified Capabilities

- `user-authentication`: registration's atomic unit grows to `User + Organization +
  Membership`; the "No Auto-Created Organization" requirement is removed and replaced.
- `organization-tenancy`: slugs may now be server-generated; the generator inherits the
  existing non-sequential / no-tenant-count-leakage constraint.
- `web-session`: post-login destination branches on organization count.
- `web-organization-workspace`: adds the post-login picker; reframes the zero-org empty
  state as an edge case rather than the default fresh-signup landing.

## Resolved Decisions

**D1 — Auto-create exactly one organization per registration** (exploration Axis 1,
Option 1, adopted). `register_user` becomes `@transaction.atomic` and calls the existing
`create_organization`, which already creates the `OWNER` `Membership` atomically and is
already invariant-correct. If org provisioning fails, the `User` row rolls back with it —
registration is all-or-nothing, never "a user with no workspace".

**D2 — Login branches on organization count** (Axis 2, Option 1, adopted), using the
existing `GET /orgs` / `useOrganizations()` data path. `0` → `/dashboard` + `OrgEmptyState`
unchanged; `1` → `setActiveOrg(slug)` then redirect; `2+` → a new post-login picker screen
reusing `OrgSwitcher`'s org+role presentational shape. `OrgSwitcher` itself is **not**
overloaded — mid-session switching and the one-time login gate stay functionally distinct.
**Precedence rule** `sdd-spec` must pin down: an explicit, valid `next` parameter wins over
org-count branching, otherwise a `/login?next=/dashboard` guard bounce would be hijacked by
the picker.

**D3 — No slug-scoped frontend routes. The redirect stays `/dashboard` + client-state
active org.** (Axis 3, resolved.) Rationale: the `tenant-isolation` URL-path mandate governs
*authorization inputs on the API* — every backend request already carries `{org_slug}` and
is guarded by `resolve_membership`. Mirroring the slug into frontend URLs would relocate a
UI hint, not add a single tenant-safety property. Blast-radius consequence, stated
explicitly: a `/orgs/[slug]/...` route tree would move `dashboard/page.tsx`, the `(app)`
layout, the route guard, `OrgSwitcher` navigation, `LoginForm`'s `next` sanitization, and
every frontend test asserting `/dashboard` — on its own that exceeds the 800-line review
budget while delivering zero isolation benefit. **This decision keeps the change medium
rather than large.** The invariant from `frontend/src/state/organizations.ts` therefore
survives untouched: `activeOrgSlugAtom` remains a UI convenience and **no request may
derive its org from it**. Frontend URL tenancy is recorded as tech debt (#1), not dropped.

**D4 — Auto-org naming.** Display source = `full_name.strip()` when non-empty, else the
email local-part. Name = `"{source}'s Workspace"`, truncated to the model's 120-char limit.
This is the conventional SaaS shape (Slack/Notion/Linear) and reads as clearly provisional,
which is the point. **The user can rename it immediately** — `rename_organization` and
`PATCH /orgs/{slug}` already exist and are OWNER-authorized, and the registrant is always
the OWNER. **The slug is not renameable** (`rename_organization` updates `name` only), and
this change does not make it so: the slug is the tenant key in the URL path, so mutating it
is a tenant-identity change with its own blast radius (bookmarks, in-flight sessions, the
persisted `activeOrgSlug`) that the product ask does not require. Tech debt #2.

**D5 — Slug generation and collision retry (exact scheme).**

1. `base = slugify(source)[:40]`; if it slugifies to empty (e.g. a non-Latin name), use
   the literal `workspace`.
2. **Always suffix** — attempt *n* (1..5) yields `f"{base}-{secrets.token_hex(3)}"`, a
   fresh 6-char lowercase hex token each attempt (~16.7M space). Max length 40+1+6 = 47,
   inside `SlugField(max_length=60)`.
3. Final fallback (attempt 6): `f"workspace-{secrets.token_hex(8)}"`.
4. Exhaustion raises an `OrganizationError`; the registration transaction rolls back rather
   than silently producing a user with no organization.

Why *always* suffix instead of trying the bare base first: a bare-base first attempt lets
the first registrant named "Acme" silently squat the global slug `acme`, which then makes
the *deliberate* `CreateOrgForm` path fail for a reason its user can neither see nor fix.
Always-suffixing keeps the clean namespace available for intentional org creation, makes
the collision path uniform with no special case, and costs nothing in the UI — the user
reads the **name**, not the slug. Random hex is non-sequential, so it leaks no tenant count,
satisfying `organization-tenancy` § "Organization Entity".

**D6 — No backfill. Pre-change zero-org users permanently fall through to `OrgEmptyState`.**
Rationale: (a) minting an organization as a side effect of *login* re-creates exactly the
"organizations appear without me asking" surprise this change exists to remove, and turns a
read-shaped action into a write that retries on every legacy login; (b) a data migration
would have to invent names and slugs for accounts whose owners never requested a workspace,
and is as irreversible as registration itself; (c) the affected population is dev/demo
accounts only; (d) the `Zero-Organization Empty State` path must stay live regardless — a
user whose sole org was deleted by its owner lands there too — so keeping legacy users on
it costs no extra code. **Consequence `sdd-design` MUST honor: "every user has ≥1
organization" is NOT a post-deploy invariant. No code may assume a non-empty org list.**

**D7 — Spec supersession map** (precise enough that `sdd-spec` need not re-investigate).

| Spec | Operation | Requirement | Reason / Migration for the delta |
|---|---|---|---|
| `user-authentication` | **REMOVED** | `No Auto-Created Organization` | Reason: directly inverted by D1 — its premise ("a freshly registered user legitimately belongs to zero organizations") is now false for new registrations. Migration: existing zero-org users are unaffected (D6); `test_registration_does_not_auto_create_an_organization` is **rewritten into its inverse, not deleted**. Renamed rather than MODIFIED because the header itself would become a lie. |
| `user-authentication` | **ADDED** | `Registration Provisions One Organization` | Replaces the removed requirement: exactly one org, creator is `OWNER`, name/slug per D4/D5. |
| `user-authentication` | **MODIFIED** | `Registration` | Reason: the atomic unit grows from `User` to `User + Organization + OWNER Membership`. Migration: the three existing scenarios remain valid verbatim; ADD scenarios for org provisioning and for transactional rollback when provisioning fails. |
| `organization-tenancy` | **ADDED** | `Server-Generated Organization Slug` | Reason: slugs were client-supplied only; D5 introduces a generator that must inherit the non-sequential / no-count-leakage constraint. ADDED rather than MODIFIED because no existing `Organization Entity` scenario changes — avoid churn. |
| `web-session` | **MODIFIED** | `Login and Logout` | Reason: post-login destination is no longer unconditionally `next`/`/dashboard`. Migration: existing scenarios stay; ADD 0/1/2+ scenarios **and** an explicit scenario pinning the D2 precedence rule (valid `next` beats org-count branching). |
| `web-session` | **MODIFIED** | `Registration` | Reason: the redirect target is still `/dashboard` under D3, but the provisioned org MUST become the active org before redirect. Migration: amend the success scenario only; no route change. |
| `web-organization-workspace` | **MODIFIED** | `Zero-Organization Empty State` | Reason: documentation truth — it reads as the normal fresh-signup landing, which is now false. Migration: **behavior is unchanged and the MUST-NOT-redirect-to-blocking-onboarding rule is explicitly preserved** (it is what makes D6 viable); scenario gains its two real preconditions: legacy pre-change account, or sole org deleted. Zero code change. |
| `web-organization-workspace` | **ADDED** | `Post-Login Organization Picker` | The 2+ branch: list orgs with roles, explicit selection writes the active org, then redirect. |
| `web-organization-workspace` | *no delta* | `Organization List and Active Selection` | Deliberately unchanged: the picker writes the choice via `setActiveOrg` before redirect, so the existing "fall back to the first listed organization" rule only fires when the persisted value is missing or stale, exactly as specified today. Recorded here so `sdd-spec` does not over-scope. |
| `tenant-isolation` | *no delta* | all | D3: the URL-path tenant-key rule keeps applying to the backend API only, unchanged. |

**D8 — The invite / `add_member` path is explicitly untouched, and here is why.**
`organization-membership` § "Add Member by Email Lookup" already requires the invitee to be
an *already-registered* user. Under D1 that person therefore already owns a workspace from
their own registration, so being added to a second org simply moves them from D2's `1` branch
to its `2+` branch — a case the login picker handles by construction. No new membership
semantics, no new invariant, no change to `organizations/services.py::add_member`. The
last-owner invariant is likewise unaffected: an auto-created org has exactly one `OWNER`
(its registrant) and is never auto-deleted.

## Approach

Backend, `backend/apps/users/services.py`: wrap `register_user` in `@transaction.atomic`,
and after `User.objects.create_user` call the existing `create_organization(owner=user,
name=..., slug=...)` with values from a **new** slug/name derivation helper implementing
D4/D5. `create_organization`, `Organization`, `Membership`, and every model stay byte-for-byte
unchanged — **no migration is introduced by this change**, which is what makes the rollback
below cheap.

Frontend: `RegisterForm.tsx` sets the returned org active before redirect;
`LoginForm.tsx` awaits the existing org list and branches 0/1/2+ per D2, with the new picker
rendered as a dedicated post-login screen (exact route path is an `sdd-design` decision;
working name `/select-organization`) that reuses `OrgSwitcher`'s presentational shape.
`OrgSwitcher`, `OrgEmptyState`, `CreateOrgForm`, and `dashboard/page.tsx` keep their current
behavior.

Strict TDD is enabled project-wide: `sdd-apply` follows RED-GREEN-REFACTOR one use case at
a time, starting with the slug generator (pure, DB-free, property-testable with the already
installed `hypothesis`) before the transactional registration path.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/apps/users/services.py` | Modified | `register_user` becomes atomic and provisions the org |
| `backend/apps/organizations/services.py` | Modified (additive) | New slug/name derivation + bounded retry helper; `create_organization` itself unchanged |
| `backend/apps/organizations/models.py`, `constants.py`, migrations | **Untouched** | No schema change, no migration |
| `backend/apps/organizations/management/commands/seed_demo.py` | **Verify / likely Modified** | It calls `register_user`, so every seeded user now also gets a personal org — `test_management_seed_demo.py` assertions must be re-checked. *(Not identified in exploration.)* |
| `backend/apps/users/tests/test_api_auth.py` | Modified | `test_registration_does_not_auto_create_an_organization` rewritten to its inverse |
| `backend/apps/organizations/tests/test_services_organizations.py` | Modified | New slug-generation / collision-retry coverage |
| `frontend/src/components/auth/LoginForm.tsx`, `RegisterForm.tsx` | Modified | Org-aware redirect |
| `frontend/src/components/workspace/` (new picker) | New | Post-login org picker screen + test |
| `frontend/src/state/organizations.ts`, `OrgSwitcher.tsx`, `OrgEmptyState.tsx`, `CreateOrgForm.tsx`, `dashboard/page.tsx` | **Untouched** | Reused as-is (D2, D3) |
| `backend/apps/users/api.py`, `schemas.py` | **Untouched** | Axis 2 Option 2 rejected — no org data in the auth response |
| `openspec/specs/{user-authentication,organization-tenancy,web-session,web-organization-workspace}/spec.md` | Modified | Deltas per D7 |
| `docs/ai/CURRENT_STATE.md`, `DECISIONS_LOG.md` | Modified | Dual-documentation convention; D1–D8 to `DECISIONS_LOG.md` |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `seed_demo` breaks or its test's org-count assertions drift | **High** | Named as an affected area above; `sdd-tasks` MUST include a work unit re-verifying `test_management_seed_demo.py`, not just the auth tests |
| Code written assuming "every user has ≥1 org" after D6 | Medium | D6 states the non-invariant explicitly; the `0` branch of D2 and the preserved `Zero-Organization Empty State` requirement keep the path live and tested |
| Picker hijacks a legitimate `next` deep-link (guard bounce) | Medium | D2's precedence rule is a required, explicitly scenario-tested spec clause, not an implementation detail |
| Auto-slug collision exhausts the retry budget | **Low** | D5's 6-char hex gives ~16.7M per base across 5 attempts plus a 16-char final fallback; exhaustion rolls the transaction back rather than corrupting state |
| Reviewers read the removed "No Auto-Created Organization" as an accidental regression | Medium | D7 makes it an explicit REMOVED+ADDED pair with Reason/Migration, and the deliberately-failing test is rewritten rather than deleted |
| Deferring frontend slug routes (D3) leaves front/back tenancy asymmetric | Medium | Accepted knowingly and logged as tech debt #1; no isolation property is weakened because the atom was already non-authoritative |
| Users dislike auto-generated names/slugs | Low | Name is renameable immediately (D4); slug immutability logged as tech debt #2 |

## Rollback Plan

Cheap, because **no migration and no model change is introduced**.

1. `git revert` the change commits. `register_user` returns to creating only a `User`;
   `LoginForm`/`RegisterForm` return to their unconditional redirect.
2. Organizations already auto-created remain as ordinary, valid rows — indistinguishable
   from manually created ones and fully manageable (rename, delete) by their `OWNER`. **No
   data loss and no orphaned state.** Deleting them, if desired, is a normal owner action,
   not a rollback step.
3. Partial rollback is available: reverting only the frontend branch restores the old
   redirect while registration keeps provisioning orgs — a safe, coherent intermediate state.
4. Spec deltas revert with the same commits; `openspec/specs/` returns to its archived text.

## Dependencies

- **No new package dependency.** `slugify` ships with Django (`django.utils.text.slugify`)
  and `secrets` is stdlib; `hypothesis` is already in `backend/requirements/test.txt`.
- Builds on archived `multi-tenant-identity` (Cycle 2) and `frontend-auth-integration`;
  modifies their specs per D7 but modifies neither of their models.
- A reachable PostgreSQL instance for the DB-backed registration tests (already required).

## Explicit Tech Debt

1. Frontend tenancy is not in the URL (D3). A future change may introduce
   `/orgs/[slug]/...` routes; until then the frontend/backend asymmetry is deliberate.
2. Organization slugs are immutable (D4). Slug rename needs its own change with a
   redirect/staleness story.
3. Pre-change zero-org accounts are never backfilled (D6); "every user has ≥1 org" is not
   an invariant and nothing may assume it.
4. Auto-generated names are cosmetic and English-shaped (`"X's Workspace"`); no
   localization of the generated name.

## Success Criteria

- [ ] A new registration produces exactly one `Organization` with the registrant as `OWNER`,
      in the same transaction as the `User`.
- [ ] A forced failure during org provisioning rolls back the `User` — no orphan account.
- [ ] The generated slug is non-sequential, unique, ≤60 chars, and survives a forced
      collision via the D5 retry scheme (property-tested).
- [ ] A user with exactly one org logs in and lands in their workspace with that org active,
      with no picker shown.
- [ ] A user with two orgs sees the picker, and their explicit choice is the active org
      after redirect and after a page reload.
- [ ] A user with zero orgs still reaches `/dashboard` and sees `OrgEmptyState` — no
      redirect to a blocking onboarding route.
- [ ] A valid `next` deep-link is honored over org-count branching.
- [ ] `test_registration_does_not_auto_create_an_organization` exists in inverted form and
      passes; `add_member` and last-owner tests are unchanged and green.
- [ ] `seed_demo` and `test_management_seed_demo.py` are green against the new behavior.
- [ ] `cd backend && pytest` and `cd frontend && npm test` are both green.
- [ ] No new migration file exists in the diff.
- [ ] `docs/ai/CURRENT_STATE.md` and `DECISIONS_LOG.md` record D1–D8.
