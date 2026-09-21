"""Deployment use cases: start (replacing), latest (refreshing from the runner), stop.

No threads: the runner builds and boots asynchronously and answers 202, so the
POST only builds the zip and uploads it. The UI polls `latest`, which pulls the
runner's state into the row. Every runner call goes through an injectable
client (`runner=`), so tests never need Docker or a network.
"""
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.http import Http404

from apps.backend_deployments.models import ACTIVE_STATUSES, Deployment, DeploymentStatus
from apps.backend_deployments.runner_client import (
    RunnerClientProtocol,
    RunnerError,
    RunnerUnavailableError,
    get_runner_client,
)
from apps.generation_export.service import build_project_archive
from apps.organizations.models import Organization
from apps.uml_modeling.documents import ProjectDocument

_VALID_STATUSES = {choice.value for choice in DeploymentStatus}


class QuotaExceededError(Exception):
    """The organization already runs its maximum of concurrent deployments."""


class DeploymentStartFailed(Exception):
    """The runner refused or could not be reached; the row was saved as failed."""

    def __init__(self, error: RunnerError):
        super().__init__(str(error))
        self.runner_error = error


def _scoped(organization: Organization):
    return Deployment.objects.for_organization(organization)


def start_deployment(
    *,
    organization: Organization,
    document: ProjectDocument,
    user,
    runner: RunnerClientProtocol | None = None,
) -> Deployment:
    # Generation errors (NothingToGenerateError, ...) surface before any row exists.
    archive = build_project_archive(document)
    runner = runner or get_runner_client()

    with transaction.atomic():
        # Serialize concurrent starts of one organization so the quota cannot be raced.
        Organization.objects.select_for_update().get(pk=organization.pk)
        active = _scoped(organization).filter(status__in=ACTIVE_STATUSES)
        replaced = list(active.filter(document_id=document.id))
        others = active.exclude(document_id=document.id).count()
        if others >= settings.DEPLOYMENT_MAX_ACTIVE_PER_ORG:
            raise QuotaExceededError(
                f"Your organization already runs {others} deployments "
                f"(limit {settings.DEPLOYMENT_MAX_ACTIVE_PER_ORG}). Stop one first."
            )
        deployment = Deployment(organization=organization, document_id=document.id, created_by=user)
        deployment.public_path = f"/gen/{deployment.id}/"
        deployment.save()
        for old in replaced:
            old.status = DeploymentStatus.STOPPED
            old.save(update_fields=["status", "updated_at"])

    for old in replaced:  # best effort: the runner's TTL reaper and startup sweep are the backstop
        try:
            runner.stop(str(old.id))
        except RunnerError:
            pass

    try:
        runner.start(str(deployment.id), organization.slug, archive)
    except RunnerError as exc:
        deployment.status = DeploymentStatus.FAILED
        deployment.error = str(exc)
        deployment.save(update_fields=["status", "error", "updated_at"])
        raise DeploymentStartFailed(exc) from exc
    deployment.status = DeploymentStatus.BUILDING
    deployment.save(update_fields=["status", "updated_at"])
    return deployment


def _refresh(deployment: Deployment, runner: RunnerClientProtocol) -> None:
    try:
        state = runner.status(str(deployment.id))
    except RunnerUnavailableError:
        return  # keep the last known state; the next poll retries
    except RunnerError:
        return
    if state is None:
        deployment.status = DeploymentStatus.STOPPED
        deployment.error = "The runner no longer knows this deployment (restarted or expired)."
    elif state.get("status") in _VALID_STATUSES:
        deployment.status = state["status"]
        deployment.error = state.get("error", "")
        deployment.log_tail = state.get("log_tail", "")
        deployment.public_path = state.get("public_path", deployment.public_path)
    deployment.save()


def latest_deployment(
    *, organization: Organization, doc_id: UUID, runner: RunnerClientProtocol | None = None
) -> Deployment:
    deployment = (
        _scoped(organization).filter(document_id=doc_id).order_by("-created_at").first()
    )
    if deployment is None:
        raise Http404("No deployment for this document")
    if deployment.status in ACTIVE_STATUSES:
        _refresh(deployment, runner or get_runner_client())
    return deployment


def stop_deployment(
    *,
    organization: Organization,
    doc_id: UUID,
    deployment_id: UUID,
    runner: RunnerClientProtocol | None = None,
) -> Deployment:
    try:
        deployment = _scoped(organization).get(id=deployment_id, document_id=doc_id)
    except Deployment.DoesNotExist as exc:
        raise Http404("Deployment not found") from exc
    if deployment.status != DeploymentStatus.STOPPED:
        (runner or get_runner_client()).stop(str(deployment.id))  # may raise: row stays active
        deployment.status = DeploymentStatus.STOPPED
        deployment.save(update_fields=["status", "updated_at"])
    return deployment
