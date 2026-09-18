"""Django app registration shell for the relational-mapping domain.

This app intentionally has no `models.py`: the whole cycle is a pure,
DB-free domain layer (dataclasses) plus a pure mapper function.
Registration exists so the package is discoverable as a proper Django
app for future cycles (§22 generator, persistence) without a breaking
restructure, mirroring `apps.uml_modeling` (DD1).
"""
from django.apps import AppConfig


class RelationalMappingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.relational_mapping"
    label = "relational_mapping"
