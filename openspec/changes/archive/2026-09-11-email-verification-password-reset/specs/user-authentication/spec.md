# Delta for User Authentication

## ADDED Requirements

### Requirement: User Verification Status Field

The `User` model MUST carry an `is_verified` boolean field, defaulting to `false` on creation.
This field is informational only: it MUST NOT gate login, session creation, or access to any
protected route (see `email-verification` § "Non-Blocking Verification" for the full contract).

#### Scenario: New user defaults to unverified
- GIVEN a new `User` is created via registration
- WHEN the record is inspected
- THEN `is_verified` is `false`

#### Scenario: Unverified user is not blocked from any route
- GIVEN a registered user with `is_verified = false`
- WHEN they log in and access any protected endpoint
- THEN access succeeds exactly as for a verified user

## MODIFIED Requirements

### Requirement: Registration

The system MUST allow an anonymous visitor to register with an email and password, creating a
`User`, one provisioned `Organization`, an `OWNER` `Membership`, and an authenticated session,
all in the same atomic transaction. The system MUST validate the password against Django's
configured password validators. The system MUST additionally create a single-use email
verification token for the new `User` within that same transaction and schedule its delivery via
`transaction.on_commit`, per `email-verification` § "Verification Token Issuance on
Registration".
(Previously: registration created `User`, `Organization`, `Membership`, and session only, with
no verification token or email dispatch.)

#### Scenario: Successful registration
- GIVEN an anonymous visitor submits a unique email and a valid password
- WHEN the registration endpoint is called
- THEN a `User` record is created
- AND the response establishes an authenticated session

#### Scenario: Weak password rejected
- GIVEN an anonymous visitor submits a password that fails a configured validator
- WHEN the registration endpoint is called
- THEN the request is rejected with a validation error
- AND no `User` record is created

#### Scenario: Duplicate email rejected
- GIVEN a registered user already owns an email
- WHEN a new registration is attempted with the same (or case-variant) email
- THEN the request is rejected with a clear, tested error
- AND no new `User` record is created

#### Scenario: Registration schedules a verification email on commit
- GIVEN an anonymous visitor submits a unique email and a valid password
- WHEN the registration transaction commits
- THEN a single-use verification token exists for the new user
- AND a verification email is dispatched only after that commit, never before
