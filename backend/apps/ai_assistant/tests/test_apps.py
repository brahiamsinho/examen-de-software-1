"""Structural check: the app registers correctly and is discoverable.
Mirrors `apps.uml_documents.tests.test_apps`.
"""
from django.apps import apps


def test_ai_assistant_app_is_registered():
    config = apps.get_app_config("ai_assistant")

    assert config.name == "apps.ai_assistant"
