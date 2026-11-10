"""Django app registration shell for the generated-backend export domain.

No `models.py` and no `migrations/`: this app only composes the existing
pipeline (mapping -> generator) over a stored document and packs the result.
"""
from django.apps import AppConfig


class GenerationExportConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "apps.generation_export"
    label = "generation_export"
