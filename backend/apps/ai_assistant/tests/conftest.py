"""App-local pytest fixtures for `apps/ai_assistant`.

Mirrors `apps.uml_documents.tests.conftest`/`apps.relational_mapping.tests.conftest`'s
`auth_client` fixture.
"""
import pytest
from django.test import Client


@pytest.fixture
def auth_client() -> Client:
    return Client()
