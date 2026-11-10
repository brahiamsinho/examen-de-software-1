"""Django app registration for the multi-tenant organizations domain."""
from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"
    name = "apps.organizations"
    label = "organizations"
