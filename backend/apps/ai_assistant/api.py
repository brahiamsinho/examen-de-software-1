"""HTTP router for the ai_assistant domain: one endpoint that turns a
voice transcript into a sequence of applied UML commands. Thin, mirroring
`apps.uml_documents.api`'s resolve_membership -> require_role -> call one
service function -> serialize shape.
"""
from uuid import UUID

from django.http import HttpRequest
from django.utils import timezone
from ninja import File, Path, Router, UploadedFile
from ninja.security import django_auth

from apps.ai_assistant import service
from apps.ai_assistant.errors import GeminiRequestError, InvalidImageError, MissingApiKeyError
from apps.ai_assistant.schemas import VoiceCommandIn, VoiceCommandOut
from apps.organizations.constants import Role
from apps.organizations.permissions import require_role, resolve_membership

ai_assistant_router = Router(auth=django_auth)

# 10 MB: generous for a screenshot/photo of a diagram while still bounding
# the request body before it ever reaches the OpenAI vision call.
_MAX_IMAGE_BYTES = 10 * 1024 * 1024
_ALLOWED_IMAGE_CONTENT_TYPES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})


@ai_assistant_router.post("/{doc_id}/voice-command", response=VoiceCommandOut)
def voice_command_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: VoiceCommandIn
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    result = service.apply_voice_command(
        organization=membership.organization,
        doc_id=doc_id,
        transcript=payload.transcript,
        now=timezone.now(),
    )
    return {
        "revision": result.revision,
        "applied": [{"ok": item.ok, "message": item.message} for item in result.applied],
    }


@ai_assistant_router.post("/{doc_id}/image-command", response=VoiceCommandOut)
def image_command_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, file: File[UploadedFile]
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)

    if file.content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
        raise InvalidImageError(
            f"Unsupported image type {file.content_type!r}; expected one of "
            f"{sorted(_ALLOWED_IMAGE_CONTENT_TYPES)}."
        )
    if file.size is not None and file.size > _MAX_IMAGE_BYTES:
        raise InvalidImageError("The image exceeds the maximum allowed size of 10 MB.")

    result = service.apply_image_command(
        organization=membership.organization,
        doc_id=doc_id,
        image_bytes=file.read(),
        image_mime_type=file.content_type,
        now=timezone.now(),
    )
    return {
        "revision": result.revision,
        "applied": [{"ok": item.ok, "message": item.message} for item in result.applied],
    }


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
