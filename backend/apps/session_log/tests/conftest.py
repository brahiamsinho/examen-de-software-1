"""App-local pytest fixtures for `apps/session_log`.

Mirrors `apps.ai_assistant.tests.conftest`'s `auth_client` fixture.
"""
import pytest
from django.test import Client


@pytest.fixture
def auth_client() -> Client:
    return Client()
