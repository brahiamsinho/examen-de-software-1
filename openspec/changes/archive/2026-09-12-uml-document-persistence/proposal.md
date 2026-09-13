# Proposal: UML Document Persistence + API

## Intent

`uml_modeling` (Cycle 1) defines the pure `ProjectDocument` domain and
`uml_commands` (Cycle 2) provides a validated, testable way to mutate it —
but nothing today stores a `ProjectDocument` anywhere, and no consumer can
reach it over HTTP. Every diagram edit built so far lives only in a test's
local variable; there is no way for a real client (frontend, future
assistant, XMI import) to create a document, submit a command against it,
or read back the result. This cycle closes that gap: it persists
`ProjectDocument` as a tenant-scoped Django model and exposes the minimum
API surface (create, read, submit-command) needed for a client to actually
use the command bus built in Cycle 2.

## Scope

### In Scope

- New sibling Django app `backend/apps/uml_documents/`, depending on
  `apps.uml_modeling` and `apps.uml_commands` (plus stdlib/Django/ninja).
- `UmlDocument(TenantScopedModel)`: a tenant-scoped Django model persisting
  a serialized `ProjectDocument`, following the `Membership` /
  `TenantScopedModel` pattern from `apps/organizations` exactly (no new
  tenancy mechanism).
- A new `codec.py` module: dataclass ↔ JSON conversion for
  `CanonicalUmlModel`/`DiagramLayout`, built from scratch (no existing
  helper to reuse or extend). Must correctly round-trip
  `Mapping[ElementId, ...]` keys and nested frozen-dataclass tuples —
  `dataclasses.asdict` alone is insufficient.
- `services.py`: thin functions — `create_document`, `get_document`,
  `submit_command` (the latter calling
  `apps.uml_commands.dispatcher.apply(document, command, now=...)` and
  persisting the resulting document).
- `api.py`: one generic command-submission endpoint (`{type, payload}`
  mapped to the closed `UmlCommand` union via a discriminated-union
  `ninja.Schema` — the first such schema in this codebase), plus the
  minimum CRUD needed for a client to use it: create-document and
  get-document.
- `owner_id` population: `str(request.user.id)` on document creation,
  following the existing opaque-string convention documented in
  `uml_modeling`.
- New migrations for `uml_documents` (sequential, mirroring
  `organizations`' numbering convention).

### Out of Scope

- **Optimistic concurrency.** The commands endpoint applies the command
  and returns the new state; it does not check a client-supplied expected
  revision (no `If-Match`, no 409-on-mismatch). Deferred to a future cycle
  once real collaborative editing exists — this codebase has zero
  precedent for this pattern today.
- **Per-command explicit endpoints** (one route per `UmlCommand` type).
  Rejected in favor of the single generic endpoint, which mirrors the
  closed-union domain type directly.
- Any change to `apps/uml_commands/` — it stays exactly as documented
  (pure, DB-free command dispatch; no `models.py`/`api.py` added there),
  same discipline that kept `apps/uml_modeling/` untouched in Cycle 2.
- Any change to `apps/uml_modeling/` — stays frozen/pure.
- Undo/redo, command history/log, command stack — still deferred (carried
  over from Cycle 2's own deferral, unchanged here).
- Frontend/canvas UI — confirmed via exploration that zero diagram UI
  exists in `frontend/src/`; this cycle is backend-only.
- Document listing, deletion, metadata-only update, or any endpoint beyond
  create/get/submit-command — first-cut surface only, to keep this cycle's
  reviewable diff proportional to what a client needs to exercise the
  command bus end-to-end.

## Capabilities

### New Capabilities

- `uml-document-persistence`: `UmlDocument` model, the dataclass↔JSON
  codec, `services.py`, and the create/get/submit-command API endpoints.

### Modified Capabilities

None. `apps/uml_modeling/` and `apps/uml_commands/` both stay untouched.

## Approach

New app `backend/apps/uml_documents/`:

- **`models.py`** — `UmlDocument(TenantScopedModel)`:
  - `id`: `UUIDField(primary_key=True)` — matches `ProjectDocument.id`.
  - `organization`: inherited from `TenantScopedModel` (FK, tenant scope).
  - `owner_id`: `CharField` — mirrors `ProjectDocument.owner_id`.
  - `revision`: `PositiveIntegerField` — mirrored as a real column (not
    only inside the JSON blob) so a future concurrency cycle can check it
    without a migration; not read/compared against a client value this
    cycle.
  - `created_at` / `updated_at`: `DateTimeField`.
  - `data`: `JSONField` — the codec's serialized `metadata`, `model`
    (`CanonicalUmlModel`), and `layout` (`DiagramLayout`); the columns
    above are denormalized out of this blob for queryability, the blob
    remains the source of truth for document content.
  - `objects = TenantScopedManager()`, `all_objects = models.Manager()`,
    `base_manager_name = "all_objects"` — identical contract to
    `Membership`.

- **`codec.py`** — `to_json(document: ProjectDocument) -> dict` /
  `from_json(data: dict) -> ProjectDocument`, handling `ElementId`-keyed
  mappings (stringify keys for JSON, restore on decode) and tuple-typed
  nested dataclasses (`UmlClass.attributes`, `Enumeration.literals`, etc).

- **`services.py`**:
  - `create_document(organization, owner_id, name, *, now) -> UmlDocument`
    — builds an initial empty `ProjectDocument`, encodes it, persists it.
  - `get_document(organization, doc_id) -> UmlDocument`.
  - `submit_command(organization, doc_id, command, *, now) -> CommandResult`
    — loads the row, decodes to `ProjectDocument`, calls
    `apps.uml_commands.dispatcher.apply(document, command, now=now)`,
    encodes and persists the resulting document, returns the
    dispatcher's `CommandResult` unchanged (document + `ValidationResult`).

- **`api.py`** — `documents_router = Router(auth=django_auth)`, mounted in
  `backend/config/api.py`. Every handler resolves membership first
  (`resolve_membership(request, org_slug)`), matching the
  `organizations/api.py` tenant-isolation contract.

First-cut endpoint list:

| Method & Path | Purpose |
|---|---|
| `POST /orgs/{org_slug}/documents` | Create a new, empty document |
| `GET /orgs/{org_slug}/documents/{doc_id}` | Read back the full document (metadata + model + layout + revision) |
| `POST /orgs/{org_slug}/documents/{doc_id}/commands` | Submit one `{type, payload}` command; applies via the dispatcher and returns the resulting revision + validation diagnostics |

`schemas.py` gains a discriminated-union `CommandIn` (one payload schema
per `UmlCommand` subtype, `type: Literal[...]` discriminator field) and a
`CommandResultOut` mirroring `CommandResult` (`revision`,
`validation: {is_valid, violations}`).

## Affected Areas

| Area | Impact |
|---|---|
| `backend/apps/uml_documents/` | New |
| `backend/config/settings.py` | Modified (`INSTALLED_APPS`) |
| `backend/config/api.py` | Modified (mount `documents_router`) |
| `backend/apps/uml_commands/` | Untouched |
| `backend/apps/uml_modeling/` | Untouched |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Codec fails to round-trip `Mapping[ElementId, ...]` keys or nested tuple dataclasses losslessly | Medium | Flagged for sdd-spec/sdd-design: require round-trip unit tests against real `CanonicalUmlModel`/`DiagramLayout` fixtures before trusting the codec |
| Discriminated-union schema is the first of its kind in this codebase — parsing/validation-error shape is unproven | Medium | Flagged for sdd-spec: define exact 422 error shape for an unknown/malformed `type` |
| No concurrency guard: concurrent `submit_command` calls on the same document silently last-write-wins | Accepted (explicit user decision) | Documented here as an explicit out-of-scope deferral, not an oversight |

## Rollback Plan

Self-contained new app: one `INSTALLED_APPS` line, one router-mount line in
`config/api.py`, its own migrations. Revert via `git revert` or delete the
app, its settings line, and its router mount.

## Dependencies

None new. Reuses `apps.uml_modeling` and `apps.uml_commands` public APIs,
stdlib (`uuid`, `dataclasses`), and the existing django-ninja/Pydantic
stack already used by `apps/organizations`.

## Success Criteria

- [ ] `POST /orgs/{org_slug}/documents` creates a tenant-scoped
      `UmlDocument` and returns its initial state.
- [ ] `GET /orgs/{org_slug}/documents/{doc_id}` returns the full decoded
      document, scoped to the caller's organization (404 for cross-tenant
      access, matching the `organizations` isolation contract).
- [ ] `POST .../commands` accepts any of the 7 `UmlCommand` payloads via
      the discriminated-union schema, applies it through
      `dispatcher.apply`, persists the new revision, and returns the
      resulting revision + validation diagnostics.
- [ ] The codec round-trips a `CanonicalUmlModel`/`DiagramLayout` fixture
      losslessly (property/unit tested).
- [ ] `apps/uml_modeling/` and `apps/uml_commands/` have zero diff.
- [ ] `uml_documents` imports only `apps.uml_modeling`, `apps.uml_commands`,
      stdlib, and Django/ninja — never `django.contrib.auth` inside the
      codec or services layer (mirrors `uml_modeling`'s opaque-`owner_id`
      constraint).

## Proposal question round

Three scope decisions and two implementation details were already
confirmed by the user before this proposal was written (Engram
`sdd/uml-document-persistence/scope-decisions`, obs #518): app placement
(new sibling app), API shape (one generic command endpoint), and
concurrency (deferred) — plus codec-from-scratch and
`str(request.user.id)` for `owner_id`. Given those, only two genuinely open
product questions remain, both flagged for `sdd-spec`/`sdd-design` with a
working assumption stated below rather than left unresolved:

1. **Permission/role to submit a command.** `apps/organizations` enforces
   `require_role` before any mutation. Should `POST .../commands` require
   `EDITOR` (or higher), with `VIEWER` restricted to `GET`? *Working
   assumption: yes — mutating commands require `EDITOR`+, matching the
   existing membership-role mutation pattern; `GET` is open to any member.*
2. **Document creation inputs.** `create_document` needs at least a name
   for the initial `ProjectMetadata`. Is a bare `{name}` body sufficient
   for the first-cut `POST /documents`, or does the client need to supply
   more at creation time (e.g. initial classes)? *Working assumption:
   `{name}` only — an empty `CanonicalUmlModel`/`DiagramLayout` is created,
   and all structural content arrives via subsequent commands, since that
   is exactly what the command bus exists for.*

If either assumption is wrong, correct it now or during `sdd-spec`; both
are cheap to change since they affect only request-schema shape and a
`require_role` call, not the model/codec/dispatcher wiring described above.
