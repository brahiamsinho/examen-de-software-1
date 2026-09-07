# Delta for Organization Tenancy

## ADDED Requirements

### Requirement: Server-Generated Organization Slug

The system MUST provide a slug-generation utility used when a caller (e.g. registration) does
not supply a slug. The base MUST be `slugify(source)[:40]`; if the slugified result is empty,
the base MUST be the literal `workspace`. Every attempt MUST always append a suffix — bare-base
values MUST NOT be tried — so the clean namespace stays available for deliberate organization
creation. Attempts 1 through 5 MUST use `f"{base}-{secrets.token_hex(3)}"` (a fresh 6-character
lowercase hex token per attempt). If all 5 attempts collide, a final attempt 6 MUST use
`f"workspace-{secrets.token_hex(8)}"`. If that also collides, the utility MUST raise an
`OrganizationError` rather than persist a duplicate or malformed slug. Every generated slug
MUST stay within `SlugField(max_length=60)` and MUST remain non-sequential, inheriting the
`Organization Entity` requirement's no-tenant-count-leakage constraint.

#### Scenario: Base derived from a normal source string

- GIVEN a source string `"Acme Corp"`
- WHEN a slug is generated
- THEN the base is `acme-corp`
- AND the generated slug is `acme-corp-{6 lowercase hex chars}`

#### Scenario: Non-Latin source falls back to the literal base

- GIVEN a source string that slugifies to an empty string
- WHEN a slug is generated
- THEN the base used is the literal `workspace`

#### Scenario: First attempt is never a bare base

- GIVEN any source string
- WHEN a slug is generated and no collision occurs
- THEN the returned slug is `{base}-{6-hex-char suffix}`, never the bare `{base}` alone

#### Scenario: Collision retried up to 5 suffixed attempts

- GIVEN the first 4 generated `{base}-{hex}` candidates already exist as slugs
- WHEN slug generation is attempted
- THEN a 5th `{base}-{hex}` candidate is tried
- AND if it does not collide, that candidate is returned

#### Scenario: Exhaustion falls back to the final long-token form

- GIVEN all 5 `{base}-{hex}` attempts collide
- WHEN slug generation continues
- THEN a 6th attempt uses the form `workspace-{16 lowercase hex chars}`
- AND if it does not collide, that candidate is returned

#### Scenario: Total exhaustion raises an error

- GIVEN all 5 `{base}-{hex}` attempts and the final `workspace-{token}` attempt all collide
- WHEN slug generation is attempted
- THEN the utility raises `OrganizationError`
- AND no slug is returned

#### Scenario: Generated slug never exceeds the field length

- GIVEN any base string up to 40 characters after truncation
- WHEN a slug is generated at any attempt
- THEN the resulting slug length is always at most 47 characters, within `SlugField(max_length=60)`
