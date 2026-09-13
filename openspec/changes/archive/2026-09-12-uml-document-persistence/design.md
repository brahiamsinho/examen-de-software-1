# Design: UML Document Persistence + API

## Technical Approach

New sibling Django app `backend/apps/uml_documents/`, depending one-directionally on
`apps.uml_modeling`, `apps.uml_commands`, and `apps.organizations` (never the reverse),
mirroring the `Membership`/`TenantScopedModel` pattern from `apps/organizations` exactly.
Unlike `uml_commands` (deliberately pure/Django-free), `uml_documents` is a real
persisted, tenant-scoped Django app — structurally the same kind of app as
`apps/organizations` itself — so depending on `apps.organizations` for
`TenantScopedModel`/`TenantScopedManager`/`resolve_membership`/`require_role`/`Role` is
correct, not a boundary violation; `apps.users` stays excluded since the caller's
identity reaches this app only as Django's built-in `request.user`. `UmlDocument`
persists a `ProjectDocument` split into real columns (`id`, `owner_id`, `revision`,
timestamps — queryable, denormalized) plus one `data: JSONField` blob holding only the
codec-serialized `metadata`/`model`/`layout` content. A new `codec.py` converts that
content triple to/from JSON; `services.py` assembles/disassembles the full
`ProjectDocument` from row + blob and is the only caller of
`apps.uml_commands.dispatcher.apply`; `api.py` exposes exactly the 3 endpoints from the
proposal, mirroring `organizations/api.py`'s thin-handler style
(`resolve_membership` → `require_role` → one service call → serialize). `apps/uml_modeling/`
and `apps/uml_commands/` receive zero changes — confirmed achievable (see below).

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|---|---|---|
| DD1 | New sibling app `uml_documents`, not an extension of `uml_commands` | Add `models.py`/`api.py` directly into `uml_commands` | Preserves `uml_commands`' own docstring ("no `models.py`: pure, DB-free command dispatch layer") and the codebase's one-app-per-domain convention; `uml_commands`' import-boundary test stays meaningful |
| DD2 | One generic `POST .../commands` endpoint, payload typed `Body[CommandIn]` where `CommandIn` is a `Field(discriminator="type")` `Union` of 7 sub-schemas | 7 explicit per-command endpoints | Matches proposal's confirmed decision; mirrors the closed `UmlCommand` union directly. `Body[...]` mirrors this codebase's existing `Path[str]` param-source-marker convention (`organizations/api.py`), since django-ninja does not auto-detect a bare `Union` type as a body param the way it does a `Schema` subclass |
| DD3 | `UmlDocument`: real columns for `id`/`owner_id`/`revision`/`created_at`/`updated_at`; `data: JSONField` holds only `metadata`+`model`+`layout` | Store the whole encoded `ProjectDocument` (incl. id/owner_id/revision) inside `data`, columns as pure cache | Avoids the same scalar values ever disagreeing between column and blob; `revision` is a real column now (not read/compared against a client value this cycle) specifically so a future optimistic-concurrency cycle needs no migration, per proposal's stated reason |
| DD4 | `created_at`/`updated_at` are plain `DateTimeField`, set explicitly by `services.py` from an injected `now` | `auto_now_add=True`/`auto_now=True` | The project's own clock-injection convention (`ProjectDocument.with_model(..., *, now)`, `dispatcher.apply(..., *, now)`) must reach the DB row too, or the row's timestamps would silently diverge from the document's; `Organization`/`Membership` use `auto_now(_add)` because those domains never inject a clock |
| DD5 | `codec.to_json(metadata, model, layout) -> dict` / `codec.from_json(data: dict) -> tuple[ProjectMetadata, CanonicalUmlModel, DiagramLayout]` — operates on the content triple, not the whole `ProjectDocument` | `to_json(document: ProjectDocument) -> dict` | Matches DD3: the blob never carries id/owner_id/revision, so the codec's contract shouldn't accept or return them either; `services.py` is the sole place that reassembles a full `ProjectDocument` from row columns + decoded triple |
| DD6 | `ElementId`-keyed mappings (`generation_metadata`, `positions`) encode as plain JSON objects with no key transform | Explicit `str(k)` stringify step | `ElementId = NewType("ElementId", str)` has zero runtime wrapper — it already *is* a `str`, so `json.dumps({elem_id: ...})` needs no conversion. Decode re-wraps each key via `ElementId(k)` purely for static typing (no-op at runtime). `generation_metadata`'s nested `Mapping[str, object]` values are trusted to already be JSON-safe primitives (`str`/`int`/`float`/`bool`/`None`/list/dict of those) — the codec does not attempt to serialize arbitrary Python objects; this is an explicit, documented constraint, not a gap |
| DD7 | `AttributeType` (`PrimitiveType \| EnumerationRef`) encodes as a plain string for `PrimitiveType` (its own `StrEnum` value) or a tagged object `{"enumeration_ref": {"enumeration_id": "..."}}` for `EnumerationRef` | A `{"kind": "primitive"/"enumeration_ref", ...}` explicit-tag envelope on both branches | `str` vs. `dict` is already an unambiguous structural discriminator in JSON — no extra tag field needed on the primitive branch; decode dispatches on `isinstance(value, str)` |
| DD8 | Schema→domain conversion (`CommandIn` payload → concrete `UmlCommand` dataclass) lives in `services.command_from_payload`, not in `api.py` or `schemas.py` | Method on each sub-schema (`payload.to_command()`); inline conversion in the view function | Keeps `api.py` handlers thin (parse → resolve membership → check role → one service call) exactly like `organizations/api.py`; keeps `schemas.py` pure data shapes with no domain-object construction, matching `organizations/schemas.py`'s convention of zero methods |
| DD9 | `POST /documents` and `POST .../commands` require `Role.OWNER`/`Role.EDITOR`; `GET` requires no `require_role` call (any member) | Require a role check on `GET` too | Matches proposal's confirmed working assumption and the existing `require_role(membership, *allowed)` variadic-role pattern already used for membership mutations |

## Data Flow

    Client
      │ POST /orgs/{slug}/documents/{id}/commands  {type, payload}
      ▼
    api.py: submit_command_view
      │ resolve_membership(request, org_slug) → membership
      │ require_role(membership, Role.OWNER, Role.EDITOR)
      │ command = services.command_from_payload(payload)
      ▼
    services.submit_command(organization, doc_id, command, now=now)
      │ row = UmlDocument.objects.for_organization(organization).get(id=doc_id)
      │ document = row → codec.from_json(row.data) → ProjectDocument
      ▼
    uml_commands.dispatcher.apply(document, command, now=now)   ← unchanged, zero diff
      │ CommandResult(document, validation_result)   — always returned, never gated
      ▼
    services._save(row, result.document)   ── codec.to_json(...) → row.data; row.revision/timestamps updated
      ▼
    api.py → CommandResultOut(revision, validation)

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/apps/uml_documents/__init__.py` | Create | Empty |
| `backend/apps/uml_documents/apps.py` | Create | `UmlDocumentsConfig(AppConfig)`, `name="apps.uml_documents"`, `label="uml_documents"` |
| `backend/apps/uml_documents/models.py` | Create | `UmlDocument(TenantScopedModel)` |
| `backend/apps/uml_documents/codec.py` | Create | `to_json`/`from_json` + private per-element encode/decode helpers |
| `backend/apps/uml_documents/services.py` | Create | `create_document`, `get_document`, `submit_command`, `command_from_payload` |
| `backend/apps/uml_documents/schemas.py` | Create | `DocumentCreateIn`, `DocumentOut`, `CommandIn` union + 7 sub-schemas, `CommandResultOut` |
| `backend/apps/uml_documents/api.py` | Create | `documents_router`, 3 handlers |
| `backend/apps/uml_documents/migrations/0001_initial.py` | Create | `makemigrations`-generated `CreateModel(UmlDocument)`, depends on `organizations`' latest migration |
| `backend/apps/uml_documents/tests/**` | Create | One test module per unit + `test_apps.py` + `test_import_boundary.py` (mirrors `uml_commands`) |
| `backend/config/settings.py` | Modify | Add `"apps.uml_documents"` to `INSTALLED_APPS` |
| `backend/config/api.py` | Modify | `api.add_router("/orgs/{org_slug}/documents", documents_router, tags=["documents"])` |
| `backend/apps/uml_modeling/**` | **None** | Zero diff — confirmed |
| `backend/apps/uml_commands/**` | **None** | Zero diff — confirmed |

## Interfaces / Contracts

```python
# models.py
class UmlDocument(TenantScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.CharField(max_length=255)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    data = models.JSONField(default=dict)   # {"metadata": {...}, "model": {...}, "layout": {...}}

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        indexes = [models.Index(fields=["organization", "owner_id"])]

# codec.py
def to_json(metadata: ProjectMetadata, model: CanonicalUmlModel, layout: DiagramLayout) -> dict: ...
def from_json(data: dict) -> tuple[ProjectMetadata, CanonicalUmlModel, DiagramLayout]: ...

def _encode_model(model: CanonicalUmlModel) -> dict:
    return {
        "classes": [_encode_class(c) for c in model.classes],
        "enumerations": [_encode_enumeration(e) for e in model.enumerations],
        "relationships": [_encode_relationship(r) for r in model.relationships],
        "generation_metadata": {k: v for k, v in model.generation_metadata.items()},
    }

def _decode_model(data: dict) -> CanonicalUmlModel:
    return CanonicalUmlModel(
        classes=tuple(_decode_class(c) for c in data["classes"]),
        enumerations=tuple(_decode_enumeration(e) for e in data["enumerations"]),
        relationships=tuple(_decode_relationship(r) for r in data["relationships"]),
        generation_metadata={ElementId(k): v for k, v in data["generation_metadata"].items()},
    )

def _encode_layout(layout: DiagramLayout) -> dict:
    return {"positions": {k: {"x": p.x, "y": p.y} for k, p in layout.positions.items()}}

def _decode_layout(data: dict) -> DiagramLayout:
    return DiagramLayout(
        positions={ElementId(k): Position(x=v["x"], y=v["y"]) for k, v in data["positions"].items()}
    )

def _encode_attribute_type(value: AttributeType) -> str | dict:
    if isinstance(value, EnumerationRef):
        return {"enumeration_ref": {"enumeration_id": str(value.enumeration_id)}}
    return value.value  # PrimitiveType is a StrEnum

def _decode_attribute_type(value: str | dict) -> AttributeType:
    if isinstance(value, str):
        return PrimitiveType(value)
    return EnumerationRef(enumeration_id=ElementId(value["enumeration_ref"]["enumeration_id"]))

# schemas.py
from typing import Annotated, Literal, Union
from pydantic import Field
from ninja import Schema

class AddClassIn(Schema):
    type: Literal["AddClass"]
    class_id: str
    name: str

class RemoveClassIn(Schema):
    type: Literal["RemoveClass"]
    class_id: str

class RenameClassIn(Schema):
    type: Literal["RenameClass"]
    class_id: str
    new_name: str

class UmlAttributeIn(Schema):
    id: str
    name: str
    type: str | dict   # decoded the same way as codec._decode_attribute_type
    visibility: Literal["public", "private", "protected", "package"] = "private"

class AddAttributeIn(Schema):
    type: Literal["AddAttribute"]
    class_id: str
    attribute: UmlAttributeIn

class RemoveAttributeIn(Schema):
    type: Literal["RemoveAttribute"]
    class_id: str
    attribute_id: str

class RelationshipEndIn(Schema):
    class_id: str
    multiplicity: str   # e.g. "0..1", "1..*" — parsed via domain.types.parse_multiplicity
    role: str | None = None

class RelationshipIn(Schema):
    id: str
    kind: Literal["association", "aggregation", "composition", "generalization"]
    source: RelationshipEndIn
    target: RelationshipEndIn
    name: str | None = None

class AddRelationshipIn(Schema):
    type: Literal["AddRelationship"]
    relationship: RelationshipIn

class RemoveRelationshipIn(Schema):
    type: Literal["RemoveRelationship"]
    relationship_id: str

CommandIn = Annotated[
    Union[
        AddClassIn, RemoveClassIn, RenameClassIn,
        AddAttributeIn, RemoveAttributeIn,
        AddRelationshipIn, RemoveRelationshipIn,
    ],
    Field(discriminator="type"),
]

class DocumentCreateIn(Schema):
    name: str

class MetadataOut(Schema):
    name: str
    description: str

class DocumentOut(Schema):
    id: UUID
    owner_id: str
    revision: int
    metadata: MetadataOut
    model: dict          # raw codec._encode_model(...) output — no duplicated Pydantic shape
    layout: dict          # raw codec._encode_layout(...) output
    created_at: datetime
    updated_at: datetime

class DiagnosticOut(Schema):
    severity: str
    code: str
    message: str
    path: str

class ValidationOut(Schema):
    is_valid: bool
    violations: list[DiagnosticOut]

class CommandResultOut(Schema):
    revision: int
    validation: ValidationOut

# api.py
documents_router = Router(auth=django_auth)

@documents_router.post("", response={201: DocumentOut})
def create_document_view(request, org_slug: Path[str], payload: DocumentCreateIn):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    document = services.create_document(
        organization=membership.organization, owner_id=str(request.user.id),
        name=payload.name, now=timezone.now(),
    )
    return Status(201, _document_out(document))

@documents_router.get("/{doc_id}", response=DocumentOut)
def get_document_view(request, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    return _document_out(document)

@documents_router.post("/{doc_id}/commands", response=CommandResultOut)
def submit_command_view(request, org_slug: Path[str], doc_id: UUID, payload: Body[CommandIn]):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    command = services.command_from_payload(payload)
    result = services.submit_command(
        organization=membership.organization, doc_id=doc_id, command=command, now=timezone.now(),
    )
    return {
        "revision": result.document.revision,
        "validation": {
            "is_valid": not result.validation_result.is_blocking,
            "violations": [
                {"severity": d.severity, "code": d.code, "message": d.message, "path": d.path}
                for d in result.validation_result.diagnostics
            ],
        },
    }
```

`services.get_document`/`submit_command` raise `Http404` (caught around
`UmlDocument.DoesNotExist`, same pattern as `resolve_membership`) whenever
`for_organization(organization).get(id=doc_id)` misses — the only lookup path used;
`UmlDocument.objects` (unscoped default manager) is never called directly, matching
`TenantScopedManager.get_queryset()`'s own enforcement.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit — codec | Round-trip a non-trivial `CanonicalUmlModel`/`DiagramLayout` fixture (multi-class, `generation_metadata`, `positions`) through `to_json`→`from_json`; both `AttributeType` branches; empty mappings | Plain `pytest`, equality assertions against `uml_modeling`-style factories |
| Unit — services | `create_document` initial state; `command_from_payload` for all 7 types; `submit_command` revision increment + persists invalid result unconditionally | Django test DB, `apps.organizations.tests.factories`-style org/user fixtures |
| Structural | App registers; import boundary (`codec.py`/`services.py`/`models.py`/`schemas.py` import only `apps.uml_modeling`, `apps.uml_commands`, `apps.organizations`, stdlib, Django/ninja/pydantic — never `apps.users`; `api.py` is excluded from the scoped file set the same way `uml_commands`' own test excludes `apps.py`, since its `resolve_membership`/`require_role`/`Role` imports are the same `apps.organizations` dependency already allowed for `models.py`, not a separate concern) | AST-based, mirrors `uml_commands/tests/test_import_boundary.py` |
| Integration | Full HTTP round trip per scenario: create → 2 sequential commands → get; viewer denied create/commands; cross-tenant 404 | `django.test.Client` / ninja test client against a real `documents_router` |
| E2E | N/A this cycle (no frontend consumer) | — |

## Threat Matrix

N/A — no routing/shell/subprocess/VCS automation, executable-file classification, or
process-integration boundary. This is a standard REST API + ORM layer, no shell/process
surface introduced.

## Migration / Rollout

One new Django migration (`0001_initial.py`, standard `CreateModel`). Rollback: delete
`backend/apps/uml_documents/`, the `INSTALLED_APPS` line, and the router-mount line — no
other app is touched, matching the proposal's rollback plan.

## Scenario Coverage Check (against the 10 scenarios)

1. **Editor creates empty document** — `create_document` builds `ProjectDocument` with
   empty `CanonicalUmlModel()`/`DiagramLayout()`, `owner_id=str(request.user.id)`,
   `revision=1` (dataclass default).
2. **Viewer denied creation** — `require_role` raises `RoleNotAllowedError` before any
   service call; already mapped to 403 by `organizations/api.py`'s globally-registered
   exception handler (no re-registration needed — handlers are attached to the shared
   `api` instance).
3. **Any member reads back** — `get_document_view` calls `resolve_membership` only, no
   `require_role`.
4. **Cross-tenant read 404** — `for_organization(organization)` scoping + `Http404` on miss.
5. **Sequential commands persist** — each call reloads the row fresh; `dispatcher.apply`'s
   existing `revision + 1` (via `with_model`) is untouched.
6. **Viewer denied command submission** — `require_role` raises before `command_from_payload`
   or any row access; document unmodified.
7. **Invalid result still persists** — `submit_command` never inspects
   `validation_result.is_blocking` before saving; dispatcher's Always-Apply Diagnostics
   Policy is reused unchanged.
8. **Codec round-trip** — DD5/DD6/DD7 above; dedicated fixture test.
9. **Tenant scoping on every access** — all 3 handlers call `resolve_membership` first;
   `services.py` only ever calls `.for_organization(...)`, never the raising default
   manager or `all_objects` directly.
10. **Import boundary + zero diff** — DD1 + AST test; `apps/uml_modeling`/`apps/uml_commands`
    file sets are provably untouched (new files only added under `apps/uml_documents/`).

No scenario forced a design choice beyond DD1–DD9 above. Scenario 7 is the one place the
design had to be explicit that persistence is **never** gated on validation outcome — this
follows directly from reusing `dispatcher.apply`'s existing contract, not a new mechanism.

## Open Questions

- [ ] `DiagnosticOut` omits `element_ref` (only `severity`/`code`/`message`/`path`) — none
  of the 10 scenarios require it in the response; flagged in case `sdd-verify` disagrees.
- [ ] `UmlAttributeIn.type`/`AddClassIn`-family fields use bare `str | dict` rather than a
  fully-typed nested Pydantic union for `AttributeType`, to avoid a second discriminated
  union this early; acceptable since `services.command_from_payload` is the single place
  that validates/converts it into the real domain type, and a malformed shape surfaces as
  a `KeyError`/`ValueError` there — no explicit 422 contract is defined for this inner
  shape (spec's discriminator requirement targets only the outer `{type, payload}` shape).

> Size note: exceeds the skill's 800-word soft budget for the same reason the prior
> `uml-command-bus` cycle's design did — the task explicitly required field-level
> dataclass/schema detail sufficient for `sdd-tasks` to slice implementable units without
> re-deriving them from the domain source.
