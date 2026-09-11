# Transactional Email Specification

## Purpose

Provide the env-driven mail mechanism that `email-verification` and `password-reset` dispatch
through: plain-text messages, a dev-only Mailpit catcher, and commit-safe delivery timing. This
spec covers the mechanism only, not the message content or triggers owned by those capabilities.

## Requirements

### Requirement: Env-Driven Email Configuration

The system MUST resolve `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, and related mail settings
from environment variables in `settings.py`, with no Mailpit-specific literal hardcoded in
`settings.py`. `backend/env.example` MUST document every `EMAIL_*` variable with a dev-safe
default.

#### Scenario: Settings resolve entirely from environment
- GIVEN `EMAIL_HOST` and `EMAIL_PORT` are set in the environment to the Mailpit dev values
- WHEN Django settings are loaded
- THEN the mail backend connects using those exact env-provided values
- AND no Mailpit hostname or port appears as a literal in `settings.py`

#### Scenario: Missing EMAIL_* falls back safely
- GIVEN no `EMAIL_*` environment variables are set
- WHEN Django settings are loaded
- THEN the system falls back to Django's default email backend
- AND no other application behavior regresses

### Requirement: Dev-Only Mailpit Wiring

`docker-compose.yml` MUST define a `mailpit` service (SMTP `1025`, web UI `8025`) usable only
when the backend's `EMAIL_*` env vars point to it; the service MUST NOT be referenced by any
production configuration.

#### Scenario: Mailpit receives dev-sent mail
- GIVEN the backend is configured with `EMAIL_HOST`/`EMAIL_PORT` pointing at the `mailpit`
  compose service
- WHEN a verification or reset email is sent
- THEN the message is retrievable from the Mailpit web UI on port `8025`

### Requirement: Plain-Text Message Dispatch

Verification and reset emails MUST be sent as plain text via Django's `send_mail`, with copy
built in `backend/apps/users/emails.py`. The system MUST NOT use an HTML template or template
file for these messages.

#### Scenario: Sent message has no HTML body
- GIVEN a verification or reset email is dispatched
- WHEN the sent message is inspected
- THEN it carries only a plain-text body and no HTML alternative

### Requirement: On-Commit Dispatch

Any email triggered by a database write MUST be scheduled via `transaction.on_commit` and MUST
NOT be sent while the enclosing transaction is still open.

#### Scenario: No email is sent for a transaction that never commits
- GIVEN a database transaction registers an on-commit email callback
- WHEN that transaction is rolled back instead of committed
- THEN the email is never sent
