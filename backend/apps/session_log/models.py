"""Persistence for the per-diagram session log (issue #17).

A `LogEntry` says who did what to a diagram and when. It is APPEND-ONLY: the
model, its querysets and both managers refuse every update and delete, and the
HTTP API has no write endpoint. The author is stored as a snapshot (`actor_label`)
so renaming or deleting the person later never rewrites history.

Deleting the diagram itself removes its log (cascade): the log describes that
diagram and has no meaning without it.
"""
from django.conf import settings
from django.db import models

from apps.organizations.models import TenantScopedManager, TenantScopedModel, TenantScopedQuerySet


class ImmutableLogError(RuntimeError):
    """Raised on any attempt to edit or delete a log entry."""

    def __init__(self) -> None:
        super().__init__("Log entries are append-only: they cannot be edited or deleted.")


class LogKind(models.TextChoices):
    CHANGE = "change", "Change"
    VERSION_RESTORED = "version.restored", "Version restored"
    DIAGRAM_REPLACED = "diagram.replaced", "Diagram replaced"
    PROPOSAL_CREATED = "proposal.created", "Proposal created"
    PROPOSAL_APPROVED = "proposal.approved", "Proposal approved"
    PROPOSAL_REJECTED = "proposal.rejected", "Proposal rejected"
    CHAT_MESSAGE = "chat.message", "Chat message"


class LogQuerySet(TenantScopedQuerySet):
    def update(self, **kwargs):
        # The one change Django itself makes: deleting a user account nulls
        # `actor` (SET_NULL). The author's name stays in `actor_label`, so the
        # history still says who did it. Nothing else, and never a reassignment.
        if kwargs and set(kwargs) <= {"actor", "actor_id"} and all(value is None for value in kwargs.values()):
            return super().update(**kwargs)
        raise ImmutableLogError()

    def bulk_update(self, objs, fields, batch_size=None):
        raise ImmutableLogError()

    def delete(self):
        raise ImmutableLogError()


class LogManager(TenantScopedManager):
    """The tenant-scoped manager, over the append-only queryset."""

    _queryset_class = LogQuerySet


class UnscopedLogManager(models.Manager):
    _queryset_class = LogQuerySet


class LogEntry(TenantScopedModel):
    id = models.BigAutoField(primary_key=True)
    document = models.ForeignKey(
        "uml_documents.UmlDocument", on_delete=models.CASCADE, related_name="log_entries"
    )
    # Numbered per diagram: a new one starts after a period of inactivity.
    session = models.PositiveIntegerField()
    kind = models.CharField(max_length=32, choices=LogKind.choices)
    # Null for the AI, for the system and for a person whose account was deleted.
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    actor_label = models.CharField(max_length=255)
    is_ai = models.BooleanField(default=False)
    summary = models.CharField(max_length=500)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField()

    objects = LogManager()
    all_objects = UnscopedLogManager()

    class Meta:
        base_manager_name = "all_objects"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["organization", "document", "id"]),
            models.Index(fields=["document", "session"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ImmutableLogError()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ImmutableLogError()
