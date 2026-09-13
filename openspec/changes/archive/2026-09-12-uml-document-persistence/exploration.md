# Exploration: ProjectDocument persistence + API layer (consumer for the UmlCommand dispatcher)

## Current State — organizations pattern (the template)

`backend/apps/organizations/`:
- `models.py`: `Organization` (UUID PK, slug-addressed). `TenantScopedModel` (abstract base): one field `organization = ForeignKey("organizations.Organization", on_delete=CASCADE, related_name="%(class)ss", null=False)`; `objects = TenantScopedManager()`, `all_objects = models.Manager()`; `Meta.abstract=True`, `base_manager_name="all_objects"`. `TenantScopedManager.get_queryset()` raises `TenantScopeViolation` unless accessed via a bound related-instance manager — forces every unscoped default-manager access to go through `.for_organization(org)` or explicit `.unscoped()`. `Membership(TenantScopedModel)` is the only current subclass (FK to `user`, `role`, unique constraint on `(user, organization)`).
- `services.py`: thin plain functions (`add_member`, `remove_member`, `change_member_role`, `list_memberships`, `_assert_not_last_owner`) — no fat models/viewsets, business invariants live here, not in `models.py` or `api.py`.
- `api.py`: django-ninja `Router(auth=django_auth)` per resource (`organizations_router`, `memberships_router`). Every handler's first statement is `resolve_membership(request, org_slug)` (404s indistinguishably for unknown-slug vs non-member — tenant-isolation contract), then `require_role(membership, Role.X)` before mutating. Handlers are thin: parse schema → resolve membership → check role → call one service function → serialize via a small `_x_out(...)` dict helper. Exception handlers registered centrally (`register_exception_handlers`) mapping domain error types to HTTP status.
- Routers mounted in `backend/config/api.py` on one shared `NinjaAPI()`: `api.add_router("/orgs", organizations_router, ...)`, `api.add_router("/orgs/{org_slug}/members", memberships_router, ...)` — nested sub-resource pattern via URL-prefix mounting.
- `schemas.py`: plain `ninja.Schema` (Pydantic) classes, no ORM access; `Literal[...]` used for small closed string enums (`MemberAddIn.role: Literal["EDITOR","VIEWER"]`). No discriminated-union schema exists anywhere in this codebase yet.
- Migrations: sequentially numbered (`0001_initial.py`, `0002_initial.py`).
- `permissions.py`: `resolve_membership` + `require_role` — the only authorization mechanism.

## uml_modeling / uml_commands boundary (frozen from prior cycles)

- `ProjectDocument` (`backend/apps/uml_modeling/documents.py`): frozen dataclass, `id: UUID`, `metadata: ProjectMetadata`, `owner_id: str` (validated non-empty, deliberately opaque — module docstring: "MUST NOT import `django.contrib.auth` or any auth module"), `model: CanonicalUmlModel`, `layout: DiagramLayout`, `created_at`/`updated_at: datetime`, `revision: int = 1`. `with_model`/`with_layout` both `dataclasses.replace` + `revision + 1` + explicit `now`.
- `backend/apps/uml_commands/dispatcher.py::apply(document, command, *, now) -> CommandResult(document, validation_result)` is the exact, already-built consumer surface this cycle would wire into persistence+API. `_HANDLERS` dict keyed by exact command type; always re-runs `validate()` after mutation.
- `apps/uml_commands/apps.py` docstring: "no `models.py`: pure, DB-free command dispatch layer... built on top of `apps.uml_modeling`."
- **`test_import_boundary.py`** (AST-based): `_SCOPED_FILES = (commands.py, dispatcher.py, handlers/*.py)` — explicitly excludes `apps.py`/`__init__.py`/`tests/`. **Critical nuance**: this test's file scope does NOT include a hypothetical `models.py`/`api.py` — adding those to `apps/uml_commands/` would NOT literally trip this test, even though it would contradict the app's own docstring/stated intent. This is a real tension, not a test-enforced hard wall.

## Serialization Story

- Zero `JSONField` usage anywhere in `backend/`. No existing to-dict/from-dict/serialization helper for dataclasses; `ninja.Schema` classes in `organizations/schemas.py` map ORM model attributes directly, never a nested frozen-dataclass graph.
- `CanonicalUmlModel` contains tuples of frozen dataclasses (`UmlClass` with tuples of `UmlAttribute`/`UmlOperation`; `Enumeration` with tuple of `EnumerationLiteral`; `Relationship` with `RelationshipEnd`s), plus `generation_metadata: Mapping[ElementId, Mapping[str, object]]`. `DiagramLayout.positions: Mapping[ElementId, Position]`. **This would be entirely new work.** `dataclasses.asdict` alone would not correctly round-trip `Mapping[ElementId, ...]` keys/`ElementId` typing without a custom encoder/decoder.

## Tenant Scoping & Ownership

- `owner_id` is used only as an arbitrary opaque string in tests/factories (`"owner-1"`, `"42"`) — no existing code converts a real Django `User`/`request.user` into an `owner_id` value. That mapping (e.g. `str(request.user.id)`) does not exist yet.
- Following the `TenantScopedModel` contract exactly, a Django wrapper model for `ProjectDocument` would add one `organization = ForeignKey(Organization, on_delete=CASCADE, related_name="...", null=False)` field and inherit `objects = TenantScopedManager()` — mirroring `Membership`, the only current subclass. No new mechanism needed; the abstract base is directly reusable.

## API Shape Options & Tradeoffs

- Precedent (`organizations/api.py`) is **explicit per-operation routes on a per-resource `Router`**, not a generic dispatch endpoint — zero example anywhere in this codebase of a "command-name + payload" generic operation endpoint.
- **Option A — one generic endpoint** (e.g. `POST /orgs/{org_slug}/documents/{doc_id}/commands` taking `{type, payload}` mapped to the closed `UmlCommand` union): fewer endpoints, directly mirrors the closed-union domain type, but requires a discriminated-union Pydantic/ninja schema — a pattern this codebase has never used (only flat `Literal` fields exist today).
- **Option B — seven endpoints** (one per command): matches the existing "thin router, explicit named operation per route" style more literally; more boilerplate but no new schema-parsing pattern needed.

## Concurrency Considerations

- No `If-Match`/optimistic-concurrency pattern exists anywhere in `backend/`. `revision` is exercised only in unit tests confirming it increments — never checked against a caller-supplied expected value anywhere. Introducing an `If-Match`/expected-revision check for this cycle would be establishing a brand-new pattern from scratch. Multi-user collaborative editing was noted as a future goal in the prior cycle's exploration but nothing concurrency-related has been built toward it yet.

## App Placement Tension (flagged, not resolved)

- `apps/uml_commands` was deliberately kept Django-import-free (except `apps.py`) with an explicit AST boundary test protecting `commands.py`/`dispatcher.py`/`handlers/*.py` specifically. Adding `models.py`+`api.py` directly into `uml_commands` would not be caught by that test's literal file scope but would contradict its own module docstring's stated architectural intent.
- User's standing global preference: one Django app per domain, never mixing domains in one app (confirmed via `django-app-per-domain-preference` memory, and reinforced by this project's existing pattern of `uml_modeling` → `uml_commands` as siblings).
- Two live options, not resolved here: (1) extend `apps/uml_commands` in place with `models.py`/`api.py`, accepting the docstring/intent drift; (2) introduce a third sibling app (e.g. `apps/uml_documents` or `apps/diagrams`) that imports both `apps.uml_modeling` and `apps.uml_commands`, keeping `uml_commands` exactly as documented. Option 2 matches the established one-app-per-domain convention more cleanly but is a materially bigger cycle (new app registration, own migrations dir, new `INSTALLED_APPS` entry, its own import-boundary decision).

## Frontend Scope Confirmation

- Re-checked `frontend/src/` for `canvas|diagram|editor|uml` (case-insensitive) — all hits are false positives (role-label copy, landing-page marketing copy, member-management UI). **Confirmed: zero diagram/canvas UI exists.** This cycle is purely backend (persistence model + API); no frontend consumer needs to change.

## Open Questions for the User

1. **App placement**: extend `apps/uml_commands` with `models.py`/`api.py`, or add a third sibling app (e.g. `apps/uml_documents`) that depends on both `uml_modeling` and `uml_commands`?
2. **API shape**: one generic command-submission endpoint (new discriminated-union schema pattern, first in this codebase) vs. seven explicit per-command endpoints (matches existing router style, more boilerplate)?
3. **Concurrency**: build optimistic-concurrency (`If-Match`/expected-revision check) now as part of this cycle, or defer it — given the codebase has zero precedent for this and collaborative editing is not yet started?
4. **Serialization**: this cycle must build a brand-new dataclass↔JSON codec for `CanonicalUmlModel`/`DiagramLayout` from scratch (no existing helper to extend) — confirm this is in scope, not assumed trivial.
5. **owner_id population**: how does `request.user` become `ProjectDocument.owner_id` (e.g. `str(request.user.id)`)? No existing code answers this.
