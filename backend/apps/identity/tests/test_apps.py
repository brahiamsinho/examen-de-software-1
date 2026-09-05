"""Structural check: the identity app is registered with the exact label
`identity` (this is what makes `AUTH_USER_MODEL = "identity.User"` resolvable).

Triangulation skipped: purely structural registration (AppConfig
attributes), no branching or logic to exercise.
"""
from django.apps import apps


def test_identity_app_is_registered_with_expected_label():
    config = apps.get_app_config("identity")

    assert config.name == "apps.identity"
    assert config.label == "identity"
