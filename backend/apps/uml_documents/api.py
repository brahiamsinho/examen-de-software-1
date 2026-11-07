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
from ninja.errors import HttpError
from ninja.security import django_auth

from apps.organizations.constants import Role
from apps.organizations.permissions import require_role, resolve_membership
from apps.backend_deployments import service as deployment_service
from apps.uml_documents import codec, services
from apps.uml_documents.errors import InvalidCommandPayloadError
from apps.uml_documents.schemas import (
    CommandIn,
    CommandResultOut,
    DocumentCreateIn,
    DocumentOut,
    DocumentSummaryOut,
    VersionCreateIn,
    VersionDiffOut,
    VersionOut,
    VersionRestoreIn,
    VersionSummaryOut,
    TemplateCreateIn,
    TemplateInstantiateIn,
    TemplateOut,
    TemplateSummaryOut,
)

documents_router = Router(auth=django_auth)


def _document_out(document) -> dict:
    return codec.document_out(document)


def _document_summary_out(document) -> dict:
    return {
        "id": document.id,
        "name": document.metadata.name,
        "revision": document.revision,
        "updated_at": document.updated_at,
    }


def _version_summary_out(version) -> dict:
    return {
        "id": version.id,
        "number": version.number,
        "source_revision": version.source_revision,
        "description": version.description,
        "created_by_id": version.created_by_id,
        "created_at": version.created_at,
    }


def _template_summary_out(template) -> dict:
    return {
        "id": template.id,
        "name": template.name,
        "source_document_id": template.source_document_id,
        "created_by_id": template.created_by_id,
        "created_at": template.created_at,
    }


@documents_router.get("", response=list[DocumentSummaryOut])
def list_documents_view(request: HttpRequest, org_slug: Path[str]):
    membership = resolve_membership(request, org_slug)  # no require_role — DD3, any member reads
    documents = services.list_documents(organization=membership.organization)
    return [_document_summary_out(document) for document in documents]


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


@documents_router.get("/templates", response=list[TemplateSummaryOut])
def list_templates_view(request: HttpRequest, org_slug: Path[str]):
    membership = resolve_membership(request, org_slug)
    return [_template_summary_out(template) for template in services.list_templates(organization=membership.organization)]


@documents_router.get("/templates/{template_id}", response=TemplateOut)
def get_template_view(request: HttpRequest, org_slug: Path[str], template_id: UUID):
    membership = resolve_membership(request, org_slug)
    template = services.get_template(organization=membership.organization, template_id=template_id)
    return {**_template_summary_out(template), "snapshot": template.snapshot}


@documents_router.post("/{doc_id}/templates", response={201: TemplateOut})
def create_template_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: TemplateCreateIn
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    template = services.create_template(
        organization=membership.organization, doc_id=doc_id, created_by=request.user, name=payload.name
    )
    return Status(201, {**_template_summary_out(template), "snapshot": template.snapshot})


@documents_router.post("/templates/{template_id}/instantiate", response={201: DocumentOut})
def instantiate_template_view(
    request: HttpRequest, org_slug: Path[str], template_id: UUID, payload: TemplateInstantiateIn
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    document = services.instantiate_template(
        organization=membership.organization,
        template_id=template_id,
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


@documents_router.post("/{doc_id}/versions", response={201: VersionOut})
def create_version_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: VersionCreateIn
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        version = services.create_version(
            organization=membership.organization,
            doc_id=doc_id,
            created_by=request.user,
            description=payload.description,
            expected_revision=payload.expected_revision,
        )
    except ValueError as exc:
        raise HttpError(409, str(exc)) from exc
    return Status(201, {**_version_summary_out(version), "snapshot": version.snapshot})


@documents_router.get("/{doc_id}/versions", response=list[VersionSummaryOut])
def list_versions_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)
    return [_version_summary_out(version) for version in services.list_versions(organization=membership.organization, doc_id=doc_id)]


@documents_router.get("/{doc_id}/versions/compare", response=VersionDiffOut)
def compare_versions_view(
    request: HttpRequest,
    org_slug: Path[str],
    doc_id: UUID,
    from_version_id: UUID,
    to_version_id: UUID,
):
    membership = resolve_membership(request, org_slug)
    return services.compare_versions(
        organization=membership.organization,
        doc_id=doc_id,
        from_version_id=from_version_id,
        to_version_id=to_version_id,
    )


@documents_router.get("/{doc_id}/versions/{version_id}", response=VersionOut)
def get_version_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, version_id: UUID):
    membership = resolve_membership(request, org_slug)
    version = services.get_version(
        organization=membership.organization, doc_id=doc_id, version_id=version_id
    )
    return {**_version_summary_out(version), "snapshot": version.snapshot}


@documents_router.post("/{doc_id}/versions/{version_id}/restore", response=DocumentOut)
def restore_version_view(
    request: HttpRequest,
    org_slug: Path[str],
    doc_id: UUID,
    version_id: UUID,
    payload: VersionRestoreIn,
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        document = services.restore_version(
            organization=membership.organization,
            doc_id=doc_id,
            version_id=version_id,
            expected_revision=payload.expected_revision,
            now=timezone.now(),
        )
    except ValueError as exc:
        raise HttpError(409, str(exc)) from exc
    return _document_out(document)


@documents_router.delete("/{doc_id}", response={204: None})
def delete_document_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    services.get_document(organization=membership.organization, doc_id=doc_id)  # 404 before side effects
    # Best effort: a runner outage must never block deleting the diagram.
    deployment_service.stop_active_for_document(
        organization=membership.organization, doc_id=doc_id
    )
    services.delete_document(organization=membership.organization, doc_id=doc_id)
    return Status(204, None)


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
