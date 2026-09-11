# Verification Report: email-verification-password-reset

**Mode**: Full artifacts (proposal, specs, design, tasks all present)
**Verdict**: PASS

## Completeness

- Tasks: 24/24 checked in tasks.md, all correspond to real, inspected code and passing tests (Phases 1-7).
- Specs: 5 spec files, 17 requirements, 41 scenarios - every scenario mapped to implementing code and a passing covering test.
- Design: 6 ADRs (DD1-DD6) in design.md, including the post-hoc "Timing-parity limit" resolution note under Open Questions - all followed by the actual code.

## Test Execution Evidence (run independently by this verify pass)

- Backend: docker compose exec -T backend pytest -q -> 233 passed in 20.19s, 0 failed.
- Frontend: docker compose exec -T frontend npx vitest run -> 168 passed (38 files), 0 failed.

## Spec Compliance Matrix (by domain)

### email-verification (4 requirements / 10 scenarios) - PASS
- Verification Token Issuance on Registration: register_user (services.py:72-73) creates the token inside the atomic block and schedules send_verification_email via transaction.on_commit. Covered by test_services_email_verification.py::TestRegisterUserSchedulesVerificationEmail using django_capture_on_commit_callbacks(execute=True) - confirmed the real fixture is used, not a vacuous pytest.mark.django_db-only test. Rollback scenario (test_rolled_back_registration_creates_no_token_and_sends_no_email) confirmed with monkeypatched organization-provisioning failure.
- Verification Token Consumption: verify_email (services.py:89-109) checks used/expired/invalid in that order; all 4 scenarios covered by TestVerifyEmail in the same file.
- Resend Verification with Cooldown/Cap: resend_verification + _cooldown_active/_hourly_cap_reached (services.py:112-144); all 3 scenarios covered by test_services_resend_verification.py with explicit created_at backdating (59s/61s, 5th/6th).
- Non-Blocking Verification: is_verified is never read by any auth/session/permission check (confirmed via register_user/authenticate_user/session middleware inspection) - no gating code exists anywhere in the login or route-protection path.

### password-reset (3 requirements / 11 scenarios) - PASS
- Anti-Enumeration Reset Request: request_password_reset (services.py:147-168) returns None on every path - existing, non-existent, and throttled - matching the exact current spec wording (status/body parity, not exact timing parity). The non-match and throttled branches call time.sleep(_RESET_ANTI_ENUMERATION_DELAY_SECONDS) (0.3s) before returning; the hit branch does not sleep. Verified with real test evidence, not just source inspection:
  - Service-level (test_services_password_reset.py): test_existing_account_..._no_artificial_delay asserts sleep_calls == [] on the hit path; test_nonexistent_account_..._applies_fixed_delay and test_throttled_existing_account_..._applies_fixed_delay both assert sleep_calls == [services._RESET_ANTI_ENUMERATION_DELAY_SECONDS].
  - API-level (test_api_password_reset.py): test_existing_and_nonexistent_email_return_byte_identical_responses and test_throttled_response_is_also_byte_identical both assert status code AND response.content byte-identity - exactly the wording change ("status/body parity ... not exact timing parity") this task description flagged as edited mid-cycle.
- Reset Token Issuance: 1h expiry via _EXPIRY_HOURS["reset"] = 1 in tokens.py; on_commit dispatch verified; scenario covered by test_reset_token_expiry_is_exactly_one_hour.
- Confirm Reset: confirm_password_reset (services.py:171-206) validates the new password, sets password + is_verified=True in one save(update_fields=[...]), marks the token used, and invalidates every other outstanding reset token via a bulk .exclude(pk=email_token.pk).update(used_at=now) query scoped to purpose="reset", used_at__isnull=True. All 6 scenarios covered by TestConfirmPasswordReset, including sibling-token invalidation (test_successful_reset_invalidates_other_outstanding_reset_tokens).

### transactional-email (4 requirements / 5 scenarios) - PASS
- Env-Driven Email Configuration: confirmed directly in backend/config/settings.py lines 165-173 - EMAIL_BACKEND/EMAIL_HOST/EMAIL_PORT/EMAIL_TIMEOUT/DEFAULT_FROM_EMAIL/FRONTEND_BASE_URL all resolve via env(...) with generic defaults (smtp backend, localhost, 25, webmaster@localhost). No Mailpit-specific literal appears in settings.py.
- Dev-Only Mailpit Wiring: docker-compose.yml defines a mailpit service (image axllent/mailpit:latest, ports 8025/1025) with a comment confirming it is reached only via backend/.env pointing EMAIL_HOST/EMAIL_PORT at it - never referenced elsewhere.
- Plain-Text Message Dispatch: emails.py uses send_mail with a message= string only, no HTML/template.
- On-Commit Dispatch: confirmed in both register_user and resend_verification/request_password_reset (transaction.on_commit(lambda: ...)), test-proven via django_capture_on_commit_callbacks.
- Confirmed the exact security-relevant claim from the task description: backend/env.example correctly scopes EMAIL_HOST=mailpit to the dev-only example file (line 48), never to settings.py itself, which only holds env-driven generic defaults.

### web-account-recovery (4 requirements / 9 scenarios) - PASS
- Verify-Email Screen: VerifyEmailForm.tsx reads token from searchParams, auto-submits once (useRef guard), falls back to a manual paste field when absent, redirects via router.replace("/login") on success, surfaces ApiError.detail on failure. Covered by VerifyEmailForm.test.tsx (5 tests).
- Forgot-Password Request Screen: ForgotPasswordForm.tsx always renders the same GENERIC_CONFIRMATION string regardless of whether the request call throws. Covered by ForgotPasswordForm.test.tsx (3 tests).
- Reset-Password Confirm Screen: ResetPasswordForm.tsx reads token, collects password, redirects via router.replace("/login"), surfaces ApiError.detail inline. Covered by ResetPasswordForm.test.tsx (2 tests).
- Dismissible Verify-Email Banner: VerifyEmailBanner.tsx renders null for unauthenticated/verified/dismissed, uses verifyBannerDismissedAtom - confirmed to be a plain atom(false) in state/session.ts (line 34), NOT atomWithStorage/localStorage, exactly matching DD6. Covered by VerifyEmailBanner.test.tsx (5 tests) and dashboard mount test.

### user-authentication delta (2 requirements / 6 scenarios) - PASS
- User Verification Status Field: User.is_verified field confirmed in models.py (default False), never read by any gating path.
- Registration (MODIFIED): confirmed token creation + transaction.on_commit wiring inside register_user; all 4 scenarios (successful, weak password, duplicate email, schedules verification email on commit) covered.

## Design Coherence (DD1-DD6) - all followed, no unresolved deviations

- DD1 (fast SHA-256 hash, secrets.token_urlsafe(32) raw token): confirmed in tokens.py - hash_token/issue_token. The raw token is returned only to the caller for the email link and is never persisted or logged; only token_hash is stored, unique-indexed.
- DD2 (single table, purpose column): confirmed - one EmailToken model with purpose choices, shared by both flows.
- DD3 (throttle via created_at queries, no new dependency): confirmed - _cooldown_active/_hourly_cap_reached query the existing table; no cache/middleware/django-ratelimit added.
- DD4 (anti-enumeration in the service, not the view): confirmed - request_password_reset returns None on every path including both new fixed-delay branches; api.py request_password_reset view always returns the same module-level _RESET_REQUEST_MESSAGE constant object regardless of the service invisible outcome.
- DD5 (FRONTEND_BASE_URL env var, no literal host): confirmed in emails.py/settings.py.
- DD6 (banner dismissal is session-only, not localStorage): confirmed as above.

## Task Completion vs. Code State

All 24 tasks.md checkboxes are genuinely [x] and correspond to real, inspected, tested code (not placeholder/stub implementations). Cross-checked against the apply-progress artifact TDD cycle evidence table (RED command/result, GREEN command/result per task group) - consistent with what the code and tests on disk actually show.

## Issues Found

### CRITICAL
None.

### WARNING
1. Documented, spec-safe deviation from tasks.md task 6.1 wording: task 6.1 says "Create Suspense-wrapped app/(auth)/{verify-email,forgot-password,reset-password}/page.tsx" (all three), but forgot-password/page.tsx is NOT Suspense-wrapped. Verified directly: ForgotPasswordForm never calls useSearchParams() (confirmed by reading the component - it only uses local useState), so no boundary is functionally required, and verify-email/reset-password (which do call useSearchParams()) are correctly wrapped. This matches the existing (auth)/register/page.tsx precedent in the repo and is explicitly documented in both the apply-progress artifact and an inline code comment. No spec scenario requires a Suspense boundary - this is a tasks.md wording imprecision, not a functional defect.

### SUGGESTION
1. The anti-enumeration fixed delay is a module-level constant (_RESET_ANTI_ENUMERATION_DELAY_SECONDS = 0.3, services.py line 37). This is explicitly an accepted residual-risk design decision (design.md "Timing-parity limit", resolved by the user) - flagging only for visibility: a slow SMTP send under real load could still exceed 0.3s and reopen a narrow timing side channel. This is already documented as an accepted risk at this project scale and is not a defect against the current spec wording.
2. Two small deviations from design.md File Changes table were made and documented in the apply-progress artifact: (a) a link added to /login for password recovery reachability (not in the original file list, low-risk), and (b) the fixed redirect destination after verify/reset success was chosen as /login (spec only required a fixed literal path, did not mandate which). Both are reasonable, low-risk, and already recorded - no action needed.

## Post-verify amendment (orchestrator, same session, before archive)

Per this project's standing convention across all SDD cycles this session — fix every verify WARNING before archiving, never defer as debt — WARNING 1 was resolved: `tasks.md` task 6.1's wording was corrected to explicitly state that Suspense-wrapping only applies where `useSearchParams()` is actually called (verify-email, reset-password), matching the existing `register/page.tsx` precedent for `forgot-password`. No code changed — the code was already correct; only the task wording that caused the false-positive WARNING was fixed.

## Final Verdict

PASS — 0 CRITICAL, 0 open WARNING, 2 informational SUGGESTIONs remaining (both non-blocking, already-accepted residual risks/deviations, no action needed). Ready for `sdd-archive`.
