"""Django app registration for the multi-tenant identity domain.

The explicit `label = "identity"` is what makes `AUTH_USER_MODEL =
"identity.User"` resolvable — Django derives the default label from the
last component of `name`, which would already be `identity` here, but the
label is set explicitly so the string never silently drifts if the package
is ever renamed.
"""
from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.identity"
    label = "identity"
