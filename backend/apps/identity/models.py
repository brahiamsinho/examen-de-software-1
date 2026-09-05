"""ORM models for the multi-tenant identity domain.

The only file in `apps/identity/` that defines DB tables. Business
invariants (last-owner, duplicate email/slug, etc.) live in `services.py`
(later PR), not here — this module only defines shape, constraints, and
tenant-scoping mechanics (DD1).
"""
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.identity.constants import Plan, Role
from apps.identity.errors import TenantScopeViolation


class UserManager(BaseUserManager):
    """Manager for the custom, email-identified `User` model."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("The email field must be set.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """The project's first persisted identity. No `username` field (D6)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    full_name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="identity_user_email_ci_unique"),
        ]

    def __str__(self) -> str:
        return self.email


class Organization(models.Model):
    """The tenant boundary. Addressed by `slug`, never a sequential id (D3)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=60, unique=True, db_index=True)
    plan = models.CharField(max_length=16, choices=Plan.choices, default=Plan.STARTER)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    members = models.ManyToManyField(
        "identity.User", through="identity.Membership", related_name="organizations"
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
        "identity.Organization",
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
        "identity.User", on_delete=models.CASCADE, related_name="memberships"
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
