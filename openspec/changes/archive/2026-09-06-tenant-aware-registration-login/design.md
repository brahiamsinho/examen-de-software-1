# Design: Tenant-Aware Registration & Login

> Size note: this document exceeds the default 800-word design budget, following the precedent set by
> `archive/2026-09-06-multi-tenant-identity/design.md` and `archive/2026-09-06-frontend-auth-integration/design.md`
> — this project's design artifacts carry a complete file architecture table.

## Technical Approach

Two independent seams, joined by nothing but the existing `GET /api/orgs` round trip:

```
BACKEND   users/services.register_user   @transaction.atomic
              │ 1. validate (unchanged)
              │ 2. User.objects.create_user (unchanged)
              └─3. organizations/services.create_organization(owner, name, slug)  [unchanged callee]
                        ↑ name ← derive_workspace_name()      pure
                        ↑ slug ← generate_unique_slug()       DB-touching, bounded retry

FRONTEND  LoginForm ──login()──► listOrganizations() ──► branch 0 / 1 / 2+
                                                              │
                          setActiveOrg + /dashboard ◄─────────┤ (1)
                          /select-organization ◄──────────────┘ (2+)
                                    │
                          OrgPicker (presentational) ──onSelect──► setActiveOrg ──► /dashboard
```

No model change, no migration, no change to `UserOut`, `Membership`, `resolve_membership`, or the
backend URL-path tenant key. The multitenancy invariant from `state/organizations.ts` survives
verbatim: `activeOrgSlugAtom` stays a UI convenience and **no request derives its org from it** —
the picker writes a UI preference, never an authorization input.

---

## Architecture Decisions

### DD1 — Slug/name derivation: three functions in `organizations/services.py`, pure split from impure

| Option | Tradeoff | Decision |
|---|---|---|
| One `generate_slug()` doing derivation + DB retry | Cannot be property-tested: `hypothesis` + `pytest-django`'s function-scoped `db` fixture raises `HealthCheck.function_scoped_fixture` | Rejected |
| New `organizations/provisioning.py` module | Cleaner boundary, but contradicts the proposal's "Affected Areas" placement and adds a module for ~30 lines | Rejected |
| **Three functions in `services.py`: two pure + one DB-touching** | Matches the proposal's stated placement; the pure pair is DB-free and therefore `hypothesis`-eligible | **Chosen** |

```python
# backend/apps/organizations/services.py  (additive; create_organization untouched)

_NAME_SUFFIX = "'s Workspace"                       # 12 chars
_NAME_MAX = 120                                     # Organization.name max_length
_SLUG_BASE_MAX = 40
_SLUG_ATTEMPTS = 5

def derive_workspace_name(*, source: str) -> str:
    """Pure. D4. Truncates the SOURCE, never the composed string, so the
    result always ends with the suffix and is always <= 120 chars."""
    return f"{source[: _NAME_MAX - len(_NAME_SUFFIX)]}{_NAME_SUFFIX}"

def build_slug_base(*, source: str) -> str:
    """Pure. D5 step 1. `slugify(source)[:40]`, or the literal `workspace`."""
    return slugify(source)[:_SLUG_BASE_MAX] or "workspace"

def generate_unique_slug(*, source: str) -> str:
    """D5 steps 2-4. Always suffixed; never tries the bare base."""
    base = build_slug_base(source=source)
    for _ in range(_SLUG_ATTEMPTS):
        candidate = f"{base}-{secrets.token_hex(3)}"
        if not Organization.objects.filter(slug=candidate).exists():
            return candidate
    candidate = f"workspace-{secrets.token_hex(8)}"
    if not Organization.objects.filter(slug=candidate).exists():
        return candidate
    raise OrganizationError("Could not generate a unique organization slug.")
```

Collision detection is an `.exists()` pre-check inside the generator (not a retry loop around
`create_organization`), because the spec places the "raise `OrganizationError`" obligation on *the
utility*, and because looping over an `IntegrityError` inside the caller's `atomic` block risks a
poisoned transaction. **Residual race** (accepted, ~1 in 16.7M): two concurrent registrations minting
the same 6-hex candidate — the loser's `create_organization` raises `DuplicateSlugError` and the whole
registration rolls back. No corrupt state, no orphan user.

**No import cycle**: `users.services → organizations.services → users.models` is a DAG;
`organizations.services` never imports `users.services`.

### DD2 — `register_user` becomes `@transaction.atomic`; its error contract is unchanged for clients

**Choice**: decorate `register_user` with `@transaction.atomic`, bind the `create_user` result to a
local, then provision. Exact shape of the change (everything above `create_user` is byte-identical):

```python
@transaction.atomic                                  # ← added
def register_user(*, email: str, password: str, full_name: str = "") -> User:
    ...                                              # unchanged validations
    try:
        user = User.objects.create_user(email=email, password=password, full_name=full_name)
    except IntegrityError as exc:
        raise DuplicateEmailError(...) from exc      # unchanged

    source = full_name.strip() or normalized_email.split("@", 1)[0]      # D4
    create_organization(
        owner=user,
        name=derive_workspace_name(source=source),
        slug=generate_unique_slug(source=source),
    )
    return user
```

`DuplicateEmailError` and `PasswordPolicyError` keep identical types, messages, and HTTP mappings
(409 / 400 via `users/api.py::_ERROR_STATUS_MAP`) — **no caller of `register_user` sees a changed
error contract**. Re-raising from inside the `atomic` block is safe because the exception escapes the
block, triggering rollback; nothing is caught-and-continued.

**New failure mode, deliberately unmapped**: a bare `OrganizationError` from slug exhaustion has *no*
registered ninja handler (`organizations/api.py` registers only the four concrete subclasses), so it
surfaces as **500**. That is correct: exhaustion is a server capacity fault, and a 4xx on
`/auth/register` would tell the client to change an email that is not the problem. `users/api.py` and
`schemas.py` stay untouched, as the proposal requires.

### DD3 — Login branches in `LoginForm`'s submit handler; `next` precedence is an early return

**Alternatives**: a dedicated `/post-login` resolver route (extra hop, visible flash, `next` must be
threaded through a URL — rejected); embedding org data in `UserOut` (rejected upstream by D2).

`LoginForm` calls the `lib/organizations.ts` domain function **directly** — not `useOrganizations()`,
whose mount effect would fire an anonymous `listOrganizations()` on the login page and 401. This
matches the existing layering: the form already calls `login()` from `lib/auth.ts`.

```ts
const rawNext = searchParams.get("next");
const user = await login({ email, password });
setSession({ status: "authenticated", user });

if (isSafeNext(rawNext)) {           // ← precedence rule: a valid `next` wins, unconditionally
  router.replace(rawNext);
  return;
}

let orgs: Organization[] = [];
try { orgs = await listOrganizations(); } catch { router.replace("/dashboard"); return; }

if (orgs.length === 1) { setActiveOrg(orgs[0]!.slug); router.replace("/dashboard"); return; }
if (orgs.length >= 2) { router.replace("/select-organization"); return; }
router.replace("/dashboard");        // zero orgs — D6 path, unchanged
```

Two supporting details this forces:

1. **`safe()` cannot express the precedence rule** — it collapses "absent" and "invalid" into
   `/dashboard`, so the branch could never tell a real deep-link from a default. `lib/next-path.ts`
   gains a predicate and `safe()` is re-expressed through it, byte-identical in behavior:
   ```ts
   export function isSafeNext(next: string | null | undefined): next is string {
     return typeof next === "string" && /^\/(?!\/)/.test(next);
   }
   export function safe(next: string | null | undefined): string {
     return isSafeNext(next) ? next : "/dashboard";
   }
   ```
2. **The post-login `listOrganizations()` failure must not reuse the login `catch`.** Login already
   succeeded; showing "no pudimos iniciar sesión" would be a lie. It degrades to `/dashboard`, which
   re-fetches on mount and renders correctly for both the empty and populated case.

`setActiveOrg` comes from a new `useSetActiveOrg()` (see DD5) — the write half of `useOrganizations`
without its fetch effect.

### DD4 — The picker lives at `/select-organization` under a new `(gate)` route group

| Option | Tradeoff | Decision |
|---|---|---|
| `app/(app)/select-organization/` | Reuses `SessionGuard` for free, but `(app)/layout.tsx` renders `AppTopbar` → `OrgSwitcher`, so the screen shows **the same org list twice**, one copy of which sets the active org *without* redirecting — a dead-end trap | Rejected |
| `app/(auth)/select-organization/` | Correct centered-card shell, but `(auth)` has **no guard** — an anonymous deep-link would render a picker instead of bouncing to `/login`. Adding the guard in the page breaks the archived DD3/DD4 rule that the guard lives only in a layout | Rejected |
| **`app/(gate)/select-organization/`** | New 12-line layout = `SessionGuard` + `(auth)`'s centered-card shell, no topbar. Guard stays in a layout; a one-time gate gets exactly one set of affordances | **Chosen** |

The new `(gate)/layout.tsx` types `children` explicitly rather than via the generated `LayoutProps`
helper, for the same reason `(auth)`/`(app)` do: route groups do not appear in the URL, so
`.next/types/routes.d.ts` keys every root-level group layout on `"/"`.

**Navigation is triggered by `LoginForm`, not by a route guard.** A guard would have to re-derive
"did this user just log in?" from nothing, and would re-trigger on ordinary mid-session navigation,
turning a one-time gate into a recurring interruption.

**Component split** (D2: `OrgSwitcher` is *not* overloaded):

- `components/workspace/OrgPicker.tsx` — new, presentational, props `{ organizations, onSelect }`.
  No `activeSlug`/`aria-pressed`: nothing is active yet, so a "current" affordance would be a lie.
  Vertical full-width buttons (name + role) instead of the switcher's horizontal inline row.
- `components/workspace/roleLabels.ts` — new, holds the `ROLE_LABELS` map currently private to
  `OrgSwitcher.tsx`; both components import it. Prevents a duplicated translation table drifting.
- `(gate)/select-organization/page.tsx` — `"use client"` container. Calls `useOrganizations()`
  (legitimate here: authenticated, and it needs the list anyway); `onSelect` = `setActiveOrg(slug)`
  then `router.replace("/dashboard")`. Redirects to `/dashboard` when the loaded list has `< 2`
  organizations, so a bookmarked/back-button visit can never become a permanent dead end.

**`useOrganizations`'s existing auto-select effect is harmless here and needs no change**: it sets
`activeSlugAtom` to `organizations[0]` on load but **does not write localStorage**. The picker's
explicit `setActiveOrg` writes both, which is what makes the *"selection survives a page reload"*
scenario pass.

### DD5 — `useSetActiveOrg()`: the write half, extracted

**Choice**: add to `state/organizations.ts`, and make `useOrganizations` consume it (no duplicated
logic).

```ts
export function useSetActiveOrg() {
  const setActiveSlug = useSetAtom(activeOrgSlugAtom);
  return useCallback((slug: string) => {
    setActiveSlug(slug);
    window.localStorage.setItem(ACTIVE_ORG_STORAGE_KEY, slug);
  }, [setActiveSlug]);
}
```

**Alternatives**: export `ACTIVE_ORG_STORAGE_KEY` and let `LoginForm`/`RegisterForm` write
localStorage themselves (spreads persistence across three files — rejected); call
`useOrganizations()` in the auth forms (fires an anonymous `GET /api/orgs` on `/login` — rejected).

### DD6 — `RegisterForm` adopts the provisioned org via the org list, not via the auth response

D2 forbids org data in `UserOut`, so "the backend response identifies the newly provisioned
organization" (web-session delta) resolves to the `GET /api/orgs` response fetched immediately after
register — where, by D1, there is exactly one entry.

```ts
const user = await register({ email, password, full_name: fullName || undefined });
setSession({ status: "authenticated", user });
try {
  const orgs = await listOrganizations();
  if (orgs.length > 0) setActiveOrg(orgs[0]!.slug);
} catch { /* non-fatal: the dashboard re-fetches on mount */ }
router.replace("/dashboard");
```

The org fetch sits **outside** the existing `catch` that renders `ApiError.detail`, so a failed org
fetch can never surface as a bogus "email already registered" message.

### DD7 — Zero-org path: **zero code changes**, stated as a decision rather than left silent

`OrgEmptyState.tsx`, `CreateOrgForm.tsx`, and `(app)/dashboard/page.tsx` are **verified unchanged**.
`DashboardPage` already branches on `organizations.length === 0` and renders the non-blocking empty
state with no onboarding redirect. The login `0` branch targets `/dashboard`, which is that exact
existing path. The `web-organization-workspace` delta corrects the requirement's *documented
preconditions* only — behavior is identical.

This is load-bearing, not cosmetic: D6 makes *"every user has ≥1 organization"* a **non-invariant**.
Nothing in this design may assume a non-empty org list, and the `0` branch stays live and tested.

### DD8 — `seed_demo`: no behavioral change; docstring corrected, test assertion added

Every demo user now also owns an auto-provisioned personal workspace on top of `acme-demo`:

| User | Orgs after `seed_demo` | Login branch |
|---|---|---|
| `owner@demo.com` | `Ana Owner's Workspace` (OWNER) + `acme-demo` (OWNER) | 2+ → picker |
| `editor@demo.com` | `Bruno Editor's Workspace` (OWNER) + `acme-demo` (EDITOR) | 2+ → picker |
| `viewer@demo.com` | `Carla Viewer's Workspace` (OWNER) + `acme-demo` (VIEWER) | 2+ → picker |

**Decision: keep this outcome; change no logic.** It is the realistic SaaS shape (a personal
workspace plus a shared team org) and it makes the demo dataset exercise the picker — the headline
behavior of this change — with no extra seeding code. **Idempotency is verified intact**: a second
run raises `DuplicateEmailError` from `register_user`, which the command already catches, so no
duplicate personal orgs appear.

**Existing tests pass unchanged** (verified by reading `test_management_seed_demo.py`): every
assertion is scoped by `slug=DEMO_ORG_SLUG` or `Membership.objects.for_organization(...)`; there is
no global `Organization.objects.count()` assertion. Two edits are still required so the new behavior
is *pinned* rather than incidental:

1. `seed_demo.py` — its module docstring and `help` string say "one organization", now false. Text
   only, no logic.
2. `test_management_seed_demo.py` — ADD an assertion that each demo user owns exactly one
   auto-provisioned organization in addition to `acme-demo`.

---

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/organizations/services.py` | Modify | + `derive_workspace_name`, `build_slug_base`, `generate_unique_slug`; imports `secrets`, `django.utils.text.slugify`, `OrganizationError`. `create_organization` untouched |
| `backend/apps/users/services.py` | Modify | `register_user` → `@transaction.atomic` + org provisioning (DD2) |
| `backend/apps/organizations/management/commands/seed_demo.py` | Modify | Docstring/`help` text only (DD8) |
| `backend/apps/organizations/tests/test_services_organizations.py` | Modify | Slug generator: base, always-suffix, retry, fallback, exhaustion, length |
| `backend/apps/organizations/tests/test_slug_properties.py` | **Create** | `hypothesis` property tests for the two pure helpers (no DB) |
| `backend/apps/users/tests/test_services_auth.py` | Modify | Provisioning + rollback at the service layer |
| `backend/apps/users/tests/test_api_auth.py` | Modify | `test_registration_does_not_auto_create_an_organization` → inverted |
| `backend/apps/organizations/tests/test_management_seed_demo.py` | Modify | + personal-workspace assertion (DD8) |
| `frontend/src/lib/next-path.ts` | Modify | + `isSafeNext`; `safe` re-expressed, behavior identical |
| `frontend/src/state/organizations.ts` | Modify | + `useSetActiveOrg`; `useOrganizations` consumes it (DD5) |
| `frontend/src/components/auth/LoginForm.tsx` | Modify | 0/1/2+ branching + `next` precedence (DD3) |
| `frontend/src/components/auth/RegisterForm.tsx` | Modify | Adopt provisioned org before redirect (DD6) |
| `frontend/src/components/workspace/roleLabels.ts` | **Create** | Shared `ROLE_LABELS` |
| `frontend/src/components/workspace/OrgSwitcher.tsx` | Modify | Import `ROLE_LABELS` instead of declaring it — no behavior change |
| `frontend/src/components/workspace/OrgPicker.tsx` | **Create** | Presentational one-time picker list |
| `frontend/src/app/(gate)/layout.tsx` | **Create** | `SessionGuard` + centered card, no topbar (DD4) |
| `frontend/src/app/(gate)/select-organization/page.tsx` | **Create** | Container: `useOrganizations` + `OrgPicker` + redirect |
| `frontend/src/lib/__tests__/next-path.test.ts` | Modify | `isSafeNext` cases |
| `frontend/src/state/__tests__/organizations.test.ts` | Modify | `useSetActiveOrg` |
| `frontend/src/components/auth/__tests__/{LoginForm,RegisterForm}.test.tsx` | Modify | Branching + adoption |
| `frontend/src/components/workspace/__tests__/OrgPicker.test.tsx` | **Create** | List renders name + role; `onSelect` fires |
| `frontend/src/app/(gate)/select-organization/__tests__/page.test.tsx` | **Create** | Selection persists + redirects; `<2` orgs redirects |
| `backend/apps/{users,organizations}/{models,api,schemas,constants}.py`, migrations | **Untouched** | No schema change, no migration, no auth-response change |
| `frontend/src/components/workspace/{OrgEmptyState,CreateOrgForm}.tsx`, `app/(app)/dashboard/page.tsx`, `AppTopbar.tsx` | **Untouched** | DD7 |
| `docs/ai/CURRENT_STATE.md`, `docs/ai/DECISIONS_LOG.md` | Modify | Dual-documentation convention; D1–D8 |

---

## Testing Strategy

Strict TDD, RED→GREEN→REFACTOR, in this order (pure before impure, backend before frontend):

| Layer | What to Test | Approach |
|---|---|---|
| Unit (pure, backend) | `build_slug_base`, `derive_workspace_name` | `hypothesis` property tests, **no DB** — this is why DD1 splits them out |
| Unit (DB, backend) | `generate_unique_slug` retry/fallback/exhaustion | `pytest.mark.django_db`; force collisions by pre-creating orgs and patching `secrets.token_hex` to a fixed sequence |
| Service (backend) | `register_user` provisions 1 org + OWNER membership; rollback | `django_db`; rollback via `monkeypatch` on `generate_unique_slug` → `OrganizationError`, then assert `User.objects.count() == 0` |
| API (backend) | Inverted `test_registration_does_not_auto_create_an_organization` | Existing ninja test client |
| Command (backend) | `seed_demo` idempotency + personal workspaces | `call_command` twice |
| Component (frontend) | `OrgPicker` renders every org with its role label; `onSelect` | RTL |
| Integration (frontend) | Login 0/1/2+ branches, `next` precedence, org-fetch failure fallback; register adoption; picker persistence + `<2` redirect | RTL + mocked `lib/auth` & `lib/organizations`, per-test Jotai `Provider` |

Property sketch (`test_slug_properties.py`):

```python
@given(st.text(max_size=200))
def test_base_is_always_a_bounded_nonempty_url_safe_slug(source):
    base = build_slug_base(source=source)
    assert 1 <= len(base) <= 40
    assert re.fullmatch(r"[a-z0-9_-]+", base)
    assert len(f"{base}-{'0' * 6}") <= 47              # < SlugField(max_length=60)

@given(st.text(max_size=300))
def test_name_always_fits_and_keeps_its_suffix(source):
    name = derive_workspace_name(source=source)
    assert name.endswith("'s Workspace") and len(name) <= 120
```

Runners: `cd backend && pytest`, `cd frontend && npm test`.

---

## Threat Matrix

No shell command, subprocess, VCS/PR automation, executable-file classification, or process
integration is introduced — those rows are **N/A**. One boundary row is applicable:

| Boundary | Applicable? | Expected safe behavior | RED test |
|---|---|---|---|
| Open redirect via the `next` query param | **Applicable** — `isSafeNext` becomes the sole gate on a post-auth `router.replace` | `//evil.com`, `https://evil.com`, `javascript:...`, and `null` all fail the predicate; only a single-leading-slash relative path is honored | `next-path.test.ts` asserts `isSafeNext` rejects each vector; `LoginForm.test.tsx` asserts a hostile `next` falls through to org-count branching, never to the hostile target |
| Tenant key derived from client state | **Applicable** — the picker writes `activeOrgSlugAtom` | The atom stays a UI preference; every API call keeps taking `{org_slug}` from its URL path, guarded by `resolve_membership` | Existing `tenant-isolation` backend tests remain green and unmodified; no frontend change routes a request off the atom |

---

## Migration / Rollout

**No migration required.** No model field, constraint, or index changes; the diff must contain no new
file under any `migrations/` directory (a stated success criterion). Rollout is a plain deploy; the
partial rollback described in the proposal (revert frontend only) remains coherent because the
backend change is additive and the frontend change is a pure branch.

---

## Deviations

Per this project's convention, deviations from the proposal are numbered and explicit, never silent.

| # | Deviation | Justification |
|---|---|---|
| **DV1** | `frontend/src/state/organizations.ts` is marked **Untouched** in the proposal, but gains `useSetActiveOrg()` | The alternatives are worse: exporting `ACTIVE_ORG_STORAGE_KEY` scatters persistence across three files, and calling `useOrganizations()` in `LoginForm` fires an anonymous `GET /api/orgs` on the login page. Additive only; `useOrganizations`'s public shape is unchanged |
| **DV2** | `frontend/src/lib/next-path.ts` is not in the proposal's Affected Areas, but gains `isSafeNext` | D2's precedence rule is unimplementable with `safe()` alone, which collapses "absent" and "invalid" into the same `/dashboard` result. `safe()`'s observable behavior is byte-identical after the refactor |
| **DV3** | `OrgSwitcher.tsx` is marked **Untouched**, but its private `ROLE_LABELS` moves to `roleLabels.ts` | The picker must render the same role labels; duplicating the map guarantees drift. Zero behavior change — a deleted `const` and an added `import` |
| **DV4** | The proposal implies the picker is only a `components/workspace/` addition; this design adds a route group `app/(gate)/` with a layout | Both existing groups are unsuitable (see DD4): `(app)` double-renders the org list and creates a dead-end trap, `(auth)` has no session guard. One 12-line layout is cheaper than either workaround |
| **DV5** | The `web-session` delta says "the backend response identifies the newly provisioned organization"; this design reads that as the `GET /api/orgs` response, not the register response | D2 explicitly rejects org data in `UserOut`. Interpretation only — no spec text change is proposed and the observable scenario is satisfied unchanged |

---

## Open Questions

None blocking. Two accepted, documented residuals: the ~1-in-16.7M concurrent-slug race that fails a
registration closed rather than corrupt (DD1), and slug exhaustion surfacing as HTTP 500 by design
(DD2).
