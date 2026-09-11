# Password Reset Specification

## Purpose

Give a locked-out user a self-service recovery path: an anti-enumeration reset request, a
single-use 1h reset token emailed on request, and a confirm endpoint that changes the password
and also proves mailbox ownership.

## Requirements

### Requirement: Anti-Enumeration Reset Request

The system MUST accept a reset request containing only an email and MUST return the identical
generic response regardless of whether that email belongs to a registered account, and
regardless of whether the request was throttled. The response MUST NOT reveal account existence
through status code or body.

The system MUST apply a fixed artificial delay to the non-match and throttled paths so their
response time approximates the existing-account path (which performs a real email dispatch).
This narrows, but does not eliminate, an observable-timing side channel: exact parity is not
achievable within this change's scope (it would require moving email dispatch to a background
worker/queue, which is explicitly out of scope). The residual timing gap is an accepted risk at
this project's scale, not a defect of this requirement.

#### Scenario: Request for an existing account
- GIVEN a registered account with email `alice@example.com`
- WHEN a reset is requested for that email
- THEN the response is the generic "check your email" response
- AND a reset token is created and emailed to that address

#### Scenario: Request for a non-existent account
- GIVEN no account exists with email `ghost@example.com`
- WHEN a reset is requested for that email
- THEN the response is byte-identical to the existing-account response
- AND no token is created and no email is sent

#### Scenario: Throttled request still returns the generic response
- GIVEN a registered account that already has an outstanding, recently-issued reset token
  subject to the same cooldown/cap rules as verification resend
- WHEN a reset is requested again for that account
- THEN the response is byte-identical to the unthrottled response
- AND no new token is created

#### Scenario: Non-match and throttled paths apply the fixed timing-parity delay
- GIVEN a reset request that does not result in an email being sent (no matching account, or
  throttled)
- WHEN the response is returned
- THEN a fixed artificial delay was applied before responding, approximating the response time of
  the email-sending path

### Requirement: Reset Token Issuance

A successful reset request MUST create a single-use reset token (hashed at rest,
`purpose="reset"`, 1h expiry) and MUST schedule its email via `transaction.on_commit`.

#### Scenario: Reset token expiry is one hour
- GIVEN a reset token is created for a request
- WHEN its `expires_at` is inspected
- THEN it is exactly one hour after creation

### Requirement: Confirm Reset

The system MUST let a caller submit a reset token and a new password to change that user's
password, MUST validate the new password against the project's configured password validators,
MUST mark the token used, MUST invalidate every other outstanding reset token for that user, and
MUST also set `is_verified = true` on success.

#### Scenario: Successful reset changes password and verifies the user
- GIVEN an unexpired, unused reset token for a user with `is_verified = false`
- WHEN a valid new password is submitted with that token
- THEN the user's password is updated
- AND the user's `is_verified` becomes `true`
- AND the user can log in with the new password

#### Scenario: Successful reset invalidates other outstanding tokens
- GIVEN a user has two outstanding, unused reset tokens
- WHEN one of them is used to successfully confirm a reset
- THEN the other outstanding reset token is also invalidated
- AND submitting the other token afterward is rejected as invalid or used

#### Scenario: Weak new password rejected
- GIVEN an unexpired, unused reset token
- WHEN a password that fails a configured validator is submitted with that token
- THEN the request is rejected with a validation error
- AND the token remains unused and the password unchanged

#### Scenario: Expired reset token is rejected
- GIVEN a reset token whose `expires_at` is in the past
- WHEN it is submitted with a new password
- THEN the request is rejected with a specific "token expired" error
- AND the password is unchanged

#### Scenario: Already-used reset token is rejected
- GIVEN a reset token that was already consumed
- WHEN it is submitted again with a new password
- THEN the request is rejected with a specific "token already used" error
- AND the password is unchanged

#### Scenario: Invalid or unknown reset token is rejected
- GIVEN a token string that does not match any stored reset token
- WHEN it is submitted with a new password
- THEN the request is rejected with a specific "token invalid" error
