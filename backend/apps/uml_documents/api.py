"""HTTP router for the uml_documents domain (design.md's Data Flow /
Interfaces-Contracts block).

Thin by construction, mirroring `apps.organizations.api`: parse schema ->
resolve membership -> check role -> call one service function ->
serialize. No business logic lives here.
"""
from uuid import UUID

from django.http import HttpRequest
from django.utils import timezone
from ninja import Body, Path, Router, Status
from ninja.security import django_auth

from apps.organizations.constants import Role
from apps.organizations.permissions import require_role, resolve_membership
from apps.uml_documents import codec, services
from apps.uml_documents.errors import InvalidCommandPayloadError
from apps.uml_documents.schemas import CommandIn, CommandResultOut, DocumentCreateIn, DocumentOut

documents_router = Router(auth=django_auth)


def _document_out(document) -> dict:
    return {
        "id": document.id,
        "owner_id": document.owner_id,
        "revision": document.revision,
        "metadata": {"name": document.metadata.name, "description": document.metadata.description},
        "model": codec._encode_model(document.model),
        "layout": codec._encode_layout(document.layout),
        "created_at": document.created_at,
        "updated_at": document.updated_at,
    }


@documents_router.post("", response={201: DocumentOut})
def create_document_view(request: HttpRequest, org_slug: Path[str], payload: DocumentCreateIn):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    document = services.create_document(
        organization=membership.organization,
        owner_id=str(request.user.id),
        name=payload.name,
        now=timezone.now(),
    )
    return Status(201, _document_out(document))


@documents_router.get("/{doc_id}", response=DocumentOut)
def get_document_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    return _document_out(document)


@documents_router.post("/{doc_id}/commands", response=CommandResultOut)
def submit_command_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: Body[CommandIn]
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    command = services.command_from_payload(payload)
    result = services.submit_command(
        organization=membership.organization,
        doc_id=doc_id,
        command=command,
        now=timezone.now(),
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


# --- exception handlers ----------------------------------------------------


def register_exception_handlers(api) -> None:
    def _handle_invalid_command_payload(request, exc: InvalidCommandPayloadError):
        return api.create_response(
            request, {"detail": str(exc), "code": "invalid_command_payload"}, status=422
        )

    api.add_exception_handler(InvalidCommandPayloadError, _handle_invalid_command_payload)
