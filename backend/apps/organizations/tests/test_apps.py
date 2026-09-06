"""Structural check: the organizations app is registered with the exact
label `organizations`.

Triangulation skipped: purely structural registration (AppConfig
attributes), no branching or logic to exercise.
"""
from django.apps import apps


def test_organizations_app_is_registered_with_expected_label():
    config = apps.get_app_config("organizations")

    assert config.name == "apps.organizations"
    assert config.label == "organizations"
