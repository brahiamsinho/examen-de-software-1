"""Django app registration shell for the ai_assistant domain (voice-driven
diagram editing).

Voice and image plans stay in the cache and never touch the database. Only
AI board proposals (`models.AiProposal`, issue #15) are persisted, because
they must outlive a request and be visible to every collaborator. Every
change to a diagram still flows through
`apps.uml_documents.services.submit_commands`.
"""
from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_assistant"
    label = "ai_assistant"
