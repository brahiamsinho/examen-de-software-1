"""Django app registration shell for the Enterprise Architect XMI import/export domain.

No `models.py` and no `migrations/`: the import produces a `CanonicalUmlModel`
(persisted through `uml_documents`) and the export renders a stored document.
"""
from django.apps import AppConfig


class XmiInteropConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.xmi_interop"
    label = "xmi_interop"
