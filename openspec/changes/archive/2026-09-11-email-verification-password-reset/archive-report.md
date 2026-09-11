# Archive Report: email-verification-password-reset

**Change**: email-verification-password-reset
**Archived**: 2026-09-11
**Status**: Complete — Ready for deployment

## Artifact Traceability

All artifacts successfully archived and merged into main specs:

| Artifact | Type | Engram ID | Status |
|----------|------|-----------|--------|
| Proposal | architecture | #496 | Retrieved, 5 open product questions recorded |
| Specification | architecture | #498 | Retrieved, 5 domains (4 NEW, 1 MODIFIED), 17 requirements merged |
| Design | architecture | #497 | Retrieved, 6 ADRs (DD1-DD6) verified in code |
| Tasks | architecture | #499 | Retrieved, 24/24 tasks completed and checked |
| Verify Report | architecture | #501 | Retrieved, PASS verdict with 0 CRITICAL, 0 open WARNING |

## Verification Status (per verify-report #501)

**Final Verdict**: PASS — 0 CRITICAL, 0 open WARNING, 2 non-blocking suggestions

### Completeness Confirmed
- **Tasks**: All 24/24 implementation tasks marked [x] in tasks.md; each corresponds to real, inspected code with passing tests (Phases 1–7)
- **Specs**: 5 spec files, 17 requirements, 41 scenarios; every scenario mapped to implementing code with passing covering tests
- **Design**: 6 ADRs (DD1–DD6) documented in design.md; all decisions followed in actual code
- **Test Evidence** (independent execution at verify time):
  - Backend: 233/233 tests pass
  - Frontend: 168/168 tests pass

### Spec Compliance by Domain

| Domain | Requirements | Scenarios | Status |
|--------|--------------|-----------|--------|
| email-verification | 4 | 10 | PASS |
| password-reset | 3 | 11 | PASS |
| transactional-email | 4 | 5 | PASS |
| web-account-recovery | 4 | 9 | PASS |
| user-authentication (delta) | 3 (1 new, 1 modified, 1 existing) | 6 | PASS |

### Key Decisions Verified

- **DD1**: SHA-256 hash of `secrets.token_urlsafe(32)` raw token; raw never persisted/logged — confirmed in tokens.py
- **DD2**: Single `EmailToken` table with `purpose` column discriminator — confirmed in models.py
- **DD3**: Throttle via `created_at` queries, no new dependencies (no cache/middleware/django-ratelimit) — confirmed in services.py
- **DD4**: Anti-enumeration logic lives entirely in the service layer; API returns fixed response — confirmed in request_password_reset and api.py
- **DD5**: `FRONTEND_BASE_URL` env var, no Mailpit literal in settings.py — confirmed in settings.py/env.example
- **DD6**: Banner dismissal is session-only jotai atom, NOT localStorage — confirmed in state/session.ts

### Issues Found and Resolution Status

**CRITICAL**: None

**WARNING** (1, now resolved):
- Original finding: task 6.1 said all 3 auth pages should be Suspense-wrapped, but `forgot-password/page.tsx` is not
- Resolution: Orchestrator corrected task 6.1 wording (same session, before archive) to explicitly state Suspense-wrapping only applies where `useSearchParams()` is called. Code was already correct; only task wording was imprecise. This aligns with existing `register/page.tsx` precedent.
- Status: RESOLVED — No code changed, only task wording fixed

**SUGGESTIONS** (2, both non-blocking, no action needed):
1. Anti-enumeration fixed delay (0.3s) is an accepted residual-risk design decision; a slow SMTP send under real load could still exceed it and reopen a narrow timing side channel, documented as accepted at this project scale
2. Two small deviations from design.md File Changes table (a /login link for password recovery reachability, /login chosen as the fixed post-verify/reset redirect) — both reasonable and already recorded

## Specs Synced to Main (openspec/specs/)

### New Capability Specs Created
1. **email-verification** — `openspec/specs/email-verification/spec.md`
   - Verification Token Issuance on Registration (on-commit, 24h expiry)
   - Verification Token Consumption (valid/used/expired/invalid)
   - Resend Verification with 60s Cooldown + 5/hr Cap
   - Non-Blocking Verification (never gates login/routes)
   - 10 scenarios, all covered by passing tests

2. **password-reset** — `openspec/specs/password-reset/spec.md`
   - Anti-Enumeration Reset Request (identical response for existing/non-existent/throttled)
   - Reset Token Issuance (1h expiry, on-commit)
   - Confirm Reset (password change + is_verified=true + invalidate other tokens)
   - 11 scenarios, all covered by passing tests

3. **transactional-email** — `openspec/specs/transactional-email/spec.md`
   - Env-Driven Email Configuration (EMAIL_BACKEND/HOST/PORT from env, no Mailpit literal)
   - Dev-Only Mailpit Wiring (docker-compose service)
   - Plain-Text Message Dispatch (send_mail, no HTML/templates)
   - On-Commit Dispatch (never sent inside open transaction)
   - 5 scenarios, all covered by passing tests

4. **web-account-recovery** — `openspec/specs/web-account-recovery/spec.md`
   - Verify-Email Screen (/verify-email, searchParams token + manual fallback)
   - Forgot-Password Request Screen (/forgot-password, always generic confirmation)
   - Reset-Password Confirm Screen (/reset-password, token+new password)
   - Dismissible Verify-Email Banner on Dashboard (shown when is_verified=false)
   - 9 scenarios, all covered by passing tests

### Modified Main Spec
1. **user-authentication** — `openspec/specs/user-authentication/spec.md` (MERGED)
   - **ADDED**: User Verification Status Field requirement (is_verified boolean, default false, non-gating)
   - **MODIFIED**: Registration requirement extended to include single-use email verification token creation and transaction.on_commit dispatch
   - New scenario: "Registration schedules a verification email on commit"
   - All existing scenarios preserved (Successful registration, Weak password rejected, Duplicate email rejected)

## Archive Contents Verified

- [x] proposal.md — 5 open product decisions recorded
- [x] specs/ — 5 domain specs (4 NEW fully copied, 1 delta merged)
- [x] design.md — 6 ADRs documented and verified
- [x] tasks.md — 24/24 tasks complete and checked
- [x] verify-report.md — PASS verdict recorded (amended post-warning fix)

## Mechanical Copy Evidence

**NEW Domain Specs Copied** (shell `cp -R`, verified with `diff`):
```
email-verification: PASS (empty diff)
password-reset: PASS (empty diff)
transactional-email: PASS (empty diff)
web-account-recovery: PASS (empty diff)
```

**Change Folder Moved to Archive** (shell `mv`, verified with `diff -r`):
```
Source snapshot → openspec/changes/archive/2026-09-11-email-verification-password-reset
Verification: PASS (empty diff, no bytes altered or truncated)
```

## SDD Cycle Complete

This change has been fully planned (proposal), specified (5 specs, 41 scenarios), designed (6 ADRs), implemented (24 tasks, 401 changed lines), verified (PASS with 0 CRITICAL, 0 open WARNING), and archived.

**Ready for deployment and next SDD cycle.**

---

**Archive Report Created**: 2026-09-11  
**Orchestrator**: sdd-archive  
**Artifact Store Mode**: hybrid (Engram + openspec)  
**Observation IDs**: #496 (proposal), #498 (spec), #497 (design), #499 (tasks), #501 (verify-report)
