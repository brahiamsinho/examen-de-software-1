"""Structural check: the app registers correctly and is discoverable.

Triangulation skipped: purely structural registration (AppConfig
attributes), no branching or logic to exercise.
"""
from django.apps import apps


def test_uml_modeling_app_is_registered():
    config = apps.get_app_config("uml_modeling")

    assert config.name == "apps.uml_modeling"
