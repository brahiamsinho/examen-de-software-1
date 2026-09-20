"""Django app registration shell for the Postman export (design.md DD109).

This app has no `models.py` and no `migrations/`. `converter/` is a pure
stdlib package and `cli.py` a plain `__main__` module; neither imports Django
or the generator apps, and nothing imports this app. Registration keeps it
discoverable next to `apps.generation_runner`, one step later in the pipeline.
"""
from django.apps import AppConfig


class PostmanExportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.postman_export"
    label = "postman_export"
