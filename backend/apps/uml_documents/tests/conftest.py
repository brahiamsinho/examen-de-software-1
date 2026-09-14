"""App-local pytest fixtures for `apps/uml_documents`.

Mirrors `apps.organizations.tests.conftest`'s `auth_client` fixture.
Organization/membership fixtures are built inline via
`apps.organizations.tests.factories.make_org_with_roles` — a normal
cross-app test import, matching that factory module's own precedent of
importing `apps.users.tests.factories.make_user`.
"""
import pytest
from django.test import Client


@pytest.fixture
def auth_client() -> Client:
    return Client()
