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
    created_at: datetime
    updated_at: datetime


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
        # The generated project ships springdoc's API docs only (no Swagger UI).
        openapi_url=f"{public_url}v3/api-docs" if public_url else None,
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
