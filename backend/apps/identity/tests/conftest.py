"""App-local pytest fixtures for `apps/identity`.

No global `backend/conftest.py` is added, so `apps/uml_modeling`'s DB-free
suite stays DB-free (matches design.md's stated test-file split).

`csrf_client` / `auth_client` are prepared here for the later PRs (API
tests) that need them; they need no `api.py` to exist yet, since they are
just plain `django.test.Client` wrappers.
"""
import pytest
from django.test import Client

from apps.identity.tests.factories import make_org_with_roles, make_user


@pytest.fixture
def csrf_client() -> Client:
    return Client(enforce_csrf_checks=True)


@pytest.fixture
def auth_client() -> Client:
    return Client()


@pytest.fixture
def organization(db):
    org, owner_user, editor_user, viewer_user, outsider_user = make_org_with_roles()
    return org


@pytest.fixture
def owner(db, organization):
    return organization.memberships.get(role="OWNER").user


@pytest.fixture
def member(db, organization):
    return organization.memberships.get(role="EDITOR").user


@pytest.fixture
def outsider(db):
    return make_user()
