"""Structural check: the app registers correctly and is discoverable.

Mirrors `apps.uml_commands`'s own `test_apps.py`. Not a true RED/GREEN
pair: task 1.1 already had to create and register `apps.py` (it is a
prerequisite for every other requirement in this app), so this test is
expected to pass on first run, same convention as the Phase 6
import-boundary test.
"""
from django.apps import apps


def test_uml_documents_app_is_registered():
    config = apps.get_app_config("uml_documents")

    assert config.name == "apps.uml_documents"
