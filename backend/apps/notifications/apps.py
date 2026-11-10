"""Django app registration for push notifications (GitHub #19)."""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "apps.notifications"
    label = "notifications"

    def ready(self) -> None:
        from apps.ai_assistant.signals import proposal_created
        from apps.notifications import triggers
        from apps.uml_documents.signals import document_changed

        proposal_created.connect(triggers.on_proposal_created, dispatch_uid="push-on-proposal-created")
        document_changed.connect(triggers.on_document_changed, dispatch_uid="push-on-document-changed")
