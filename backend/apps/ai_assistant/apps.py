"""Django app registration shell for the ai_assistant domain (voice-driven
diagram editing).

Mirrors `apps.relational_mapping.apps`: a persisted-looking Django app with
no `models.py` of its own (it never touches the database directly — every
mutation flows through `apps.uml_documents.services.submit_command`).
"""
from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ai_assistant"
    label = "ai_assistant"
