"""App-local pytest fixtures for `apps/users`.

No global `backend/conftest.py` is added, so `apps/uml_modeling`'s DB-free
suite stays DB-free (matches design.md's stated test-file split).
"""
import pytest
from django.test import Client


@pytest.fixture
def csrf_client() -> Client:
    return Client(enforce_csrf_checks=True)


@pytest.fixture
def auth_client() -> Client:
    return Client()
