"""HTTP router for running a document's generated backend.

Mounted under `/orgs/{org_slug}/documents` like `generation_export`. Starting
and stopping need OWNER/EDITOR (they consume resources); reading the status is
open to any member. Failures become stable `{detail, code}` bodies.
"""
from datetime import datetime
from uuid import UUID

from django.conf import settings
from django.http import HttpRequest
from ninja import Path, Router, Schema, Status
from ninja.security import django_auth

from apps.backend_deployments import service
from apps.backend_deployments.models import Deployment
from apps.backend_deployments.models import RemoteDeploymentDestination, RemoteDeploymentRequest
from apps.backend_deployments import remote_service
from apps.backend_deployments.runner_client import RunnerRejectedError
from apps.generation_export.api import GENERATION_ERRORS
from apps.generation_export.service import NothingToGenerateError
from apps.organizations.constants import Role
from apps.organizations.permissions import require_role, resolve_membership
from apps.uml_documents import services

deployments_router = Router(auth=django_auth)


class DeploymentOut(Schema):
    id: UUID
    document_id: UUID
    status: str
    error: str
    log_tail: str
    public_path: str
    public_url: str | None
    openapi_url: str | None
    docs_url: str | None
    created_at: datetime
    updated_at: datetime


class RemoteDestinationIn(Schema):
    name: str
    environment: str
    managed_config_id: str
    connectivity_config_ref: str
    capabilities: list[str] = []


class RemoteDestinationOut(Schema):
    id: UUID
    name: str
    destination_type: str
    environment: str
    managed_config_id: str
    connectivity_config_ref: str
    capabilities: list[str]
    enabled: bool


class RemotePreviewOut(Schema):
    checks: list[dict]
    warnings: list[str]
    can_request: bool
    artifact_sha256: str
    document_revision: int


class RemoteRequestIn(Schema):
    destination_id: UUID


class RemoteConfirmOut(Schema):
    confirmation_token: str
    expires_at: datetime


class RemoteConfirmIn(Schema):
    confirmation_token: str


class RemoteRequestOut(Schema):
    id: UUID
    destination_id: UUID
    destination_name: str
    environment: str
    action: str
    status: str
    document_revision: int
    artifact_sha256: str
    error_code: str
    error_message: str
    correlation_id: UUID
    created_at: datetime
    updated_at: datetime


class RemoteEventOut(Schema):
    id: int
    action: str
    previous_status: str
    new_status: str
    result: str
    error_code: str
    message: str
    correlation_id: UUID
    created_at: datetime


def _destination_out(destination: RemoteDeploymentDestination) -> RemoteDestinationOut:
    return RemoteDestinationOut(
        id=destination.id, name=destination.name, destination_type=destination.destination_type,
        environment=destination.environment, managed_config_id=destination.managed_config_id,
        connectivity_config_ref=destination.connectivity_config_ref,
        capabilities=destination.capabilities, enabled=destination.enabled,
    )


def _remote_out(request: RemoteDeploymentRequest) -> RemoteRequestOut:
    return RemoteRequestOut(
        id=request.id, destination_id=request.destination_id, destination_name=request.destination.name,
        environment=request.destination.environment, action=request.action, status=request.status,
        document_revision=request.document_revision, artifact_sha256=request.artifact_sha256,
        error_code=request.error_code, error_message=request.error_message,
        correlation_id=request.correlation_id, created_at=request.created_at, updated_at=request.updated_at,
    )


def _out(deployment: Deployment) -> DeploymentOut:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    public_url = f"{base}{deployment.public_path}" if deployment.public_path else None
    return DeploymentOut(
        id=deployment.id,
        document_id=deployment.document_id,
        status=deployment.status,
        error=deployment.error,
        log_tail=deployment.log_tail,
        public_path=deployment.public_path,
        public_url=public_url,
        # The generated project serves Swagger UI (docs) and the raw OpenAPI JSON.
        openapi_url=f"{public_url}v3/api-docs" if public_url else None,
        docs_url=f"{public_url}swagger-ui/index.html" if public_url else None,
        created_at=deployment.created_at,
        updated_at=deployment.updated_at,
    )


def _error(status: int, message: str, code: str) -> Status:
    return Status(status, {"detail": message, "code": code})


@deployments_router.post(
    "/{doc_id}/deployments", response={202: DeploymentOut, 409: dict, 422: dict, 502: dict}
)
def start_deployment_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    try:
        deployment = service.start_deployment(
            organization=membership.organization, document=document, user=request.user
        )
    except NothingToGenerateError as exc:
        return _error(422, str(exc), "nothing_to_generate")
    except GENERATION_ERRORS as exc:
        return _error(422, str(exc), "generation_failed")
    except service.QuotaExceededError as exc:
        return _error(409, str(exc), "quota_exceeded")
    except service.DeploymentStartFailed as exc:
        code = "runner_rejected" if isinstance(exc.runner_error, RunnerRejectedError) else "runner_unavailable"
        return _error(502, str(exc), code)
    return Status(202, _out(deployment))


@deployments_router.get("/{doc_id}/deployments/latest", response={200: DeploymentOut})
def latest_deployment_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)  # any member reads
    return _out(service.latest_deployment(organization=membership.organization, doc_id=doc_id))


@deployments_router.delete(
    "/{doc_id}/deployments/{deployment_id}", response={200: DeploymentOut, 502: dict}
)
def stop_deployment_view(
    request: HttpRequest, org_slug: Path[str], doc_id: UUID, deployment_id: UUID
):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER, Role.EDITOR)
    try:
        deployment = service.stop_deployment(
            organization=membership.organization, doc_id=doc_id, deployment_id=deployment_id
        )
    except service.RunnerError as exc:
        return _error(502, str(exc), "runner_unavailable")
    return _out(deployment)


@deployments_router.get("/{doc_id}/remote-destinations", response=list[RemoteDestinationOut])
def list_remote_destinations_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID):
    membership = resolve_membership(request, org_slug)
    services.get_document(organization=membership.organization, doc_id=doc_id)
    return [_destination_out(destination) for destination in remote_service.destinations(membership.organization)]


@deployments_router.post("/remote-destinations", response={201: RemoteDestinationOut, 422: dict})
def create_remote_destination_view(request: HttpRequest, org_slug: Path[str], payload: RemoteDestinationIn):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER)
    if payload.environment not in {"development", "testing", "production"}:
        return _error(422, "El entorno debe ser development, testing o production.", "invalid_destination")
    destination = RemoteDeploymentDestination.objects.unscoped().create(
        organization=membership.organization, name=payload.name, environment=payload.environment,
        managed_config_id=payload.managed_config_id, connectivity_config_ref=payload.connectivity_config_ref,
        capabilities=payload.capabilities,
    )
    return Status(201, _destination_out(destination))


@deployments_router.post("/{doc_id}/remote-deployments/preview", response={200: RemotePreviewOut, 422: dict})
def preview_remote_deployment_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: RemoteRequestIn):
    membership = resolve_membership(request, org_slug)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    preview = remote_service.preview(organization=membership.organization, document=document, destination_id=payload.destination_id)
    return RemotePreviewOut(checks=preview["checks"], warnings=preview["warnings"], can_request=preview["can_request"], artifact_sha256=preview["artifact_sha256"], document_revision=preview["document_revision"])


@deployments_router.post("/{doc_id}/remote-deployments", response={202: RemoteRequestOut, 403: dict, 409: dict})
def request_remote_deployment_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, payload: RemoteRequestIn):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    try:
        remote = remote_service.request_deployment(organization=membership.organization, document=document, user=request.user, destination_id=payload.destination_id)
    except remote_service.RemoteDeploymentBlocked as exc:
        return _error(409, str(exc), exc.code)
    return Status(202, _remote_out(remote))


@deployments_router.post("/{doc_id}/remote-deployments/{request_id}/confirmation", response={200: RemoteConfirmOut, 409: dict})
def issue_remote_confirmation_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, request_id: UUID):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    remote = remote_service.get_request(membership.organization, document, request_id)
    if remote.created_by_id != request.user.id:
        return _error(409, "La solicitud pertenece a otro usuario.", "confirmation_invalid")
    try:
        token = remote_service.issue_confirmation(request=remote, user=request.user)
    except remote_service.RemoteDeploymentError as exc:
        return _error(409, str(exc), exc.code)
    return RemoteConfirmOut(confirmation_token=token, expires_at=remote.confirmation_expires_at)


@deployments_router.post("/{doc_id}/remote-deployments/{request_id}/confirm", response={200: RemoteRequestOut, 409: dict})
def confirm_remote_deployment_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, request_id: UUID, payload: RemoteConfirmIn):
    membership = resolve_membership(request, org_slug)
    require_role(membership, Role.OWNER)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    try:
        remote = remote_service.confirm(organization=membership.organization, document=document, request_id=request_id, user=request.user, token=payload.confirmation_token)
    except remote_service.RemoteDeploymentError as exc:
        return _error(409, str(exc), exc.code)
    return _remote_out(remote)


@deployments_router.get("/{doc_id}/remote-deployments/{request_id}", response=RemoteRequestOut)
def get_remote_deployment_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, request_id: UUID):
    membership = resolve_membership(request, org_slug)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    return _remote_out(remote_service.get_request(membership.organization, document, request_id))


@deployments_router.get("/{doc_id}/remote-deployments/{request_id}/events", response=list[RemoteEventOut])
def remote_deployment_events_view(request: HttpRequest, org_slug: Path[str], doc_id: UUID, request_id: UUID):
    membership = resolve_membership(request, org_slug)
    document = services.get_document(organization=membership.organization, doc_id=doc_id)
    remote = remote_service.get_request(membership.organization, document, request_id)
    return [
        RemoteEventOut(id=event.id, action=event.action, previous_status=event.previous_status,
                       new_status=event.new_status, result=event.result, error_code=event.error_code,
                       message=event.message, correlation_id=event.correlation_id, created_at=event.created_at)
        for event in remote.events.all()
    ]
