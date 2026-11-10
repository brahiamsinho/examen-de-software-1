"""Service layer for the uml_documents domain (design.md's Data Flow).

The only caller of `apps.uml_commands.dispatcher.apply` and the only
place that reassembles a full `ProjectDocument` from a `UmlDocument` row
+ decoded `codec` triple (DD5). Every lookup goes through
`UmlDocument.objects.for_organization(organization)` — never through the
raising default manager or `all_objects` directly (Tenant Scoping on
Every Access).
"""
import dataclasses
import datetime
import copy
import uuid
from uuid import UUID

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError
from django_mongodb_backend import transaction

from config.transactions import atomic_retrying
from django.http import Http404

from apps.uml_documents.signals import document_changed
from apps.organizations.models import Organization
from apps.uml_commands import commands
from apps.uml_commands.commands import UmlCommand
from apps.session_log import services as session_log
from apps.relational_mapping.mapping.profile_parser import (
    InvalidGenerationProfileError,
    parse_column_profile,
    parse_table_profile,
)
from apps.uml_commands.dispatcher import CommandResult, apply
from apps.uml_documents import codec, schemas
from apps.uml_documents.errors import InvalidCommandPayloadError
from apps.uml_documents.models import UmlDocument, UmlTemplate, UmlVersion
from apps.uml_modeling.documents import DiagramLayout, Position, ProjectDocument, ProjectMetadata
from apps.uml_modeling.domain.elements import (
    Relationship,
    RelationshipEnd,
    RelationshipKind,
    UmlAttribute,
    UmlClass,
    UmlOperation,
    Visibility,
)
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity, parse_multiplicity


def _to_project_document(row: UmlDocument) -> ProjectDocument:
    metadata, model, layout = codec.from_json(row.data)
    return ProjectDocument(
        id=row.id,
        metadata=metadata,
        owner_id=row.owner_id,
        model=model,
        layout=layout,
        created_at=row.created_at,
        updated_at=row.updated_at,
        revision=row.revision,
    )


def _save(row: UmlDocument, document: ProjectDocument) -> None:
    row.revision = document.revision
    row.updated_at = document.updated_at
    row.data = codec.to_json(document.metadata, document.model, document.layout)
    row.save()


def _get_row(*, organization: Organization, doc_id: UUID) -> UmlDocument:
    """The document row, scoped to the organization (404 otherwise). Writers that
    rewrite it (every command bumps `revision`) are serialised by MongoDB's
    write conflict detection plus `atomic_retrying`, not by a row lock.
    """
    qs = UmlDocument.objects.for_organization(organization)
    try:
        return qs.get(id=doc_id)
    except UmlDocument.DoesNotExist as exc:
        raise Http404("Document not found") from exc


def _get_version(*, organization: Organization, doc_id: UUID, version_id: UUID) -> UmlVersion:
    try:
        return UmlVersion.objects.for_organization(organization).get(document_id=doc_id, id=version_id)
    except UmlVersion.DoesNotExist as exc:
        raise Http404("Version not found") from exc


def _get_template(*, organization: Organization, template_id: UUID) -> UmlTemplate:
    try:
        return UmlTemplate.objects.for_organization(organization).get(id=template_id)
    except UmlTemplate.DoesNotExist as exc:
        raise Http404("Template not found") from exc


def template_preview(snapshot: dict) -> dict:
    """A thumbnail-sized description of a template for the catalogue.

    Carries only class names, attribute counts, coordinates and relationship
    endpoints, so listing templates never ships whole snapshots. Classes the
    author never positioned get a deterministic grid slot to remain drawable.
    """
    positions = snapshot.get("layout", {}).get("positions", {})
    classes = []
    for index, uml_class in enumerate(snapshot["model"]["classes"]):
        position = positions.get(uml_class["id"])
        x, y = (position["x"], position["y"]) if position else (index % 3 * 220, index // 3 * 160)
        classes.append(
            {
                "id": uml_class["id"],
                "name": uml_class["name"],
                "attributes": len(uml_class["attributes"]),
                "x": x,
                "y": y,
            }
        )
    relationships = [
        {"source": item["source"]["class_id"], "target": item["target"]["class_id"], "kind": item["kind"]}
        for item in snapshot["model"]["relationships"]
    ]
    return {"classes": classes, "relationships": relationships}


def list_templates(*, organization: Organization) -> list[UmlTemplate]:
    return list(UmlTemplate.objects.for_organization(organization).order_by("name", "id"))


def get_template(*, organization: Organization, template_id: UUID) -> UmlTemplate:
    return _get_template(organization=organization, template_id=template_id)


def create_template(
    *, organization: Organization, doc_id: UUID, created_by, name: str
) -> UmlTemplate:
    row = _get_row(organization=organization, doc_id=doc_id)
    return UmlTemplate.objects.for_organization(organization).create(
        organization=organization,
        name=name,
        source_document=row,
        snapshot=copy.deepcopy(row.data),
        created_by=created_by,
    )


def _clone_template_data(snapshot: dict, *, name: str) -> tuple[CanonicalUmlModel, DiagramLayout]:
    """Clone every persisted UML identifier before decoding the snapshot.

    References appear in element fields, JSON object keys and layout positions,
    so the rewrite is recursive rather than tied to one UI representation.
    """
    cloned = copy.deepcopy(snapshot)
    model = cloned["model"]
    old_ids = [
        *(item["id"] for item in model["classes"]),
        *(attribute["id"] for item in model["classes"] for attribute in item["attributes"]),
        *(operation["id"] for item in model["classes"] for operation in item["operations"]),
        *(item["id"] for item in model["enumerations"]),
        *(literal["id"] for item in model["enumerations"] for literal in item["literals"]),
        *(item["id"] for item in model["relationships"]),
    ]
    replacements = {old_id: str(uuid.uuid4()) for old_id in old_ids}

    def rewrite(value):
        if isinstance(value, str):
            return replacements.get(value, value)
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, dict):
            return {replacements.get(key, key): rewrite(item) for key, item in value.items()}
        return value

    cloned = rewrite(cloned)
    cloned["metadata"]["name"] = name
    _metadata, cloned_model, cloned_layout = codec.from_json(cloned)
    return cloned_model, cloned_layout


def instantiate_template(
    *, organization: Organization, template_id: UUID, owner_id: str, name: str, now: datetime.datetime
) -> ProjectDocument:
    template = _get_template(organization=organization, template_id=template_id)
    model, layout = _clone_template_data(template.snapshot, name=name)
    return create_document_from_model(
        organization=organization, owner_id=owner_id, name=name, model=model, layout=layout, now=now
    )


def list_versions(*, organization: Organization, doc_id: UUID) -> list[UmlVersion]:
    _get_row(organization=organization, doc_id=doc_id)
    return list(UmlVersion.objects.for_organization(organization).filter(document_id=doc_id).order_by("-number"))


def get_version(*, organization: Organization, doc_id: UUID, version_id: UUID) -> UmlVersion:
    _get_row(organization=organization, doc_id=doc_id)
    return _get_version(organization=organization, doc_id=doc_id, version_id=version_id)


def compare_versions(
    *, organization: Organization, doc_id: UUID, from_version_id: UUID, to_version_id: UUID
) -> dict:
    before = get_version(organization=organization, doc_id=doc_id, version_id=from_version_id)
    after = get_version(organization=organization, doc_id=doc_id, version_id=to_version_id)
    before_model = before.snapshot["model"]
    after_model = after.snapshot["model"]
    return {
        "from_version_id": before.id,
        "to_version_id": after.id,
        "classes": _diff_elements(
            [_class_summary(item) for item in before_model["classes"]],
            [_class_summary(item) for item in after_model["classes"]],
        ),
        "attributes": _diff_attributes(before_model["classes"], after_model["classes"]),
        "relationships": _diff_elements(
            before_model["relationships"], after_model["relationships"]
        ),
    }


def _diff_elements(before: list[dict], after: list[dict]) -> dict:
    before_by_id = {item["id"]: item for item in before}
    after_by_id = {item["id"]: item for item in after}
    return {
        "added": [
            _diff_label(after_by_id[item_id]) for item_id in sorted(after_by_id.keys() - before_by_id.keys())
        ],
        "removed": [
            _diff_label(before_by_id[item_id]) for item_id in sorted(before_by_id.keys() - after_by_id.keys())
        ],
        "modified": [
            {"before": _diff_label(before_by_id[item_id]), "after": _diff_label(after_by_id[item_id])}
            for item_id in sorted(before_by_id.keys() & after_by_id.keys())
            if before_by_id[item_id] != after_by_id[item_id]
        ],
    }


def _diff_attributes(before_classes: list[dict], after_classes: list[dict]) -> dict:
    def flatten(classes: list[dict]) -> list[dict]:
        return [
            {**attribute, "class_id": uml_class["id"], "class_name": uml_class["name"]}
            for uml_class in classes
            for attribute in uml_class["attributes"]
        ]

    return _diff_elements(flatten(before_classes), flatten(after_classes))


def _class_summary(item: dict) -> dict:
    return {key: item[key] for key in ("id", "name", "visibility") if key in item}


def _diff_label(item: dict) -> dict:
    return {key: item[key] for key in ("id", "name", "class_id", "class_name") if key in item}


@atomic_retrying(also_retry=(IntegrityError,))
def create_version(
    *, organization: Organization, doc_id: UUID, created_by, description: str, expected_revision: int
) -> UmlVersion:
    row = _get_row(organization=organization, doc_id=doc_id)
    if row.revision != expected_revision:
        raise ValueError("The diagram changed before this version could be saved. Reload and try again.")
    latest = (
        UmlVersion.objects.for_organization(organization)
        .filter(document_id=doc_id)
        .order_by("-number")
        .first()
    )
    return UmlVersion.objects.for_organization(organization).create(
        organization=organization,
        document=row,
        number=(latest.number if latest else 0) + 1,
        source_revision=row.revision,
        description=description,
        snapshot=row.data,
        created_by=created_by,
    )


@atomic_retrying
def restore_version(
    *,
    organization: Organization,
    doc_id: UUID,
    version_id: UUID,
    expected_revision: int,
    now: datetime.datetime,
    actor=None,
) -> ProjectDocument:
    row = _get_row(organization=organization, doc_id=doc_id)
    if row.revision != expected_revision:
        raise ValueError("The diagram changed before this version could be restored. Reload and try again.")
    version = _get_version(organization=organization, doc_id=doc_id, version_id=version_id)
    metadata, model, layout = codec.from_json(version.snapshot)
    restored = ProjectDocument(
        id=row.id,
        metadata=metadata,
        owner_id=row.owner_id,
        model=model,
        layout=layout,
        created_at=row.created_at,
        updated_at=now,
        revision=row.revision + 1,
    )
    _save(row, restored)
    session_log.record(
        organization=organization,
        document_id=doc_id,
        kind=session_log.LogKind.VERSION_RESTORED,
        summary=f"Restored version {version.number}",
        actor=actor,
        data={"version_id": str(version_id), "version_number": version.number, "revision": restored.revision},
        now=now,
    )
    transaction.on_commit(lambda: broadcast_document(document=restored))
    return restored


def broadcast_document(*, document: ProjectDocument) -> None:
    """Fans a `document.update` event out to every socket subscribed to
    this document's group (design.md DD2/DD3/DD6/DD7). Always called via
    `transaction.on_commit`, never inline, so a reader can always `SELECT`
    the revision being broadcast.

    `channel_layer.group_send` crosses channels_redis' msgpack transport in
    production — a boundary distinct from (and earlier than) the
    `json.dumps` the consumer's `send_json` sees. `codec.document_out`
    returns raw `UUID`/`datetime` values, so the payload is pre-serialized
    through `schemas.DocumentOut` here, before it ever reaches `group_send`,
    not just on the consumer's receiving side.
    """
    channel_layer = get_channel_layer()
    payload = schemas.DocumentOut.model_validate(codec.document_out(document)).model_dump(
        mode="json"
    )
    async_to_sync(channel_layer.group_send)(
        f"uml-doc-{document.id}",
        {"type": "document.update", "document": payload},
    )
    # Other apps (e.g. phone pushes) listen; this app does not know them.
    document_changed.send_robust(sender=type(document), document=document)


def broadcast_event(*, document_id: UUID, payload: dict) -> None:
    """Fans a JSON-safe, `type`-tagged event out to every socket subscribed
    to this document's group. Used by features (e.g. AI proposals) that
    share the document socket without owning it. Call via
    `transaction.on_commit` so readers never see an uncommitted state."""
    async_to_sync(get_channel_layer().group_send)(f"uml-doc-{document_id}", payload)


def create_document(
    *, organization: Organization, owner_id: str, name: str, now: datetime.datetime
) -> ProjectDocument:
    data = codec.to_json(ProjectMetadata(name=name), CanonicalUmlModel(), DiagramLayout())
    row = UmlDocument.objects.for_organization(organization).create(
        organization=organization,
        owner_id=owner_id,
        revision=1,
        created_at=now,
        updated_at=now,
        data=data,
    )
    return _to_project_document(row)


def create_document_from_model(
    *,
    organization: Organization,
    owner_id: str,
    name: str,
    model: CanonicalUmlModel,
    layout: DiagramLayout,
    now: datetime.datetime,
) -> ProjectDocument:
    """Like `create_document`, but seeded with a ready model (e.g. an XMI import)."""
    data = codec.to_json(ProjectMetadata(name=name), model, layout)
    row = UmlDocument.objects.for_organization(organization).create(
        organization=organization,
        owner_id=owner_id,
        revision=1,
        created_at=now,
        updated_at=now,
        data=data,
    )
    return _to_project_document(row)


@atomic_retrying
def replace_document_content(
    *,
    organization: Organization,
    doc_id: UUID,
    model: CanonicalUmlModel,
    layout: DiagramLayout,
    now: datetime.datetime,
    actor=None,
) -> ProjectDocument:
    """Loads a ready model (e.g. an XMI import) INTO an existing document,
    REPLACING whatever it currently has — used for the Modelia <-> Enterprise
    Architect round-trip workflow (edit in EA, re-import to bring the changes
    back). Deliberately unconditional: unlike a blank-only import, this
    intentionally overwrites existing content, so the caller (the frontend's
    confirmation prompt) is where accidental data loss must be guarded, not
    here.

    Serialized under the same row lock as `submit_command`, so a concurrent
    edit cannot race the replace. The name stays the one the user chose; the
    revision is bumped once and the result is broadcast on commit so other
    connected clients see the new content.
    """
    row = _get_row(organization=organization, doc_id=doc_id)
    document = _to_project_document(row)
    updated = dataclasses.replace(
        document, model=model, layout=layout, revision=document.revision + 1, updated_at=now
    )
    _save(row, updated)
    session_log.record(
        organization=organization,
        document_id=doc_id,
        kind=session_log.LogKind.DIAGRAM_REPLACED,
        summary="Replaced the diagram content with an import",
        actor=actor,
        data={"revision": updated.revision},
        now=now,
    )
    transaction.on_commit(lambda: broadcast_document(document=updated))
    return updated


def delete_document(*, organization: Organization, doc_id: UUID) -> None:
    """Hard-deletes the document. Rows that reference it (deployments) cascade."""
    row = _get_row(organization=organization, doc_id=doc_id)
    row.delete()


def get_document(*, organization: Organization, doc_id: UUID) -> ProjectDocument:
    row = _get_row(organization=organization, doc_id=doc_id)
    return _to_project_document(row)


def list_documents(*, organization: Organization) -> list[ProjectDocument]:
    """Newest-updated first — `UmlDocument.Meta` declares no `ordering`,
    so the order is stated here or it is undefined (design.md DD1).
    """
    rows = UmlDocument.objects.for_organization(organization).order_by("-updated_at")
    return [_to_project_document(row) for row in rows]


@atomic_retrying
def submit_command(
    *, organization: Organization, doc_id: UUID, command: UmlCommand, now: datetime.datetime, actor=None
) -> CommandResult:
    """Serialized under a per-document row lock (design.md DD1): the
    decorator opens the transaction (and runs it again if another writer
    wins the conflict, see `config/transactions.py`), matching
    `users/services.py:40`/`organizations/services.py:68` style. On
    success, the resulting document is broadcast to the document's group
    once the transaction actually commits (DD2) — never inline, which
    would publish a revision no reader can yet `SELECT`.
    """
    row = _get_row(organization=organization, doc_id=doc_id)
    document = _to_project_document(row)
    if isinstance(command, commands.SetGenerationProfile):
        _validate_generation_profile(document.model, command)
    if isinstance(command, commands.UpdateRelationship):
        _validate_relationship_update(document.model, command)
    result = apply(document, command, now=now)
    _save(row, result.document)
    session_log.record_change(
        organization=organization,
        document_id=doc_id,
        batch=[command],
        model_before=document.model,
        revision=result.document.revision,
        actor=actor,
        now=now,
    )
    transaction.on_commit(lambda: broadcast_document(document=result.document))
    return result


@atomic_retrying
def submit_commands(
    *,
    organization: Organization,
    doc_id: UUID,
    commands_to_apply: list[UmlCommand],
    now: datetime.datetime,
    expected_revision: int | None = None,
    actor=None,
) -> CommandResult:
    """Apply a prevalidated batch under one lock, save, revision and broadcast.

    Image-reconciliation confirmation uses this instead of `submit_command`
    per item so observers never see a partially reconciled diagram.

    `actor` is who made the change, for the session log; a change without a
    known author is still logged (as the system), never skipped.
    """
    row = _get_row(organization=organization, doc_id=doc_id)
    document = _to_project_document(row)
    model_before = document.model
    if expected_revision is not None and document.revision != expected_revision:
        raise ValueError("The diagram changed after this preview. Upload the image again.")
    result: CommandResult | None = None
    for command in commands_to_apply:
        if isinstance(command, commands.SetGenerationProfile):
            _validate_generation_profile(document.model, command)
        if isinstance(command, commands.UpdateRelationship):
            _validate_relationship_update(document.model, command)
        result = apply(document, command, now=now)
        document = result.document
    if result is None:
        raise ValueError("A command batch cannot be empty")
    _save(row, result.document)
    session_log.record_change(
        organization=organization,
        document_id=doc_id,
        batch=commands_to_apply,
        model_before=model_before,
        revision=result.document.revision,
        actor=actor,
        now=now,
    )
    transaction.on_commit(lambda: broadcast_document(document=result.document))
    return result


def _validate_relationship_update(
    model: CanonicalUmlModel, command: commands.UpdateRelationship
) -> None:
    """Write-time gate for `UpdateRelationship`; the handler itself stays structural (DD6)."""
    target = next((r for r in model.relationships if r.id == command.relationship_id), None)
    if target is None:
        raise InvalidCommandPayloadError(
            f"Unknown relationship id {command.relationship_id!r}: not a relationship of this document"
        )
    changes_multiplicity = (
        command.source_multiplicity is not None or command.target_multiplicity is not None
    )
    if changes_multiplicity and target.kind in (RelationshipKind.GENERALIZATION, RelationshipKind.DEPENDENCY):
        raise InvalidCommandPayloadError(
            f"Relationship {command.relationship_id!r} is a {target.kind.value} and has no multiplicities"
        )


def _attribute_owner(model: CanonicalUmlModel, element_id: ElementId) -> UmlClass | None:
    """The class holding the attribute with this id, if any."""
    for uml_class in model.classes:
        if any(attribute.id == element_id for attribute in uml_class.attributes):
            return uml_class
    return None


def _descendant_class_ids(model: CanonicalUmlModel, class_id: ElementId) -> frozenset[ElementId]:
    """Transitive descendants: GENERALIZATION `source` is the child, `target` the parent."""
    descendants: set[ElementId] = set()
    frontier = [class_id]
    while frontier:
        current = frontier.pop()
        for relationship in model.relationships:
            if (
                relationship.kind is RelationshipKind.GENERALIZATION
                and relationship.target.class_id == current
                and relationship.source.class_id not in descendants
            ):
                descendants.add(relationship.source.class_id)
                frontier.append(relationship.source.class_id)
    return frozenset(descendants)


def _is_inheritance_root(model: CanonicalUmlModel, class_id: ElementId) -> bool:
    return not any(
        relationship.kind is RelationshipKind.GENERALIZATION
        and relationship.source.class_id == class_id
        for relationship in model.relationships
    )


def _validate_generation_profile(
    model: CanonicalUmlModel, command: commands.SetGenerationProfile
) -> None:
    """Write-time gate for `SetGenerationProfile` (DD153-DD157). Runs inside
    `submit_command`'s row lock; the handler itself stays structural (DD6).
    """
    owner = _attribute_owner(model, command.element_id)
    target = model.class_by_id(command.element_id)
    if target is None and owner is None:
        raise InvalidCommandPayloadError(
            f"Unknown element id {command.element_id!r}: not a class or attribute of this document"
        )
    if not command.profile:
        return

    entry = {"profile": dict(command.profile)}
    try:
        if target is None:
            parse_column_profile(command.element_id, entry)
            return
        parsed = parse_table_profile(command.element_id, entry)
    except InvalidGenerationProfileError as exc:
        raise InvalidCommandPayloadError(str(exc)) from exc

    if parsed is None or parsed.default_sort is None:
        return
    allowed = {attribute.id for attribute in target.attributes}
    descendants = (
        _descendant_class_ids(model, target.id)
        if _is_inheritance_root(model, target.id)
        else frozenset()
    )
    for class_id in descendants:
        allowed |= {attribute.id for attribute in model.class_by_id(class_id).attributes}
    attribute_id = parsed.default_sort.attribute_id
    if attribute_id not in allowed:
        scope = "this class or its descendants" if descendants else "this class"
        raise InvalidCommandPayloadError(
            f"Invalid generation profile for element {command.element_id!r}, "
            f"key 'defaultSort.attribute': {attribute_id!r} is not an attribute of {scope}"
        )


@atomic_retrying
def save_layout_position(
    *,
    organization: Organization,
    doc_id: UUID,
    class_id: str,
    position: Position,
    now: datetime.datetime,
) -> ProjectDocument:
    """Sibling to `submit_command`, deliberately NOT routed through
    `dispatcher.apply()` or any `UmlCommand` variant (design.md DD8):
    ephemeral node claims never touch Postgres or `revision`, but a
    released drag's final position is durable, and this is that write.
    Uses the same `@atomic_retrying` + `_get_row` as `submit_command`, and
    both rewrite the document row, so the two write paths can never race
    each other on the same document.

    A `class_id` absent from the document's current model (removed by a
    `RemoveClass` mid-drag) returns the document UNCHANGED — no write, no
    `revision` bump (DD8's `RemoveClass` case). Every persisted entry
    whose class id is no longer live is pruned on every successful call,
    which is self-healing and needs no migration.
    """
    row = _get_row(organization=organization, doc_id=doc_id)
    document = _to_project_document(row)
    live = {c.id for c in document.model.classes}
    target = ElementId(class_id)
    if target not in live:
        return document
    positions = {cid: p for cid, p in document.layout.positions.items() if cid in live}
    positions[target] = position
    updated = document.with_layout(DiagramLayout(positions=positions), now=now)
    _save(row, updated)
    transaction.on_commit(lambda: broadcast_document(document=updated))
    return updated


def command_from_payload(payload: "schemas.CommandIn") -> UmlCommand:
    """Convert a validated `CommandIn` payload into a real `UmlCommand`.

    The outer `{type, ...}` envelope is already validated by pydantic's
    discriminated union before this runs. The inner shapes this function
    decodes (`attribute.type`, a relationship end's `multiplicity`) are
    loosely typed (`str | dict`) and validated here by hand — any
    `KeyError`/`ValueError`/`TypeError` from a malformed inner shape is
    normalized to `InvalidCommandPayloadError`, mapped to a 422 by
    `api.py`'s exception handler, so a bad client payload never surfaces
    as an unhandled 500.
    """
    try:
        return _command_from_payload(payload)
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidCommandPayloadError(f"Malformed command payload: {exc}") from exc


def _command_from_payload(payload: "schemas.CommandIn") -> UmlCommand:
    if isinstance(payload, schemas.AddClassIn):
        return commands.AddClass(class_id=ElementId(payload.class_id), name=payload.name)
    if isinstance(payload, schemas.RemoveClassIn):
        return commands.RemoveClass(class_id=ElementId(payload.class_id))
    if isinstance(payload, schemas.RenameClassIn):
        return commands.RenameClass(class_id=ElementId(payload.class_id), new_name=payload.new_name)
    if isinstance(payload, schemas.SetClassAbstractIn):
        return commands.SetClassAbstract(class_id=ElementId(payload.class_id), is_abstract=payload.is_abstract)
    if isinstance(payload, schemas.AddAttributeIn):
        return commands.AddAttribute(
            class_id=ElementId(payload.class_id),
            attribute=_attribute_from_schema(payload.attribute),
        )
    if isinstance(payload, schemas.RemoveAttributeIn):
        return commands.RemoveAttribute(
            class_id=ElementId(payload.class_id), attribute_id=ElementId(payload.attribute_id)
        )
    if isinstance(payload, schemas.AddOperationIn):
        return commands.AddOperation(
            class_id=ElementId(payload.class_id),
            operation=_operation_from_schema(payload.operation),
        )
    if isinstance(payload, schemas.RemoveOperationIn):
        return commands.RemoveOperation(
            class_id=ElementId(payload.class_id), operation_id=ElementId(payload.operation_id)
        )
    if isinstance(payload, schemas.AddRelationshipIn):
        return commands.AddRelationship(relationship=_relationship_from_schema(payload.relationship))
    if isinstance(payload, schemas.RemoveRelationshipIn):
        return commands.RemoveRelationship(relationship_id=ElementId(payload.relationship_id))
    if isinstance(payload, schemas.UpdateRelationshipIn):
        return commands.UpdateRelationship(
            relationship_id=ElementId(payload.relationship_id),
            # Distinguish "omitted" (leave as is) from an explicit null/blank (clear).
            name=payload.name if "name" in payload.model_fields_set else commands.UNSET,
            source_multiplicity=_optional_multiplicity(payload.source_multiplicity),
            target_multiplicity=_optional_multiplicity(payload.target_multiplicity),
        )
    if isinstance(payload, schemas.SetGenerationProfileIn):
        return commands.SetGenerationProfile(
            element_id=ElementId(payload.element_id), profile=payload.profile
        )
    raise ValueError(f"Unknown command payload type: {payload!r}")


def _optional_multiplicity(text: str | None) -> Multiplicity | None:
    return parse_multiplicity(text) if text is not None else None


def _attribute_from_schema(attribute_in: "schemas.UmlAttributeIn") -> UmlAttribute:
    return UmlAttribute(
        id=ElementId(attribute_in.id),
        name=attribute_in.name,
        type=codec._decode_attribute_type(attribute_in.type),
        visibility=Visibility(attribute_in.visibility),
    )


def _operation_from_schema(operation_in: "schemas.UmlOperationIn") -> UmlOperation:
    return UmlOperation(
        id=ElementId(operation_in.id),
        name=operation_in.name,
        return_type=codec._decode_attribute_type(operation_in.return_type)
        if operation_in.return_type is not None
        else None,
        parameters=(),
        visibility=Visibility(operation_in.visibility),
    )


def _relationship_from_schema(relationship_in: "schemas.RelationshipIn") -> Relationship:
    return Relationship(
        id=ElementId(relationship_in.id),
        kind=RelationshipKind(relationship_in.kind),
        source=_relationship_end_from_schema(relationship_in.source),
        target=_relationship_end_from_schema(relationship_in.target),
        name=relationship_in.name,
    )


def _relationship_end_from_schema(end_in: "schemas.RelationshipEndIn") -> RelationshipEnd:
    return RelationshipEnd(
        class_id=ElementId(end_in.class_id),
        multiplicity=parse_multiplicity(end_in.multiplicity),
        role=end_in.role,
    )
