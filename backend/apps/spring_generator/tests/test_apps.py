"""Structural check: the app registers correctly and is discoverable.

Triangulation skipped: purely structural registration (AppConfig
attributes), no branching or logic to exercise (mirrors
`relational_mapping/tests/test_apps.py`).
"""
from django.apps import apps


def test_spring_generator_app_is_registered():
    config = apps.get_app_config("spring_generator")

    assert config.name == "apps.spring_generator"
    assert config.label == "spring_generator"
