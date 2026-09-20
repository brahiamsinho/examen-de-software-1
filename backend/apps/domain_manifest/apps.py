"""Django app registration shell (design.md DD121).

No `models.py`, no `migrations/`. `builder/` and `serialize.py` are pure and
import only `apps.spring_generator.emit.naming`; `cli.py` is a plain
`__main__` module. Nothing imports this app.
"""
from django.apps import AppConfig


class DomainManifestConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.domain_manifest"
    label = "domain_manifest"
