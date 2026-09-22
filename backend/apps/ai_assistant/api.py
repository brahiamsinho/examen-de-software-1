"""HTTP router for the ai_assistant domain: one endpoint that turns a
voice transcript into a sequence of applied UML commands. Thin, mirroring
`apps.uml_documents.api`'s resolve_membership -> require_role -> call one
service function -> serialize shape.
"""
from uuid import UUID

from django.http import HttpRequest
from django.utils import timezone
from ninja import Path, Router
from ninja.security import django_auth

from apps.ai_assistant import service
from apps.ai_assistant.errors import GeminiRequestError, MissingApiKeyError
from apps.ai_assistant.schemas import VoiceCommandIn, VoiceCommandOut
from apps.organizations.constants import Role
from apps.organizations.permissions import require_role, resolve_membership

ai_assistant_router = Router(auth=django_auth)


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

    api.add_exception_handler(MissingApiKeyError, _handle_missing_api_key)
    api.add_exception_handler(GeminiRequestError, _handle_gemini_request_error)
