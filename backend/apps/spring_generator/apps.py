"""Django app registration shell for the Spring Boot generator (design.md DD1).

This app intentionally has no `models.py` and no `migrations/`: the
whole slice is a pure, DB-free, filesystem-free module that turns a
`relational_mapping.domain.schema.Table` into in-memory Java source
text (`domain/` output shape + `emit/` algorithm). Registration exists
so the package is discoverable as a proper Django app, mirroring
`apps.relational_mapping` one cycle later in the same pipeline.
"""
from django.apps import AppConfig


class SpringGeneratorConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.spring_generator"
    label = "spring_generator"
