"""Django app registration shell for the UML document persistence layer.

Mirrors `apps.uml_modeling`/`apps.uml_commands`'s own registration shell
(design.md's File Changes table).
"""
from django.apps import AppConfig


class UmlDocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.uml_documents"
    label = "uml_documents"
