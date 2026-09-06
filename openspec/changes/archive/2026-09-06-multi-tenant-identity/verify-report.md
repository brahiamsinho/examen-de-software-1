```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:3d26ba6-backfill-verify-gaps-and-fix-cosmetic-drift
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 20/20
scenarios: 37/37
test_command: docker compose exec -T backend pytest -q
test_exit_code: 0
test_output_hash: sha256:f6bbd9ffa433b9e2e8c0a455d1a63de04d3bfaf9a4691c78a2388dfb49b1c190
build_command: docker compose exec -T backend python manage.py check
build_exit_code: 0
build_output_hash: sha256:1e3e63f221bde88816c4a4ef7367691607b20cc1d194028a02ec9ae0586cf9b1
```

## Verification Report

**Change**: multi-tenant-identity
**Version**: Cycle 2 (post-refactor users/organizations split, plus 2026-09-06 verify-gap backfill commit 3d26ba6)
**Mode**: Strict TDD

This is a re-verify following commit 3d26ba6 ("test(multi-tenant-identity): backfill verify gaps and fix cosmetic drift"), made in direct response to the previous verify report (Engram sdd/multi-tenant-identity/verify-report, id 420, 2026-09-06). Every prior finding was independently re-checked against the actual repo state and re-run test suite, not assumed from the commit message.

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 41 |
| Tasks complete | 41 |
| Tasks incomplete | 0 |

tasks.md re-read in full: all 41 tasks across Phases 0-6 remain [x]. No task was un-checked or added by the backfill commit (it is scoped to tests, constraints, and docs, not new task-tracked work).

### Build & Tests Execution
**Build** (Django system check, closest available proxy - no lint/type-check tool in requirements/*): PASSED
```text
docker compose exec -T backend python manage.py check
System check identified no issues (0 silenced).
```

**Tests**: 170 passed / 0 failed / 0 skipped
```text
docker compose exec -T backend pytest -q
........................................................................ [ 42%]
........................................................................ [ 84%]
..........................                                               [100%]
170 passed in 14.77s
```
Independently re-run this session (not trusted from the prior report). 170 = prior 168 baseline plus 2 new backfill regression tests (test_registration_does_not_auto_create_an_organization in apps/users/tests/test_api_auth.py, test_resolves_strictly_from_the_path_slug_regardless_of_other_membership in apps/organizations/tests/test_permissions.py). Both new tests exercise real production code paths (POST /api/auth/register + GET /api/orgs; permissions.resolve_membership) with non-trivial assertions - no tautologies, no assertions-without-production-call.

**Coverage**: Not available - no coverage tool detected in requirements/*.

### Re-Check of Every Previously-Flagged Finding

| # | Prior finding | Severity | Independently re-verified this session | Status |
|---|---|---|---|---|
| 1 | user-authentication / "No Auto-Created Organization" - scenario "fresh registration to empty org membership list" had no covering test | CRITICAL | Read the new test in apps/users/tests/test_api_auth.py (git diff of 3d26ba6): registers via POST /api/auth/register, then asserts GET /api/orgs returns []. Confirmed GET /api/orgs (list_organizations in apps/organizations/api.py:45-48) is real production code (queries request.user.memberships), not a stub. Test passed in the independent full-suite re-run. | RESOLVED |
| 2 | tenant-isolation / "Tenant Key in URL Path" - scenario "authorization uses path org even if session differs" had no covering test | CRITICAL | Read the new test in apps/organizations/tests/test_permissions.py: a user with memberships in two orgs calls permissions.resolve_membership (real production function) with each org slug in both orders, asserting the returned membership always matches the path slug, never the other. This is the closest possible regression test given no session-based "current org" concept exists in the code (confirmed by re-reading permissions.py, services.py, api.py - no request.session reads). Test passed in the independent full-suite re-run. | RESOLVED |
| 3a | Leftover identity_-prefixed DB constraint names (identity_user_email_ci_unique, identity_membership_user_org_uniq) not renamed during the identity to users/organizations split | WARNING | git show 3d26ba6 confirms both models.py files and both migration files (users/migrations/0001_initial.py, organizations/migrations/0002_initial.py) renamed to users_user_email_ci_unique / organizations_membership_user_org_uniq. Ran docker compose exec backend python manage.py sqlmigrate users 0001 against the live container - the applied schema constraint name is confirmed users_user_email_ci_unique. Repo-wide rg "identity_" in backend/ returns only two unrelated matches (identity_fields local variable in test_models_membership.py; test_format_of_parse_is_the_identity_... - mathematical "identity function" naming in uml_modeling), neither a constraint reference. rg "apps/identity" and rg "apps.identity" return zero matches anywhere in backend/. | RESOLVED |
| 3b | organizations app has two initial migrations (0001_initial.py + 0002_initial.py) instead of design.md's stated one-per-app, undocumented | WARNING | git show 3d26ba6 for design.md confirms step 4 of the Implementation Order was rewritten to state the split explicitly and explain why: Organization.members is an M2M through="organizations.Membership" (confirmed in models.py:30-32) while Membership.organization is itself an FK back to Organization (confirmed models.py:66-71, via the TenantScopedModel abstract base) - a circular in-app dependency Django's migration autodetector cannot express in one file, standard Django behavior, not a bug. The explanation is technically accurate, not merely asserted. | RESOLVED |
| 4 | backend/requirements/base.txt's comment on the email-validator line still referenced the deleted identity/schemas.py path | WARNING | git show 3d26ba6 for backend/requirements/base.txt confirms the comment now reads "used by apps/users/schemas.py and apps/organizations/schemas.py request schemas" - both paths verified to exist and both actually define Pydantic/Ninja schemas using EmailStr. | RESOLVED |
| 5 | Organization.plan "gates nothing" scenario proven only by static absence-of-reader review, no dedicated regression test | WARNING | Not addressed by this commit (not in the requested fix scope) - rg -i "plan.*gates" and rg -i "gates.*plan" across apps/organizations/tests/ return nothing. Re-confirmed the underlying claim still holds: no code path reads Organization.plan for authorization decisions. | STILL OPEN (unchanged, non-blocking) |
| 6 | The two undocumented drifts above (3a/3b) should be added to DECISIONS_LOG.md's 2026-09-06 entry for completeness | WARNING (documentation only) | Re-read docs/ai/DECISIONS_LOG.md's 2026-09-06 entry: still does not mention the constraint rename or the migration-count fix explicitly (it only describes the app split itself). This is a documentation completeness nit, not a functional gap - the underlying facts (3a, 3b) are now correctly reflected in the code and in design.md itself. | STILL OPEN (cosmetic, non-blocking) |

### Spec Compliance Matrix (deltas from prior report only - all other 33 scenarios unchanged and still COMPLIANT, re-confirmed against the 170-test run)
| Requirement | Scenario | Test | Result |
|---|---|---|---|
| No Auto-Created Organization | fresh registration to empty org membership list | test_api_auth.py > test_registration_does_not_auto_create_an_organization | COMPLIANT (was UNTESTED) |
| Tenant Key in URL Path | authorization uses path org even if session differs | test_permissions.py > test_resolves_strictly_from_the_path_slug_regardless_of_other_membership | COMPLIANT (was UNTESTED) |
| Organization Entity | plan gates nothing | Static only (grep-confirmed absence of any reader) - no dedicated test | PARTIAL (unchanged) |

**Compliance summary**: 36/37 scenarios fully COMPLIANT with a passing runtime test (up from 35/37), 1/37 still PARTIAL (static-evidence-only, unchanged, non-blocking per D7's "plan gates nothing by design" - there is no code path to write a meaningful negative test against today). 0/37 UNTESTED (down from 2/37).

### Correctness (Static Evidence) - re-confirmed, no change from prior report
| Requirement | Status | Notes |
|---|---|---|
| AUTH_USER_MODEL = "users.User" | Implemented | config/settings.py:57 |
| TenantScopedModel DD1 shape | Implemented | organizations/models.py - raising manager, .unscoped() escape hatch, base_manager_name="all_objects" |
| Cross-origin CSRF/session block (DD2) | Implemented | config/settings.py env-driven |
| _assert_not_last_owner single-helper invariant (DD3) | Implemented | organizations/services.py, select_for_update() present |
| resolve_membership 404-not-403 (DD4) | Implemented | organizations/permissions.py |
| UUID PKs for User/Organization (DD5) | Implemented | Both models.py |
| Error taxonomy to status mapping (DD6) | Implemented | _ERROR_STATUS_MAP in both api.py files |
| Case-insensitive email uniqueness (DD7) | Implemented | UserManager.normalize_email + Lower("email") constraint, now named users_user_email_ci_unique |
| One-directional organizations to users import | Implemented | No reverse import found |

### Coherence (Design)
| Decision | Followed? | Notes |
|---|---|---|
| DD1-DD7 | Yes | Unchanged from prior report |
| NinjaAPI(csrf=True) exact API surface | Deviated (documented) | Unchanged - django-ninja 1.7 has no csrf kwarg; equivalent enforcement documented in tasks.md, DECISIONS_LOG.md, and config/api.py |
| org_slug: str auto-binds from mount prefix | Deviated (documented) | Unchanged - fixed with explicit Path[str] |
| No new dependency (email-validator) | Deviated (documented) | Unchanged - documented in tasks.md and DECISIONS_LOG.md |
| One 0001_initial.py per app | Now documented | design.md's Implementation Order step 4 now explains the two-migration split for organizations accurately (circular M2M-through/FK dependency) - was previously an undocumented drift |
| Constraint names match design.md | Now matches | users_user_email_ci_unique, organizations_membership_user_org_uniq - confirmed in code, migrations, and live applied schema |
| backend/requirements/base.txt comment | Now accurate | References apps/users/schemas.py and apps/organizations/schemas.py |

### Issues Found

**CRITICAL**: None (both prior CRITICAL findings resolved with passing runtime tests, independently re-verified).

**WARNING**:
1. Organization.plan "gates nothing" scenario is still proven only by static absence-of-reader review, not a dedicated regression test. Unchanged from the prior report and not in this commit's fix scope. Low risk - no plan-gated code exists anywhere today - but there is no regression guard if that changes carelessly later.
2. docs/ai/DECISIONS_LOG.md's 2026-09-06 entry still does not explicitly call out the constraint rename or the two-migration organizations split as follow-up fixes - a documentation-completeness nit only; the underlying facts are correctly reflected in the code and in design.md itself.

**SUGGESTION**: None.

### Verdict
**PASS WITH WARNINGS**

All 41 tasks remain complete, all 20 spec requirements are implemented, and both previously CRITICAL untested scenarios now have real, independently-verified, passing runtime tests (36/37 scenarios fully compliant, 1/37 unchanged non-blocking PARTIAL). The identity_-prefixed constraint names are fully renamed in code, migrations, and the live applied database schema. design.md's migration-count note is now technically accurate. The requirements/base.txt comment is now accurate. 170/170 tests pass against live Postgres; manage.py check is clean. The two remaining WARNING items (plan-gates regression test, DECISIONS_LOG completeness) are cosmetic/low-risk and do not block archive.

---

### TDD Compliance
| Check | Result | Details |
|---|---|---|
| TDD Evidence reported | Yes | Prior apply-progress artifact (id 415) plus tasks.md's deviation notes cover the original 41 tasks; the 2 new backfill tests are direct spec-scenario regression tests added post-hoc in response to a verify finding (standard verify to apply-gap-fix cycle, not a new TDD unit) |
| All tasks have tests | Yes | 89 non-infra test functions (87 + 2 backfill) across 15 test files map to the 41 tasks' RED/GREEN pairs |
| RED confirmed (tests exist) | Yes | All 15 test files verified to exist on disk; the 2 new tests confirmed present via git show 3d26ba6 diff |
| GREEN confirmed (tests pass) | Yes | 170/170 pass on independent re-run this session |
| Triangulation adequate | Yes | Unchanged - every multi-scenario requirement still has 2+ distinct test cases |
| Safety Net for modified files | Yes | Full-suite green run covers all 8 files touched by 3d26ba6; no regression to uml_modeling's 80 tests |

**TDD Compliance**: 6/6 checks passed

---

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|---|---|---|---|
| Unit (model/service) | 38 | 8 | pytest-django, @pytest.mark.django_db |
| Unit (permissions, no HTTP) | 7 | 1 | pytest-django, RequestFactory-style direct calls (+1 backfill test) |
| Integration/API (Django test Client) | 40 | 4 | Django Client, pytest-django (+1 backfill test) |
| Infra (app registration, isolation contract) | 4 | 3 | pytest-django |
| E2E | 0 | 0 | Not installed (backend-only cycle, matches proposal's explicit frontend deferral) |
| **Total** | **89** | **15** | |

---

### Changed File Coverage
Coverage analysis skipped - no coverage tool (coverage.py/pytest-cov) detected in backend/requirements/*.

---

### Assertion Quality
Read both new test functions in full (see diff excerpts in the re-check table above). Both call real production code (POST /api/auth/register + GET /api/orgs; permissions.resolve_membership) and assert non-trivial, specific values (== [], .organization_id == org_a.id, .role == Role.VIEWER / Role.OWNER) - no tautologies, no assertions-without-production-call, no ghost loops, no smoke-test-only patterns.

**Assertion quality**: All assertions verify real behavior

---

### Quality Metrics
**Linter**: Not available (no ruff/flake8 in requirements/*)
**Type Checker**: Not available (no mypy in requirements/*)

---

### Archive Readiness
**Clean - recommended for sdd-archive.** Zero CRITICAL findings, zero blockers, 170/170 tests passing, all 41 tasks complete, all 6 items from the prior verify report's finding list independently re-checked (4 fully resolved, 2 unchanged low-risk WARNINGs that were already non-blocking in the prior report and remain so). No new issues introduced by the backfill commit.
