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
