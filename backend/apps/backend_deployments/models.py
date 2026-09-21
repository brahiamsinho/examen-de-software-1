"""`Deployment`: one attempt to run a document's generated backend.

Tenant-scoped like `UmlDocument` (`TenantScopedModel` supplies the
`organization` FK and the raising-by-default `objects` manager). The runner is
the source of truth for the live state; this row caches it and is refreshed
whenever the UI polls `.../deployments/latest`.
"""
import uuid

from django.conf import settings
from django.db import models

from apps.organizations.models import TenantScopedManager, TenantScopedModel


class DeploymentStatus(models.TextChoices):
    QUEUED = "queued"
    BUILDING = "building"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


ACTIVE_STATUSES = (
    DeploymentStatus.QUEUED,
    DeploymentStatus.BUILDING,
    DeploymentStatus.STARTING,
    DeploymentStatus.RUNNING,
)


class Deployment(TenantScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "uml_documents.UmlDocument", on_delete=models.CASCADE, related_name="deployments"
    )
    status = models.CharField(
        max_length=16, choices=DeploymentStatus.choices, default=DeploymentStatus.QUEUED
    )
    error = models.TextField(blank=True, default="")
    log_tail = models.TextField(blank=True, default="")
    public_path = models.CharField(max_length=128, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        indexes = [models.Index(fields=["organization", "status"])]
