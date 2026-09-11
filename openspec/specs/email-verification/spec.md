# Email Verification Specification

## Purpose

Give the system an ownership signal for a registered email address: a single-use, expiring
token emailed on registration, a confirm endpoint that flips `User.is_verified`, and a
throttled resend path. Verification is informational only — it never gates login or any route.

## Requirements

### Requirement: Verification Token Issuance on Registration

Registration MUST create a single-use verification token (hashed at rest, `purpose="verify"`,
24h expiry) for the new `User` and MUST schedule its delivery via `transaction.on_commit` inside
the registration transaction. The system MUST NOT send the email before the transaction commits.

#### Scenario: Registration schedules a verification email
- GIVEN an anonymous visitor completes registration successfully
- WHEN the registration transaction commits
- THEN exactly one verification token exists for the new user
- AND a verification email containing a link with that token is sent

#### Scenario: Rolled-back registration sends no email
- GIVEN a registration fails after the token would have been created (e.g. organization
  provisioning fails)
- WHEN the transaction rolls back
- THEN no verification token persists
- AND no email is sent

### Requirement: Verification Token Consumption

The system MUST let a caller submit a verification token to mark the corresponding `User` as
`is_verified = true`, and MUST mark the token used (`used_at` set) so it cannot be reused.

#### Scenario: Valid token verifies the user
- GIVEN an unexpired, unused verification token for a user
- WHEN that token is submitted to the confirm-verification endpoint
- THEN the user's `is_verified` becomes `true`
- AND the token is marked used

#### Scenario: Already-used token is rejected
- GIVEN a verification token that was already consumed
- WHEN it is submitted again
- THEN the request is rejected with a specific "token already used" error
- AND the user's `is_verified` value does not change

#### Scenario: Expired token is rejected
- GIVEN a verification token whose `expires_at` is in the past
- WHEN it is submitted to the confirm-verification endpoint
- THEN the request is rejected with a specific "token expired" error

#### Scenario: Invalid or unknown token is rejected
- GIVEN a token string that does not match any stored verification token
- WHEN it is submitted to the confirm-verification endpoint
- THEN the request is rejected with a specific "token invalid" error

### Requirement: Resend Verification with Cooldown and Hourly Cap

The system MUST let an unverified user request a new verification email, MUST reject a resend
within 60 seconds of the caller's last verification token, and MUST reject a resend once the
caller has reached 5 verification tokens within the trailing rolling hour.

#### Scenario: Resend within cooldown is rejected
- GIVEN a user requested a verification token less than 60 seconds ago
- WHEN they call resend-verification again
- THEN the request is rejected with a specific cooldown error
- AND no new token is created

#### Scenario: Resend after cooldown is accepted
- GIVEN a user's last verification token was created more than 60 seconds ago
- WHEN they call resend-verification
- THEN a new verification token is created and emailed
- AND the previous token remains valid until its own expiry or use

#### Scenario: Hourly resend cap is enforced
- GIVEN a user has created 5 verification tokens within the last rolling hour
- WHEN they call resend-verification again
- THEN the request is rejected with a specific rate-limit error
- AND no new token is created

### Requirement: Non-Blocking Verification

`is_verified` MUST NOT gate login, session creation, or access to any protected route.

#### Scenario: Unverified user retains full access
- GIVEN a registered user whose `is_verified` is `false`
- WHEN they log in and call any protected endpoint
- THEN every request succeeds exactly as it would for a verified user
