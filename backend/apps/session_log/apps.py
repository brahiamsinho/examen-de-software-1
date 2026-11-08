"""Django app registration shell for the per-diagram session log (issue #17).

A low-level, tenant-scoped app: it depends only on `apps.organizations` (and,
for the description of commands, `apps.uml_commands`). The apps that change a
diagram call `services.record(...)`, never the other way around, so the log can
be consulted without importing any feature app.
"""
from django.apps import AppConfig


class SessionLogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.session_log"
    label = "session_log"
