"""Structural check: the app registers correctly and is discoverable.

Triangulation skipped: purely structural registration (AppConfig
attributes), no branching or logic to exercise. Mirrors
`apps.uml_modeling`'s own `test_apps.py`.
"""
from django.apps import apps


def test_uml_commands_app_is_registered():
    config = apps.get_app_config("uml_commands")

    assert config.name == "apps.uml_commands"
