"""Django's own apps with MongoDB ObjectId primary keys.

MongoDB's backend needs every model to use `ObjectIdAutoField`. Django's admin,
auth and contenttypes declare their own `default_auto_field`, so each gets a
subclass that overrides it (see `INSTALLED_APPS` in settings.py).
"""

from django.contrib.admin.apps import AdminConfig
from django.contrib.auth.apps import AuthConfig
from django.contrib.contenttypes.apps import ContentTypesConfig


class MongoAdminConfig(AdminConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


class MongoAuthConfig(AuthConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"


class MongoContentTypesConfig(ContentTypesConfig):
    default_auto_field = "django_mongodb_backend.fields.ObjectIdAutoField"