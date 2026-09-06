"""ORM models for the multi-tenant organizations domain.

The only file in `apps/organizations/` that defines DB tables. Business
invariants (last-owner, duplicate slug, etc.) live in `services.py`, not
here — this module only defines shape, constraints, and tenant-scoping
mechanics (DD1).

`TenantScopedModel` (and its manager/queryset) is the reusable abstract
base for tenant-scoped tables — it lives here because tenancy is this
domain's concern; future apps needing tenant scoping import it from here.
"""
import uuid

from django.conf import settings
from django.db import models

from apps.organizations.constants import Plan, Role
from apps.organizations.errors import TenantScopeViolation


class Organization(models.Model):
    """The tenant boundary. Addressed by `slug`, never a sequential id (D3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60, unique=True, db_index=True)
    plan = models.CharField(max_length=16, choices=Plan.choices, default=Plan.STARTER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="organizations.Membership", related_name="organizations"
    )

    def __str__(self) -> str:
        return self.slug


class TenantScopedQuerySet(models.QuerySet):
    def for_organization(self, organization: "Organization"):
        return self.filter(organization=organization)


class TenantScopedManager(models.Manager.from_queryset(TenantScopedQuerySet)):
    """Raises on any unscoped default access, except reverse related
    access (which is already org-bound because Django binds `instance`
    on the related manager) — see design.md DD1.
    """

    def get_queryset(self):
        if getattr(self, "instance", None) is not None:
            return super().get_queryset()
        raise TenantScopeViolation(
            f"{self.model.__name__} is tenant-scoped: use .for_organization(org) or .unscoped()."
        )

    def for_organization(self, organization: "Organization"):
        return self.unscoped().filter(organization=organization)

    def unscoped(self):
        return super().get_queryset()


class TenantScopedModel(models.Model):
    """Abstract base for every tenant-scoped table (tenant-isolation spec)."""

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        null=False,
    )
    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "all_objects"


class Membership(TenantScopedModel):
    """The join between `User` and `Organization`, carrying exactly one role."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"], name="identity_membership_user_org_uniq"
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "role"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}@{self.organization_id}:{self.role}"
