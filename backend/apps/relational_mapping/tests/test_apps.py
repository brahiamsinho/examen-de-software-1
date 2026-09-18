"""Structural check: the app registers correctly and is discoverable.

Triangulation skipped: purely structural registration (AppConfig
attributes), no branching or logic to exercise.
"""
from django.apps import apps


def test_relational_mapping_app_is_registered():
    config = apps.get_app_config("relational_mapping")

    assert config.name == "apps.relational_mapping"
