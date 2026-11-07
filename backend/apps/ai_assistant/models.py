"""Persistence for AI board proposals (issue #15).

An `AiProposal` is a draft the AI suggested for one diagram. It stores the
function calls the model chose (`calls`) and their human-readable description
(`changes`), never the resulting document: the diagram only changes when a
developer approves the proposal, through the normal command pipeline.
"""
import uuid

from django.conf import settings
from django.db import models

from apps.organizations.models import TenantScopedManager, TenantScopedModel


class ProposalStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    STALE = "stale", "Stale"


class AiProposal(TenantScopedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "uml_documents.UmlDocument", on_delete=models.CASCADE, related_name="ai_proposals"
    )
    prompt = models.TextField(blank=True, default="")
    base_revision = models.PositiveIntegerField()
    calls = models.JSONField(default=list)
    changes = models.JSONField(default=list)
    # Which of `calls` the approver chose to apply (None until decided or when rejected).
    applied_indices = models.JSONField(null=True, default=None)
    status = models.CharField(
        max_length=16, choices=ProposalStatus.choices, default=ProposalStatus.PENDING
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True)

    objects = TenantScopedManager()
    all_objects = models.Manager()

    class Meta:
        base_manager_name = "all_objects"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["organization", "document", "status"])]
