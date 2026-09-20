import pytest
from django.test import Client


@pytest.fixture
def auth_client() -> Client:
    return Client()
