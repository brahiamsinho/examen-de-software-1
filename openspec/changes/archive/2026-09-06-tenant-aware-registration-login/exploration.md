# Exploration: Tenant-Aware Registration & Login

Scope: registration-time organization creation and login-time tenant
resolution/redirect. Does not implement anything — output is options with
tradeoffs for `sdd-propose`.

## Current State

Registration (`backend/apps/users/services.py::register_user`, called from
`backend/apps/users/api.py::register`) creates only a `User` row and logs the
session in. No `Organization`/`Membership` is created. This is not an
oversight — it is an explicit, tested, archived spec decision:
`openspec/specs/user-authentication/spec.md` § "No Auto-Created Organization"
states "Registration MUST NOT create an organization on the user's behalf"
and is enforced by
`backend/apps/users/tests/test_api_auth.py::test_registration_does_not_auto_create_an_organization`.
Any auto-create-org-at-registration design must explicitly supersede this
requirement, not silently contradict it.

Org creation (`backend/apps/organizations/services.py::create_organization`)
is the only path that produces an `Organization` + `OWNER` `Membership`,
atomically. Today it is reachable only from `POST /orgs` via the dashboard's
`CreateOrgForm`, which is rendered unconditionally regardless of how many orgs
the user already owns — this, not registration itself, is the actual
"unlimited orgs" gap. `Organization.slug` is `unique=True` and today is
client-derived and client-editable (`CreateOrgForm.tsx`'s own `slugify()`),
then just uniqueness-checked server-side (`DuplicateSlugError` on collision).
There is no backend slug-generation utility anywhere in the repo.

Login (`backend/apps/users/api.py::login_view` / `services.authenticate_user`)
only authenticates and starts a session; it returns `UserOut` with zero
organization awareness. `LoginForm.tsx` redirects immediately to `next`
(sanitized) or `/dashboard`, before any org data is fetched.

Multi-org support already exists post-login: `list_user_organizations()` /
`GET /orgs` return the caller's memberships; `frontend/src/state/organizations.ts`
(`organizationsAtom`, `activeOrgSlugAtom`) persists an "active org" choice in
`localStorage`; `OrgSwitcher.tsx` renders orgs with role labels for switching.
Critically, `organizations.ts`'s own comment states this atom is "a UI
convenience only — no request may derive its org from this atom" — matching
`openspec/specs/tenant-isolation/spec.md` § "Tenant Key in the URL Path",
which mandates the tenant key live as an explicit path segment
(`/orgs/{org_slug}/...`) and forbids treating session/localStorage state as
authoritative for authorization.

Structural gap found: that URL-path tenancy rule is only implemented on the
backend Ninja routers (`organizations_router`, `memberships_router` mounted
with `{org_slug}` in the path, guarded by `resolve_membership`). The frontend
has no tenant-scoped route at all — `frontend/src/app/(app)/dashboard/page.tsx`
is a single flat `/dashboard` route; "active org" is pure client state, not a
URL segment. So "login should detect the org and redirect them there"
currently has no slug-addressed destination page to redirect into.

## Affected Areas

- `backend/apps/users/services.py` (`register_user`) — candidate for calling
  `create_organization` transactionally.
- `backend/apps/users/api.py` (`register`, `login_view`) — response payload
  would need to carry org context (or not, if the frontend just re-fetches).
- `backend/apps/organizations/services.py` (`create_organization`,
  `list_user_organizations`) — reused, not replaced; slug-collision-retry
  logic for auto-generated slugs is genuinely new.
- `backend/apps/organizations/models.py` (`Organization.slug`, globally
  unique, non-sequential by design) — auto-slug strategy must respect the
  existing "no tenant-count leakage" intent.
- `frontend/src/components/auth/LoginForm.tsx`, `RegisterForm.tsx` — redirect
  logic must become org-aware.
- `frontend/src/state/organizations.ts`, `OrgSwitcher.tsx` — likely reusable
  data/shape for a login-time picker; must stay clearly separated in role
  from "switching mid-session" vs. "choosing at login."
- `frontend/src/components/workspace/OrgEmptyState.tsx`, `CreateOrgForm.tsx`,
  `frontend/src/app/(app)/dashboard/page.tsx` — remain relevant, not dead
  code (see zero-org analysis below).
- `openspec/specs/user-authentication/spec.md` — "No Auto-Created
  Organization" requirement directly contradicted; needs a MODIFIED/REMOVED
  delta with Reason/Migration.
- `openspec/specs/web-organization-workspace/spec.md` — "Zero-Organization
  Empty State" requirement needs reframing as an edge case, not the default
  fresh-signup path.
- `openspec/specs/web-session/spec.md` — "Login and Logout" / redirect
  requirement needs an ADDED/MODIFIED delta for org-count-based redirect
  branching.
- `openspec/specs/tenant-isolation/spec.md` — "Tenant Key in the URL Path"
  requirement is currently backend-only; extending it to a frontend route is
  a design decision this exploration surfaces but does not resolve.
- Tests:
  `backend/apps/users/tests/test_api_auth.py::test_registration_does_not_auto_create_an_organization`
  (breaks by design), `backend/apps/organizations/tests/test_services_organizations.py`
  (needs new slug-retry coverage), `frontend/.../LoginForm.test.tsx` (needs
  0/1/2+-org branch cases), `OrgEmptyState.test.tsx` / `CreateOrgForm.test.tsx`
  (should remain green, re-verify at `sdd-tasks`).

## Approaches

### Axis 1 — Registration-time org creation

1. **Auto-create exactly one org per registration** (call `create_organization`
   inside/adjacent to `register_user`'s transaction, deriving name from
   `full_name` or email local-part, auto-slugged with collision-retry) —
   supersede the "No Auto-Created Organization" requirement.
   - Pros: Directly matches the product ask; reuses the already-invariant-correct
     `create_organization` (creator becomes `OWNER` atomically); `add_member`
     (invite path) is unaffected since an invited user already got their own
     org at their own registration — "every registered user has ≥1 org from
     signup" holds without contradicting invites.
   - Cons: Needs new slug-derivation + collision-retry logic that doesn't
     exist today; must explicitly amend an archived spec and its passing
     test; auto-generated org names/slugs are cosmetically arbitrary.
   - Effort: Medium. **Recommended.**
2. **Keep registration org-free, make first-login org-creation blocking**
   (turn `OrgEmptyState`'s reachable-dashboard into a mandatory onboarding
   redirect).
   - Pros: No slug-generation-without-input problem — user supplies a real
     org name interactively.
   - Cons: Directly contradicts the archived, deliberate "Zero-Organization
     Empty State ... MUST NOT redirect to a blocking onboarding flow"
     requirement; does not actually cap "unlimited orgs" any better than
     today; adds a second onboarding screen. Higher spec blast radius than
     Option 1.
   - Effort: Medium-High.
3. **No registration change; only cap `CreateOrgForm` to one-org-per-user
   going forward.**
   - Pros: Smallest diff.
   - Cons: Does not satisfy the user's explicit ask; still leaves a manual
     post-login step between signup and having a workspace.
   - Effort: Low, but misses the requirement.

### Axis 2 — Login-time tenant resolution & redirect

1. **Branch on org count** using the existing `GET /orgs` primitive: 0 orgs →
   unchanged `/dashboard` + `OrgEmptyState` (edge case, not the default
   anymore); exactly 1 org → set active org (localStorage/atom) and redirect
   straight in; 2+ orgs → show a dedicated picker screen reusing
   `OrgSwitcher`'s org+role list shape, then redirect on selection.
   `OrgSwitcher` itself stays as-is for mid-session switching; the picker is
   a one-time post-login gate, functionally distinct.
   - Pros: Reuses existing, tested data flow; minimal new backend surface;
     clean separation of "initial choice" vs. "ongoing switch."
   - Cons: Still redirects into the same flat `/dashboard` route (org is
     encoded only in client state, not the URL) unless paired with Axis 3.
   - Effort: Low-Medium. **Recommended.**
2. **Embed org list directly in the login/register response** to avoid a
   second round trip before deciding where to redirect.
   - Pros: Fewer requests, redirect decision available immediately.
   - Cons: Couples an unrelated concern into the auth response schema; the
     existing `useOrganizations()` hook already does this fetch cheaply —
     marginal gain, extra churn on `UserOut`/`LoginIn` schemas and their
     tests.
   - Effort: Low, but likely not worth it.

### Axis 3 (surfaced, not resolved)

Does the frontend need real slug-scoped routes (`/orgs/[slug]/...`) to have
something authentic to "redirect into," given the tenant-isolation spec's
URL-path mandate currently applies only to the backend? This is a genuine
open design question for `sdd-propose`/`sdd-design`, not something to decide
here.

## Recommendation

Axis 1 → Option 1 (auto-create one org at registration, explicit spec
supersession) combined with Axis 2 → Option 1 (org-count branch reusing
existing list/switch primitives). Concretely:

- `register_user` gains an org-creation side effect (same transaction), with
  a bounded slug-collision-retry loop using a non-sequential suffix (short
  random token, not incrementing numbers, to stay consistent with
  `organization-tenancy`'s "no tenant-count leakage via slug" intent).
- `CreateOrgForm` stays untouched and available for deliberately creating
  additional orgs — auto-creation at signup and voluntary multi-org growth
  are not in tension; the user's own multi-org/picker ask confirms multi-org
  remains a first-class, intentional feature, not something to cap.
- Post-login redirect branches on org count (0/1/2+) using the existing
  `GET /orgs` data path; the 2+ case gets a new, distinct picker screen
  (reusing `OrgSwitcher`'s presentational shape) rather than overloading
  `OrgSwitcher` itself.
- `OrgEmptyState`/zero-org handling is explicitly kept, reframed as the edge
  case for: legacy pre-migration accounts registered under the old flow, and
  any user whose sole org was later deleted by its owner (org deletion
  cascades memberships; the last-owner invariant blocks demoting/removing the
  last `OWNER` but not deleting the org itself).
- Whether the redirect target becomes a real `/orgs/[slug]/...` frontend
  route or stays `/dashboard` + client-state active-org should be an
  explicit open question carried into `sdd-propose`, since it changes blast
  radius substantially (new route tree vs. reuse of existing state).

## Open Questions / Risks

- **Direct spec contradiction**: "No Auto-Created Organization" is an
  archived, deliberate decision with a passing test — this change must
  supersede it via a proper MODIFIED/REMOVED delta with Reason/Migration, not
  an implicit rewrite.
- **Migration/backfill gap**: existing users registered under the current
  org-free flow will have 0 orgs; login-time logic must define their path
  explicitly (fall through to the unchanged zero-org dashboard state) rather
  than assume "every user has ≥1 org" as a post-deploy universal truth.
- **Slug collision at scale**: auto-derived slugs from names/emails have a
  meaningfully higher collision rate than deliberate human-chosen slugs; the
  retry strategy needs a bounded attempt count and must not leak
  sequential/incremental patterns.
- **Frontend/backend tenancy-in-URL asymmetry**: the tenant-isolation spec's
  URL-path rule is enforced only on the backend API today; deciding whether
  the frontend also needs slug-scoped routes is unresolved and changes the
  size of this change substantially — must be decided explicitly in
  `sdd-propose`, not assumed.
- Test breakage is intentional but must be tracked:
  `test_registration_does_not_auto_create_an_organization` will fail by
  design and needs rewriting alongside the spec delta, not just deletion.

## Ready for Proposal

Yes — proceed to `sdd-propose`. Registration-time auto-org-creation directly
reverses an existing, deliberate, tested spec decision (must be an explicit
supersession, not silent); the "unlimited orgs" complaint and "auto-create at
registration" are two related but separable concerns (multi-org itself stays
fully supported, including via the login picker the user asked for); and the
frontend currently has no slug-addressed route to redirect into, so the
proposal must explicitly decide whether to introduce one or keep tenancy
client-state-only for now.
