# User Authentication Specification

## Purpose

Establish the project's first persisted identity: a custom, email-identified `User` model
with session-based registration, login, logout, and current-user introspection, backed by
Argon2 password hashing and Django's password validators.

## Requirements

### Requirement: User Identity Model

The system MUST represent users with a custom `User` model using `AbstractBaseUser` and
`PermissionsMixin`, with `USERNAME_FIELD = "email"`. The system MUST NOT define a `username`
field. Email MUST be unique and normalized case-insensitively. Passwords MUST be hashed with
Argon2.

#### Scenario: Email uniqueness is case-insensitive

- GIVEN a registered user with email `alice@example.com`
- WHEN a new registration is attempted with email `Alice@Example.com`
- THEN the system rejects the registration as a duplicate email

#### Scenario: Password stored hashed

- GIVEN a user registers with a valid password
- WHEN the stored `User` record is inspected
- THEN the password field contains an Argon2 hash, never the plaintext value

### Requirement: Registration Provisions One Organization

Registration MUST provision exactly one `Organization` for the newly created `User`, in the
same atomic transaction as the `User` row, with the registrant as `OWNER`. Name and slug MUST
be derived per `organization-tenancy` § "Server-Generated Organization Slug" (source: stripped
`full_name` if non-empty, else the email local-part; name = `"{source}'s Workspace"`,
truncated to 120 chars). If organization provisioning fails, the entire transaction MUST roll
back — no `User` row may persist without its organization.

#### Scenario: Registration creates exactly one organization with the registrant as OWNER

- GIVEN an anonymous visitor submits a unique email and a valid password
- WHEN the registration endpoint is called
- THEN exactly one `Organization` is created
- AND a `Membership` binding the new `User` to that organization with role `OWNER` is created

#### Scenario: Organization provisioning failure rolls back the user

- GIVEN organization provisioning fails during registration (e.g. slug-generation exhaustion)
- WHEN the registration endpoint is called
- THEN no `User` record is persisted
- AND no `Organization` or `Membership` record is persisted

### Requirement: Registration

The system MUST allow an anonymous visitor to register with an email and password, creating a
`User`, one provisioned `Organization`, an `OWNER` `Membership`, and an authenticated session,
all in the same atomic transaction. The system MUST validate the password against Django's
configured password validators.
(Previously: the atomic unit was `User` only; organization provisioning is new.)

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

### Requirement: Session Login and Logout

The system MUST authenticate a registered user via email and password against session
authentication, and MUST invalidate the session server-side on logout.

#### Scenario: Successful login

- GIVEN a registered user with valid credentials
- WHEN the login endpoint is called with the correct email and password
- THEN the response establishes an authenticated session

#### Scenario: Invalid credentials rejected

- GIVEN a registered user
- WHEN the login endpoint is called with an incorrect password or an unknown email
- THEN the request is rejected with one generic error
- AND the response does not reveal whether the email exists

#### Scenario: Logout invalidates the session

- GIVEN an authenticated session
- WHEN the logout endpoint is called
- THEN the session is invalidated server-side
- AND a subsequent authenticated-only request with the same session fails as unauthenticated

### Requirement: Current User Introspection

The system MUST expose the authenticated caller's own identity, and MUST reject unauthenticated
requests.

#### Scenario: Authenticated introspection

- GIVEN an authenticated session
- WHEN the current-user endpoint is called
- THEN the response contains that user's own identity fields

#### Scenario: Unauthenticated introspection rejected

- GIVEN no authenticated session
- WHEN the current-user endpoint is called
- THEN the request is rejected with `401`

### Requirement: No Auto-Created Organization (REMOVED)

(Reason: directly inverted by the new "Registration Provisions One Organization" requirement —
its premise that "a freshly registered user legitimately belongs to zero organizations" is now
false for new registrations.)
(Migration: pre-change zero-org users are unaffected and are never backfilled; the test
`test_registration_does_not_auto_create_an_organization` is rewritten into its inverse — a
freshly registered user has exactly one organization — not deleted.)
