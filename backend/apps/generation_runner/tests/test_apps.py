"""Structural check: the app registers correctly and is discoverable.

Triangulation skipped: purely structural registration (AppConfig
attributes), no branching or logic to exercise (mirrors
`spring_generator/tests/test_apps.py`).
"""
from django.apps import apps


def test_generation_runner_app_is_registered():
    config = apps.get_app_config("generation_runner")

    assert config.name == "apps.generation_runner"
    assert config.label == "generation_runner"
