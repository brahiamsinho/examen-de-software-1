"""Django app registration for the user-identity domain.

The explicit `label = "users"` is what makes `AUTH_USER_MODEL = "users.User"`
resolvable — Django derives the default label from the last component of
`name`, which would already be `users` here, but the label is set
explicitly so the string never silently drifts if the package is ever
renamed.
"""
from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"
