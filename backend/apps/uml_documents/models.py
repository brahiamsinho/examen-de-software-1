"""ORM model for the UML document persistence domain.

`UmlDocument` splits a `ProjectDocument` (apps.uml_modeling.documents)
into real columns (`id`, `owner_id`, `revision`, timestamps) plus one
`data: JSONField` blob holding only the codec-serialized
`metadata`/`model`/`layout` content triple (design.md DD3).

Mirrors `apps.organizations.models.Membership`'s tenant-scoping wiring
exactly: `TenantScopedModel` supplies the `organization` FK and the
raising-by-default `objects` manager; `all_objects` is the escape-hatch
default manager used only by `all_objects`-aware call sites (never by
`services.py`, which must go through `.for_organization(...)` only).
"""
import uuid

from django.conf import settings
from django.db import models

from apps.organizations.models import TenantScopedManager, TenantScopedModel


class UmlDocument(TenantScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_id = models.CharField(max_length=255)
    revision = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    data = models.JSONField(default=dict)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        indexes = [models.Index(fields=["organization", "owner_id"])]


class UmlVersion(TenantScopedModel):
    """An immutable, tenant-bound snapshot of one UML document state."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(UmlDocument, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    source_revision = models.PositiveIntegerField()
    description = models.CharField(max_length=500, blank=True, default="")
    snapshot = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        constraints = [models.UniqueConstraint(fields=["document", "number"], name="unique_uml_version_number")]
        indexes = [models.Index(fields=["organization", "document", "-number"])]


class UmlTemplate(TenantScopedModel):
    """An organization-private reusable UML document snapshot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    source_document = models.ForeignKey(UmlDocument, on_delete=models.SET_NULL, null=True, related_name="templates")
    snapshot = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        indexes = [models.Index(fields=["organization", "name"])]
