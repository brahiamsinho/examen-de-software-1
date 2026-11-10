"""`Deployment`: one attempt to run a document's generated backend.

Tenant-scoped like `UmlDocument` (`TenantScopedModel` supplies the
`organization` FK and the raising-by-default `objects` manager). The runner is
the source of truth for the live state; this row caches it and is refreshed
whenever the UI polls `.../deployments/latest`.
"""
import uuid

from django.conf import settings
from django.db import models
from django_mongodb_backend.fields import ObjectIdAutoField

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


class RemoteDeploymentEnvironment(models.TextChoices):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class RemoteDeploymentStatus(models.TextChoices):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    AUTHORIZED = "AUTHORIZED"
    QUEUED = "QUEUED"
    DEPLOYING = "DEPLOYING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    CANCELLED = "CANCELLED"


class RemoteDeploymentDestination(TenantScopedModel):
    """Server-managed VM target metadata. Connectivity secrets live outside Django."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    destination_type = models.CharField(max_length=32, default="vm_containers")
    environment = models.CharField(max_length=16, choices=RemoteDeploymentEnvironment.choices)
    managed_config_id = models.CharField(max_length=120)
    connectivity_config_ref = models.CharField(max_length=120)
    capabilities = models.JSONField(default=list)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "managed_config_id"],
                name="remote_destination_org_config_uniq",
            )
        ]
        indexes = [models.Index(fields=["organization", "enabled"], name="remote_dest_org_enabled_idx")]


class RemoteDeploymentRequest(TenantScopedModel):
    """A governed remote operation; never implies that a VM operation occurred."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey("uml_documents.UmlDocument", on_delete=models.CASCADE, related_name="remote_deployment_requests")
    destination = models.ForeignKey(RemoteDeploymentDestination, on_delete=models.PROTECT, related_name="requests")
    action = models.CharField(max_length=16, default="deploy")
    status = models.CharField(max_length=24, choices=RemoteDeploymentStatus.choices, default=RemoteDeploymentStatus.DRAFT)
    document_revision = models.PositiveIntegerField()
    artifact_sha256 = models.CharField(max_length=64)
    validation = models.JSONField(default=dict)
    confirmation_digest = models.CharField(max_length=64, blank=True, default="")
    confirmation_expires_at = models.DateTimeField(null=True, blank=True)
    confirmation_used_at = models.DateTimeField(null=True, blank=True)
    correlation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        indexes = [models.Index(fields=["organization", "document", "status"], name="remote_req_org_doc_status_idx")]


class RemoteDeploymentEvent(TenantScopedModel):
    """Append-only audit trail. Payload is intentionally limited to safe metadata."""

    id = ObjectIdAutoField(primary_key=True)
    request = models.ForeignKey(RemoteDeploymentRequest, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=32)
    previous_status = models.CharField(max_length=24, blank=True, default="")
    new_status = models.CharField(max_length=24)
    result = models.CharField(max_length=16)
    error_code = models.CharField(max_length=64, blank=True, default="")
    message = models.CharField(max_length=500, blank=True, default="")
    correlation_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        ordering = ["id"]
        indexes = [models.Index(fields=["organization", "request", "id"], name="remote_event_org_req_id_idx")]
