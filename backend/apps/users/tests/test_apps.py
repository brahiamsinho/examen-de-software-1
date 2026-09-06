"""Structural check: the users app is registered with the exact label
`users` (this is what makes `AUTH_USER_MODEL = "users.User"` resolvable).

Triangulation skipped: purely structural registration (AppConfig
attributes), no branching or logic to exercise.
"""
from django.apps import apps


def test_users_app_is_registered_with_expected_label():
    config = apps.get_app_config("users")

    assert config.name == "apps.users"
    assert config.label == "users"
