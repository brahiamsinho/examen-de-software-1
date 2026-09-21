"""Django app registration shell for the running-backend deployments domain.

Django never talks to Docker here: it stores the deployment row and calls the
separate `runner` service over HTTP (`runner_client.py`).
"""
from django.apps import AppConfig


class BackendDeploymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.backend_deployments"
    label = "backend_deployments"
