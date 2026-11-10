"""The events that become a push. Called from `on_commit`, so a rolled-back
change never notifies, and written never to raise."""
import logging

from apps.notifications import service
from apps.organizations.models import Organization
from apps.uml_documents.models import UmlDocument

logger = logging.getLogger(__name__)


def _name(document) -> str:
    # The AI path hands over the domain document (.metadata.name); the change
    # path hands over the stored row (data["metadata"]["name"]).
    metadata = getattr(document, "metadata", None)
    if metadata is None:
        metadata = (getattr(document, "data", None) or {}).get("metadata") or {}
    name = metadata.get("name") if isinstance(metadata, dict) else getattr(metadata, "name", None)
    return name or "Diagrama"


def on_proposal_created(sender, *, organization, document, requested_by_id, **kwargs) -> None:
    """The AI left a draft. The person who asked already knows, so they are skipped."""
    try:
        service.notify_organization(
            organization_id=organization.id,
            exclude_user_id=requested_by_id,
            title="Nueva propuesta de la IA",
            body=f"La IA dejó una propuesta en «{_name(document)}» para revisar.",
            data={
                "type": "proposal",
                "organization_slug": organization.slug,
                "document_id": str(document.id),
            },
        )
    except Exception:  # noqa: BLE001 - a push must never break the request
        logger.exception("proposal push failed")


def on_document_changed(sender, *, document, **kwargs) -> None:
    """A diagram changed. At most one push per diagram per minute."""
    try:
        if not service.document_push_allowed(document.id):
            return
        # The broadcast carries the domain document, which does not know its
        # organization, so look it up from the stored row.
        organization_id = UmlDocument.all_objects.filter(pk=document.id).values_list("organization_id", flat=True).first()
        if organization_id is None:
            return
        slug = Organization.objects.filter(pk=organization_id).values_list("slug", flat=True).first()
        service.notify_organization(
            organization_id=organization_id,
            title="Diagrama actualizado",
            body=f"«{_name(document)}» tiene cambios nuevos.",
            data={"type": "document", "organization_slug": slug or "", "document_id": str(document.id)},
        )
    except Exception:  # noqa: BLE001 - a push must never break the request
        logger.exception("document push failed")
