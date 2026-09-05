"""Django app registration shell for the UML modeling domain.

This app intentionally has no `models.py`: Cycle 1 is a pure, DB-free
domain layer (dataclasses only). Registration exists so the package is
discoverable as a proper Django app for future cycles (persistence,
API wiring) without a breaking restructure.
"""
from django.apps import AppConfig


class UmlModelingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.uml_modeling"
    label = "uml_modeling"
