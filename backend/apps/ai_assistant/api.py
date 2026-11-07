"""HTTP router for the ai_assistant domain: one endpoint that turns a
voice transcript into a sequence of applied UML commands. Thin, mirroring
`apps.uml_documents.api`'s resolve_membership -> require_role -> call one
service function -> serialize shape.
"""
import dataclasses
import json
from uuid import UUID

from django.http import HttpRequest
from django.utils import timezone
from ninja import File, Path, Router, UploadedFile
from ninja.errors import HttpError
from ninja.security import django_auth
from pydantic import ValidationError

from apps.ai_assistant import chat, proposals, service
from apps.ai_assistant.errors import GeminiRequestError, InvalidImageError, MissingApiKeyError
from apps.ai_assistant.schemas import (
    ApproveProposalIn,
    ChatMessageIn,
    ChatMessageOut,
    ChatPostOut,
    ImageImportConfirmIn,
    ImageImportPreviewOut,
    ProposalOut,
    ProposalRequestIn,
    VoiceCommandConfirmIn,
    VoiceCommandIn,
    VoiceCommandOut,
    VoiceCommandPreviewOut,
)
from apps.organizations.constants import Role
from apps.organizations.permissions import require_role, resolve_membership

ai_assistant_router = Router(auth=django_auth)

# 10 MB: generous for a screenshot/photo of a diagram while still bounding
# the request body before it ever reaches the OpenAI vision call.
_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})


@ai_assistant_router.post("/{doc_id}/voice-command", response=VoiceCommandPreviewOut)
def voice_command_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: VoiceCommandIn
):
    """Compatibility route: spoken commands are preview-only until confirmed."""
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    preview = service.preview_voice_command(
        organization=membership.organization,
        doc_id=doc_id,
        transcript=payload.transcript,
    )
    return {
        "plan_id": preview.plan_id,
        "base_revision": preview.base_revision,
        "changes": [dataclasses.asdict(item) for item in preview.changes],
    }


@ai_assistant_router.post("/{doc_id}/voice-command-preview", response=VoiceCommandPreviewOut)
def voice_command_preview_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: VoiceCommandIn
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    preview = service.preview_voice_command(
        organization=membership.organization, doc_id=doc_id, transcript=payload.transcript
    )
    return {
        "plan_id": preview.plan_id,
        "base_revision": preview.base_revision,
        "changes": [dataclasses.asdict(item) for item in preview.changes],
    }


@ai_assistant_router.post("/{doc_id}/voice-command-confirm", response=VoiceCommandOut)
def voice_command_confirm_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: VoiceCommandConfirmIn
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        result = service.confirm_voice_command(
            organization=membership.organization, doc_id=doc_id, plan_id=payload.plan_id, now=timezone.now()
        )
    except ValueError as exc:
        raise HttpError(409, str(exc)) from exc
    return {"revision": result.revision, "applied": [dataclasses.asdict(item) for item in result.applied]}


@ai_assistant_router.post("/{doc_id}/image-command", response=ImageImportPreviewOut)
def image_command_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, file: File[UploadedFile]
):
    """Compatibility route: image input is preview-only, never a write."""
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)

    if file.content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
        raise InvalidImageError(
            f"Unsupported image type {file.content_type!r}; expected one of "
            f"{sorted(_ALLOWED_IMAGE_CONTENT_TYPES)}."
        )
    if file.size is not None and file.size > _MAX_IMAGE_BYTES:
        raise InvalidImageError("The image exceeds the maximum allowed size of 10 MB.")

    preview = service.preview_image_import(
        organization=membership.organization,
        doc_id=doc_id,
        image_bytes=file.read(),
        image_mime_type=file.content_type,
    )
    return {
        "plan_id": preview.plan_id,
        "base_revision": preview.base_revision,
        "changes": [dataclasses.asdict(item) for item in preview.changes],
    }


@ai_assistant_router.post("/{doc_id}/image-import-preview", response=ImageImportPreviewOut)
def image_import_preview_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, file: File[UploadedFile]
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    if file.content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
        raise InvalidImageError(f"Unsupported image type {file.content_type!r}.")
    if file.size is not None and file.size > _MAX_IMAGE_BYTES:
        raise InvalidImageError("The image exceeds the maximum allowed size of 10 MB.")
    preview = service.preview_image_import(
        organization=membership.organization,
        doc_id=doc_id,
        image_bytes=file.read(),
        image_mime_type=file.content_type,
    )
    return {"plan_id": preview.plan_id, "base_revision": preview.base_revision, "changes": [dataclasses.asdict(item) for item in preview.changes]}


@ai_assistant_router.post("/{doc_id}/image-import-confirm", response=VoiceCommandOut)
def image_import_confirm_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: ImageImportConfirmIn
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        result = service.confirm_image_import(
            organization=membership.organization, doc_id=doc_id, plan_id=payload.plan_id, now=timezone.now()
        )
    except ValueError as exc:
        raise HttpError(409, str(exc)) from exc
    return {"revision": result.revision, "applied": [dataclasses.asdict(item) for item in result.applied]}


# --- AI board proposals (issue #15) ----------------------------------------


@ai_assistant_router.get("/{doc_id}/chat", response=list[ChatMessageOut])
def list_chat_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)  # any member reads
    found = chat.list_messages(organization=membership.organization, doc_id=doc_id)
    return [chat.serialize_message(item) for item in found]


@ai_assistant_router.post("/{doc_id}/chat", response={201: ChatPostOut})
def post_chat_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: ChatMessageIn):
    """Posts to the diagram's group chat. A message that mentions `@IA` also
    returns the model's reply; if the model fails the message is kept and the
    failure is reported in `ai_error` instead of an HTTP error."""
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        result = chat.post_message(
            organization=membership.organization, doc_id=doc_id, author=request.user, content=payload.content
        )
    except chat.ChatError as exc:
        raise HttpError(422, str(exc)) from exc
    return 201, {
        "message": chat.serialize_message(result.message),
        "reply": chat.serialize_message(result.reply) if result.reply else None,
        "ai_error": result.ai_error,
    }


@ai_assistant_router.post("/{doc_id}/ai-proposals", response={201: ProposalOut})
def create_proposal_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: ProposalRequestIn
):
    """A teammate asks the AI for ideas. The answer is a draft: it is stored
    and broadcast, and the diagram is not touched until someone approves it."""
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        proposal = proposals.create_proposal(
            organization=membership.organization,
            doc_id=doc_id,
            requested_by=request.user,
            prompt=payload.prompt,
        )
    except proposals.NoSuggestionsError as exc:
        raise HttpError(422, str(exc)) from exc
    return 201, proposals.serialize_proposal(proposal)


@ai_assistant_router.get("/{doc_id}/ai-proposals", response=list[ProposalOut])
def list_proposals_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)  # any member reads
    found = proposals.list_proposals(organization=membership.organization, doc_id=doc_id)
    return [proposals.serialize_proposal(item) for item in found]


def _optional_approve_body(request: HttpRequest) -> ApproveProposalIn | None:
    if request.content_type != "application/json" or not request.body:
        return None
    try:
        return ApproveProposalIn.model_validate(json.loads(request.body))
    except (ValueError, ValidationError) as exc:
        raise HttpError(422, "The approval body must be JSON like {\"selected\": [0, 2]}.") from exc


@ai_assistant_router.post("/{doc_id}/ai-proposals/{proposal_id}/approve", response=ProposalOut)
def approve_proposal_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, proposal_id: UUID):
    """Applies the chosen changes (`selected` indices in a JSON body) or, with
    no body at all, every change. The unchosen ones are discarded with the
    proposal. The body is read by hand because Ninja answers 400 to a missing
    body, and "approve everything" must keep working as a bodyless POST."""
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    payload = _optional_approve_body(request)
    try:
        proposal = proposals.approve_proposal(
            organization=membership.organization,
            doc_id=doc_id,
            proposal_id=proposal_id,
            decided_by=request.user,
            now=timezone.now(),
            selected=payload.selected if payload is not None else None,
        )
    except ValueError as exc:
        raise HttpError(409, str(exc)) from exc
    return proposals.serialize_proposal(proposal)


@ai_assistant_router.post("/{doc_id}/ai-proposals/{proposal_id}/reject", response=ProposalOut)
def reject_proposal_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, proposal_id: UUID):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        proposal = proposals.reject_proposal(
            organization=membership.organization,
            doc_id=doc_id,
            proposal_id=proposal_id,
            decided_by=request.user,
            now=timezone.now(),
        )
    except ValueError as exc:
        raise HttpError(409, str(exc)) from exc
    return proposals.serialize_proposal(proposal)


# --- exception handlers ----------------------------------------------------


def register_exception_handlers(api) -> None:
    def _handle_missing_api_key(request, exc: MissingApiKeyError):
        return api.create_response(
            request, {"detail": str(exc), "code": "gemini_api_key_missing"}, status=503
        )

    def _handle_gemini_request_error(request, exc: GeminiRequestError):
        return api.create_response(
            request, {"detail": str(exc), "code": "gemini_request_failed"}, status=502
        )

    def _handle_invalid_image_error(request, exc: InvalidImageError):
        return api.create_response(request, {"detail": str(exc), "code": "invalid_image"}, status=400)

    api.add_exception_handler(MissingApiKeyError, _handle_missing_api_key)
    api.add_exception_handler(GeminiRequestError, _handle_gemini_request_error)
    api.add_exception_handler(InvalidImageError, _handle_invalid_image_error)
