"""Django app registration shell for the UML command bus.

This app intentionally has no `models.py`: it is a pure, DB-free command
dispatch layer (dataclasses + functions) built on top of `apps.uml_modeling`.
Registration exists so the package is discoverable as a proper Django app,
matching `apps.uml_modeling`'s own registration shell.
"""
from django.apps import AppConfig


class UmlCommandsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.uml_commands"
    label = "uml_commands"
