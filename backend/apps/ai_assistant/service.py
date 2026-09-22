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
from uuid import UUID

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
    "tool. Replicate every class, attribute, operation, and relationship "
    "visible in the image using the provided functions, one call per element. "
    "Always create a class before adding its attributes or operations, and "
    "create both endpoint classes before adding a relationship between them. "
    "Only call the provided functions — never invent a class, attribute, "
    "operation, or relationship that is not actually visible in the image. "
    "Always refer to classes, attributes, and operations by name, never by "
    "id. If the image is unclear or only partially legible, do the best you "
    "can with what you can make out rather than failing outright."
)


@dataclasses.dataclass(frozen=True)
class AppliedCommand:
    ok: bool
    message: str


@dataclasses.dataclass(frozen=True)
class VoiceCommandResult:
    revision: int
    applied: list[AppliedCommand]


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
        tools=tools.TOOLS,
    )

    return _apply_translated_commands(
        organization=organization, doc_id=doc_id, document=document, calls=calls, now=now
    )


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
