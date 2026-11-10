"""App-local pytest fixtures for `apps/ai_assistant`.

Mirrors `apps.uml_documents.tests.conftest`/`apps.relational_mapping.tests.conftest`'s
`auth_client` fixture.
"""
import pytest
from django.test import Client

from apps.ai_assistant import memory


@pytest.fixture
def auth_client() -> Client:
    return Client()


@pytest.fixture(autouse=True)
def no_background_embeddings(monkeypatch):
    """The chat remembers messages in a background thread. A test must never start one
    (it could reach a real embeddings provider); the memory tests opt in explicitly."""
    monkeypatch.setattr(memory, "_run_in_background", lambda job: None)
