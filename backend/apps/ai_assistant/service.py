"""Orchestration for one voice utterance: transcript -> Gemini (function
calling) -> per-command translate + submit through the EXISTING
`uml_documents.services` pipeline -> a response listing what was applied.

Partial-failure policy: each translated command is submitted
independently, in the order Gemini returned them. A failure at command N
(an unresolvable class name, a malformed inner shape, an unknown
relationship, ...) is caught, reported, and does NOT roll back commands
1..N-1 and does NOT block N+1..end. This mirrors how a human applying the
same utterance by hand, one command at a time, would naturally proceed:
they would not undo an already-created class just because a later step
failed, and they would keep going with whatever they could still do. The
alternative (all-or-nothing, wrapping the whole batch in one transaction)
would mean one misheard word discards an otherwise-correct multi-command
utterance entirely — worse for a voice interface, where re-speaking the
whole sentence is more costly than fixing just the one part that failed.
"""
import dataclasses
import datetime
from collections.abc import Sequence
from uuid import UUID, uuid4

from django.core.cache import cache

from apps.ai_assistant import tools
from apps.ai_assistant.errors import TranslationError
from apps.ai_assistant.gemini_client import GeminiClientProtocol, GeminiFunctionCall
from apps.ai_assistant.llm_provider import get_active_llm_client
from apps.ai_assistant.translator import Translator
from apps.organizations.models import Organization
from apps.uml_documents import services
from apps.uml_documents.errors import InvalidCommandPayloadError
from apps.uml_modeling.documents import ProjectDocument

_SYSTEM_INSTRUCTION = (
    "You are a voice-driven assistant for a UML class diagram editor. The user "
    "speaks Spanish; translate what they ask for into the provided function "
    "calls, one call per distinct change. Only call the provided functions — "
    "never invent a class, attribute, operation, or relationship the user did "
    "not ask for. Always refer to classes, attributes, and operations by name, "
    "never by id. When the user describes several changes in one sentence, "
    "emit one function call per change, in the order they were spoken."
)

_IMAGE_SYSTEM_INSTRUCTION = (
    "You are a diagram-import assistant for a UML class diagram editor. The "
    "user uploaded an image of a UML class diagram — a screenshot, a photo of "
    "a whiteboard or hand-drawn sketch, or an export from another modeling "
    "tool. Return one complete extraction: every class, each visible attribute "
    "and operation, and every connector with its multiplicities. Inspect class "
    "boxes and relationship lines before responding. Never invent an element "
    "that is not actually visible. If part of the image is unclear, include all "
    "legible elements and omit only the unclear detail."
)


@dataclasses.dataclass(frozen=True)
class AppliedCommand:
    ok: bool
    message: str


@dataclasses.dataclass(frozen=True)
class VoiceCommandResult:
    revision: int
    applied: list[AppliedCommand]


@dataclasses.dataclass(frozen=True)
class ImageImportPreview:
    plan_id: str
    base_revision: int
    changes: list[AppliedCommand]


@dataclasses.dataclass(frozen=True)
class VoiceCommandPreview:
    plan_id: str
    base_revision: int
    changes: list[AppliedCommand]


@dataclasses.dataclass(frozen=True)
class _ImageImportPlan:
    document_id: UUID
    organization_id: UUID
    base_revision: int
    calls: tuple[GeminiFunctionCall, ...]
    changes: tuple[AppliedCommand, ...]


@dataclasses.dataclass(frozen=True)
class _VoiceCommandPlan:
    document_id: UUID
    organization_id: UUID
    base_revision: int
    calls: tuple[GeminiFunctionCall, ...]
    changes: tuple[AppliedCommand, ...]


_IMAGE_PLAN_TTL_SECONDS = 15 * 60
_VOICE_PLAN_TTL_SECONDS = 15 * 60


def _document_context(document: ProjectDocument) -> str:
    """A compact natural-language description of the current diagram:
    plain text, not the raw `CanonicalUmlModel` — Gemini reasons over
    prose, not dataclasses."""
    if not document.model.classes:
        return "The diagram is currently empty: it has no classes."
    lines = ["Current diagram classes:"]
    for uml_class in document.model.classes:
        attributes = ", ".join(f"{a.name}: {a.type}" for a in uml_class.attributes) or "none"
        operations = ", ".join(o.name for o in uml_class.operations) or "none"
        lines.append(f"- {uml_class.name} (attributes: {attributes}; operations: {operations})")
    if document.model.relationships:
        lines.append("Current relationships:")
        for relationship in document.model.relationships:
            source = document.model.class_by_id(relationship.source.class_id)
            target = document.model.class_by_id(relationship.target.class_id)
            source_name = source.name if source is not None else relationship.source.class_id
            target_name = target.name if target is not None else relationship.target.class_id
            lines.append(f"- {relationship.kind.value}: {source_name} -> {target_name}")
    return "\n".join(lines)


def apply_voice_command(
    *,
    organization: Organization,
    doc_id: UUID,
    transcript: str,
    now: datetime.datetime,
    gemini: GeminiClientProtocol | None = None,
) -> VoiceCommandResult:
    """Raises `MissingApiKeyError`/`GeminiRequestError` (whole-request
    failures, nothing has been attempted yet) and `Http404` (unknown/foreign
    document, via `services.get_document`) — both caught by `api.py`'s
    exception handling. Per-command failures never raise past this
    function; they land in the returned `applied` list instead.
    """
    gemini = gemini or get_active_llm_client()
    document = services.get_document(organization=organization, doc_id=doc_id)

    calls = gemini.generate_function_calls(
        system_instruction=_SYSTEM_INSTRUCTION,
        transcript=f"{_document_context(document)}\n\nUser said: {transcript}",
        tools=tools.TOOLS,
    )

    return _apply_translated_commands(
        organization=organization, doc_id=doc_id, document=document, calls=calls, now=now
    )


def preview_voice_command(
    *,
    organization: Organization,
    doc_id: UUID,
    transcript: str,
    gemini: GeminiClientProtocol | None = None,
) -> VoiceCommandPreview:
    """Interpret speech into an expiring, non-persisted edit plan."""
    gemini = gemini or get_active_llm_client()
    document = services.get_document(organization=organization, doc_id=doc_id)
    calls = gemini.generate_function_calls(
        system_instruction=_SYSTEM_INSTRUCTION,
        transcript=f"{_document_context(document)}\n\nUser said: {transcript}",
        tools=tools.TOOLS,
    )
    changes = tuple(_describe_calls(document, calls))
    plan_id = uuid4().hex
    cache.set(
        _voice_plan_key(plan_id),
        _VoiceCommandPlan(
            document_id=doc_id,
            organization_id=organization.id,
            base_revision=document.revision,
            calls=tuple(calls),
            changes=changes,
        ),
        timeout=_VOICE_PLAN_TTL_SECONDS,
    )
    return VoiceCommandPreview(plan_id=plan_id, base_revision=document.revision, changes=list(changes))


def confirm_voice_command(
    *, organization: Organization, doc_id: UUID, plan_id: str, now: datetime.datetime
) -> VoiceCommandResult:
    plan = cache.get(_voice_plan_key(plan_id))
    if not isinstance(plan, _VoiceCommandPlan) or plan.document_id != doc_id or plan.organization_id != organization.id:
        raise ValueError("This voice preview has expired. Speak the command again.")
    document = services.get_document(organization=organization, doc_id=doc_id)
    if document.revision != plan.base_revision:
        raise ValueError("The diagram changed after this preview. Speak the command again.")
    cache.delete(_voice_plan_key(plan_id))
    if not plan.calls:
        return VoiceCommandResult(revision=document.revision, applied=[])
    translator = Translator(document.model)
    translated = [translator.translate(call) for call in plan.calls]
    result = services.submit_commands(
        organization=organization,
        doc_id=doc_id,
        commands_to_apply=[services.command_from_payload(item.payload) for item in translated],
        now=now,
        expected_revision=plan.base_revision,
    )
    return VoiceCommandResult(
        revision=result.document.revision,
        applied=[AppliedCommand(ok=True, message=item.description) for item in translated],
    )


def apply_image_command(
    *,
    organization: Organization,
    doc_id: UUID,
    image_bytes: bytes,
    image_mime_type: str,
    now: datetime.datetime,
    gemini: GeminiClientProtocol | None = None,
) -> VoiceCommandResult:
    """Same shape and the same whole-request-vs-per-command failure split as
    `apply_voice_command` (see its docstring) — the only difference is the
    input modality: an uploaded image of a UML diagram instead of a spoken
    transcript. `_document_context(document)` is reused unchanged, so the
    model also knows what (if anything) already exists in the target
    document and can avoid duplicating it.
    """
    gemini = gemini or get_active_llm_client()
    document = services.get_document(organization=organization, doc_id=doc_id)

    calls = gemini.generate_function_calls_from_image(
        system_instruction=f"{_IMAGE_SYSTEM_INSTRUCTION}\n\n{_document_context(document)}",
        image_bytes=image_bytes,
        image_mime_type=image_mime_type,
        tools=tools.IMAGE_IMPORT_TOOLS,
    )

    calls = _expand_image_extraction(calls)

    return _apply_translated_commands(
        organization=organization, doc_id=doc_id, document=document, calls=calls, now=now
    )


def preview_image_import(
    *,
    organization: Organization,
    doc_id: UUID,
    image_bytes: bytes,
    image_mime_type: str,
    gemini: GeminiClientProtocol | None = None,
) -> ImageImportPreview:
    """Extract an image into a non-persisted, expiring reconciliation plan."""
    gemini = gemini or get_active_llm_client()
    document = services.get_document(organization=organization, doc_id=doc_id)
    extracted = _expand_image_extraction(
        gemini.generate_function_calls_from_image(
            system_instruction=f"{_IMAGE_SYSTEM_INSTRUCTION}\n\n{_document_context(document)}",
            image_bytes=image_bytes,
            image_mime_type=image_mime_type,
            tools=tools.IMAGE_IMPORT_TOOLS,
        )
    )
    calls = _reconcile_image_calls(document, extracted)
    changes = tuple(_describe_calls(document, calls))
    plan_id = uuid4().hex
    cache.set(
        _image_plan_key(plan_id),
        _ImageImportPlan(
            document_id=doc_id,
            organization_id=organization.id,
            base_revision=document.revision,
            calls=tuple(calls),
            changes=changes,
        ),
        timeout=_IMAGE_PLAN_TTL_SECONDS,
    )
    return ImageImportPreview(plan_id=plan_id, base_revision=document.revision, changes=list(changes))


def confirm_image_import(
    *, organization: Organization, doc_id: UUID, plan_id: str, now: datetime.datetime
) -> VoiceCommandResult:
    plan = cache.get(_image_plan_key(plan_id))
    if not isinstance(plan, _ImageImportPlan) or plan.document_id != doc_id or plan.organization_id != organization.id:
        raise ValueError("This image preview has expired. Upload the image again.")
    document = services.get_document(organization=organization, doc_id=doc_id)
    if document.revision != plan.base_revision:
        raise ValueError("The diagram changed after this preview. Upload the image again.")
    cache.delete(_image_plan_key(plan_id))
    if not plan.calls:
        return VoiceCommandResult(revision=document.revision, applied=[])
    translator = Translator(document.model)
    translated = [translator.translate(call) for call in plan.calls]
    result = services.submit_commands(
        organization=organization,
        doc_id=doc_id,
        commands_to_apply=[services.command_from_payload(item.payload) for item in translated],
        now=now,
        expected_revision=plan.base_revision,
    )
    return VoiceCommandResult(
        revision=result.document.revision,
        applied=[AppliedCommand(ok=True, message=item.description) for item in translated],
    )


def _image_plan_key(plan_id: str) -> str:
    return f"ai_assistant:image-import-plan:{plan_id}"


def _voice_plan_key(plan_id: str) -> str:
    return f"ai_assistant:voice-command-plan:{plan_id}"


def _describe_calls(document: ProjectDocument, calls: Sequence[GeminiFunctionCall]) -> list[AppliedCommand]:
    translator = Translator(document.model)
    described: list[AppliedCommand] = []
    for call in calls:
        try:
            described.append(AppliedCommand(ok=True, message=translator.translate(call).description))
        except (TranslationError, KeyError, ValueError, TypeError) as exc:
            described.append(AppliedCommand(ok=False, message=str(exc)))
    return described


def _reconcile_image_calls(
    document: ProjectDocument, extracted: Sequence[GeminiFunctionCall]
) -> list[GeminiFunctionCall]:
    """Create a conservative name-based diff from the image extraction.

    A class or member renamed in an image is intentionally represented as an
    addition and a removal. Images have no stable element ids, so guessing a
    rename would make a destructive change without reliable evidence.
    """
    extraction = next((call for call in extracted if call.name == "extract_uml_diagram"), None)
    if extraction is not None:
        return list(extracted)

    desired_classes: dict[str, dict[str, object]] = {}
    desired_relationships: list[dict[str, object]] = []
    for call in extracted:
        if call.name == "add_class":
            desired_classes.setdefault(_key(str(call.args["name"])), {"name": str(call.args["name"]), "attributes": [], "operations": []})
    for call in extracted:
        if call.name in {"add_attribute", "add_operation"}:
            class_name = str(call.args["class_name"])
            target = desired_classes.get(_key(class_name))
            if target is not None:
                target["attributes" if call.name == "add_attribute" else "operations"].append(dict(call.args))
        elif call.name == "add_relationship":
            desired_relationships.append(dict(call.args))

    existing_classes = {_key(c.name): c for c in document.model.classes}
    removals: list[GeminiFunctionCall] = []
    additions: list[GeminiFunctionCall] = []
    for key, uml_class in existing_classes.items():
        if key not in desired_classes:
            removals.append(GeminiFunctionCall(name="remove_class", args={"class_name": uml_class.name}))

    for key, desired in desired_classes.items():
        name = str(desired["name"])
        existing = existing_classes.get(key)
        if existing is None:
            additions.append(GeminiFunctionCall(name="add_class", args={"name": name}))
            additions.extend(_members_to_calls(name, desired))
            continue
        wanted_attributes = {_key(str(item["attribute_name"])): item for item in desired["attributes"]}
        for attribute in existing.attributes:
            wanted = wanted_attributes.get(_key(attribute.name))
            if wanted is None or str(wanted["attribute_type"]) != str(attribute.type):
                removals.append(GeminiFunctionCall(name="remove_attribute", args={"class_name": existing.name, "attribute_name": attribute.name}))
        for wanted in wanted_attributes.values():
            previous = next((a for a in existing.attributes if _key(a.name) == _key(str(wanted["attribute_name"]))), None)
            if previous is None or str(previous.type) != str(wanted["attribute_type"]):
                additions.append(GeminiFunctionCall(name="add_attribute", args=dict(wanted)))
        wanted_operations = {_key(str(item["operation_name"])): item for item in desired["operations"]}
        for operation in existing.operations:
            wanted = wanted_operations.get(_key(operation.name))
            if wanted is None or str(wanted.get("return_type") or "") != str(operation.return_type or ""):
                removals.append(GeminiFunctionCall(name="remove_operation", args={"class_name": existing.name, "operation_name": operation.name}))
        for wanted in wanted_operations.values():
            previous = next((o for o in existing.operations if _key(o.name) == _key(str(wanted["operation_name"]))), None)
            if previous is None or str(previous.return_type or "") != str(wanted.get("return_type") or ""):
                additions.append(GeminiFunctionCall(name="add_operation", args=dict(wanted)))

    existing_relationships = list(document.model.relationships)
    matched: set[str] = set()
    for desired in desired_relationships:
        source = existing_classes.get(_key(str(desired["source_class_name"])))
        target = existing_classes.get(_key(str(desired["target_class_name"])))
        current = next((r for r in existing_relationships if source and target and r.kind.value == desired["kind"] and r.source.class_id == source.id and r.target.class_id == target.id), None)
        if current is None:
            additions.append(GeminiFunctionCall(name="add_relationship", args=desired))
            continue
        matched.add(str(current.id))
        changes = {"source_class_name": str(desired["source_class_name"]), "target_class_name": str(desired["target_class_name"]), "kind": str(desired["kind"])}
        if str(desired.get("name") or "") != str(current.name or ""):
            changes["name"] = desired.get("name")
        if str(desired.get("source_multiplicity") or "0..1") != str(current.source.multiplicity):
            changes["source_multiplicity"] = str(desired.get("source_multiplicity") or "0..1")
        if str(desired.get("target_multiplicity") or "0..*") != str(current.target.multiplicity):
            changes["target_multiplicity"] = str(desired.get("target_multiplicity") or "0..*")
        if len(changes) > 3:
            additions.append(GeminiFunctionCall(name="update_relationship", args=changes))
    for relationship in existing_relationships:
        if str(relationship.id) not in matched:
            source = document.model.class_by_id(relationship.source.class_id)
            target = document.model.class_by_id(relationship.target.class_id)
            if source is not None and target is not None:
                removals.append(GeminiFunctionCall(name="remove_relationship", args={"source_class_name": source.name, "target_class_name": target.name, "kind": relationship.kind.value}))
    return [*removals, *additions]


def _members_to_calls(class_name: str, desired: dict[str, object]) -> list[GeminiFunctionCall]:
    calls: list[GeminiFunctionCall] = []
    for attribute in desired["attributes"]:
        calls.append(GeminiFunctionCall(name="add_attribute", args=dict(attribute)))
    for operation in desired["operations"]:
        calls.append(GeminiFunctionCall(name="add_operation", args=dict(operation)))
    return calls


def _key(value: str) -> str:
    return value.strip().casefold()


def _expand_image_extraction(calls: Sequence[GeminiFunctionCall]) -> list[GeminiFunctionCall]:
    """Turn the atomic vision extraction into ordered normal UML commands."""
    extraction = next((call for call in calls if call.name == "extract_uml_diagram"), None)
    if extraction is None:
        return list(calls)

    classes = extraction.args.get("classes", [])
    relationships = extraction.args.get("relationships", [])
    if not isinstance(classes, list) or not isinstance(relationships, list):
        return [GeminiFunctionCall(name="extract_uml_diagram", args={})]

    expanded: list[GeminiFunctionCall] = []
    for item in classes:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        class_name = item["name"]
        expanded.append(GeminiFunctionCall(name="add_class", args={"name": class_name}))

    for item in classes:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        class_name = item["name"]
        for attribute in item.get("attributes", []):
            if isinstance(attribute, dict) and isinstance(attribute.get("name"), str) and isinstance(attribute.get("type"), str):
                expanded.append(
                    GeminiFunctionCall(
                        name="add_attribute",
                        args={
                            "class_name": class_name,
                            "attribute_name": attribute["name"],
                            "attribute_type": attribute["type"],
                        },
                    )
                )
        for operation in item.get("operations", []):
            if isinstance(operation, dict) and isinstance(operation.get("name"), str):
                args: dict[str, object] = {
                    "class_name": class_name,
                    "operation_name": operation["name"],
                }
                if isinstance(operation.get("return_type"), str):
                    args["return_type"] = operation["return_type"]
                expanded.append(GeminiFunctionCall(name="add_operation", args=args))

    for relationship in relationships:
        if not isinstance(relationship, dict):
            continue
        required = {"kind", "source_class_name", "target_class_name"}
        if not required.issubset(relationship) or not all(isinstance(relationship[key], str) for key in required):
            continue
        args = {key: relationship[key] for key in required}
        for key in ("source_multiplicity", "target_multiplicity", "name"):
            if isinstance(relationship.get(key), str):
                args[key] = (
                    _normalize_image_multiplicity(relationship[key])
                    if key.endswith("multiplicity")
                    else relationship[key]
                )
        expanded.append(GeminiFunctionCall(name="add_relationship", args=args))
    return expanded


def _normalize_image_multiplicity(value: str) -> str:
    """Translate common handwritten UML shorthand into the command grammar."""
    compact = value.strip().replace(" ", "")
    if compact in {"*", "n", "N"}:
        return "0..*"
    if compact.lower() in {"0..n", "0..many"}:
        return "0..*"
    if compact.lower() in {"1..n", "1..many"}:
        return "1..*"
    return compact


def _apply_translated_commands(
    *,
    organization: Organization,
    doc_id: UUID,
    document: ProjectDocument,
    calls: Sequence[GeminiFunctionCall],
    now: datetime.datetime,
) -> VoiceCommandResult:
    """The per-command translate -> submit loop shared by
    `apply_voice_command` and `apply_image_command`: identical
    partial-failure policy regardless of which LLM call produced `calls`
    (see the module docstring)."""
    translator = Translator(document.model)
    applied: list[AppliedCommand] = []
    revision = document.revision

    for call in calls:
        try:
            translated = translator.translate(call)
            command = services.command_from_payload(translated.payload)
            result = services.submit_command(
                organization=organization, doc_id=doc_id, command=command, now=now
            )
            revision = result.document.revision
            applied.append(AppliedCommand(ok=True, message=translated.description))
        except (TranslationError, InvalidCommandPayloadError, KeyError, ValueError, TypeError) as exc:
            applied.append(AppliedCommand(ok=False, message=str(exc)))

    return VoiceCommandResult(revision=revision, applied=applied)
