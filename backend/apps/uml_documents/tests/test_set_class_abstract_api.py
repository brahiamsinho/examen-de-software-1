"""`POST .../commands` with `SetClassAbstract`: the web and the phone mark a class abstract."""
import json

import pytest
from django.test import Client
from django.utils import timezone

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import schemas, services
from apps.users.mobile_tokens import issue_mobile_token


def _bearer(user) -> dict:
    raw, _ = issue_mobile_token(user, device_name="test")
    return {"HTTP_AUTHORIZATION": f"Bearer {raw}"}


def _post(client, base, user, body):
    return client.post(f"{base}/commands", data=json.dumps(body), content_type="application/json", **_bearer(user))


@pytest.fixture
def setup():
    organization, owner, editor, viewer, _outsider = make_org_with_roles()
    document = services.create_document(organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now())
    command = services.command_from_payload(schemas.AddClassIn(type="AddClass", class_id="shape-1", name="Shape"))
    services.submit_commands(organization=organization, doc_id=document.id, commands_to_apply=[command], now=timezone.now())
    base = f"/api/orgs/{organization.slug}/documents/{document.id}"
    return Client(), base, editor, viewer


@pytest.mark.django_db
def test_an_editor_marks_a_class_abstract_and_the_document_shows_it(setup):
    client, base, editor, _viewer = setup

    response = _post(client, base, editor, {"type": "SetClassAbstract", "class_id": "shape-1", "is_abstract": True})

    assert response.status_code == 200
    stored = client.get(base, **_bearer(editor)).json()["model"]["classes"][0]
    assert stored["name"] == "Shape" and stored["is_abstract"] is True


@pytest.mark.django_db
def test_a_viewer_cannot_change_it(setup):
    client, base, _editor, viewer = setup

    response = _post(client, base, viewer, {"type": "SetClassAbstract", "class_id": "shape-1", "is_abstract": True})

    assert response.status_code == 403


@pytest.mark.django_db
def test_the_flag_is_required(setup):
    client, base, editor, _viewer = setup

    assert _post(client, base, editor, {"type": "SetClassAbstract", "class_id": "shape-1"}).status_code == 422
