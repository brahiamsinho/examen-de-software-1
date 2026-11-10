"""Dependency through the codec and the HTTP command API."""
import json

import pytest
from django.test import Client
from django.utils import timezone

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import codec, schemas, services
from apps.uml_documents.tests.factories import a_metadata
from apps.uml_modeling.documents import DiagramLayout
from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.tests.factories import a_class, a_relationship, a_relationship_end
from apps.users.mobile_tokens import issue_mobile_token


def test_a_dependency_round_trips_through_the_codec():
    client, supplier = a_class(name="Pedido"), a_class(name="Calculadora")
    dependency = a_relationship(
        kind=RelationshipKind.DEPENDENCY,
        source=a_relationship_end(class_id=client.id),
        target=a_relationship_end(class_id=supplier.id),
    )
    model = CanonicalUmlModel(classes=(client, supplier), relationships=(dependency,))

    _, decoded, _ = codec.from_json(codec.to_json(a_metadata(), model, DiagramLayout()))

    assert decoded == model


def _bearer(user) -> dict:
    raw, _ = issue_mobile_token(user, device_name="test")
    return {"HTTP_AUTHORIZATION": f"Bearer {raw}"}


@pytest.fixture
def setup():
    organization, owner, editor, *_ = make_org_with_roles()
    document = services.create_document(organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now())
    for class_id, name in (("c-client", "Pedido"), ("c-supplier", "Calculadora")):
        command = services.command_from_payload(schemas.AddClassIn(type="AddClass", class_id=class_id, name=name))
        services.submit_commands(organization=organization, doc_id=document.id, commands_to_apply=[command], now=timezone.now())
    return Client(), f"/api/orgs/{organization.slug}/documents/{document.id}", editor


def _post(client, base, user, body):
    return client.post(f"{base}/commands", data=json.dumps(body), content_type="application/json", **_bearer(user))


def _dependency_body(**extra):
    relationship = {
        "id": "dep-1",
        "kind": "dependency",
        "source": {"class_id": "c-client", "multiplicity": "1"},
        "target": {"class_id": "c-supplier", "multiplicity": "1"},
    }
    return {"type": "AddRelationship", "relationship": {**relationship, **extra}}


@pytest.mark.django_db
def test_a_dependency_can_be_added_over_http_and_is_returned_as_a_dependency(setup):
    client, base, editor = setup

    response = _post(client, base, editor, _dependency_body())

    assert response.status_code == 200
    stored = client.get(base, **_bearer(editor)).json()["model"]["relationships"]
    assert [(item["kind"], item["source"]["class_id"], item["target"]["class_id"]) for item in stored] == [
        ("dependency", "c-client", "c-supplier")
    ]


@pytest.mark.django_db
def test_a_dependency_has_no_multiplicities_to_edit(setup):
    client, base, editor = setup
    _post(client, base, editor, _dependency_body())

    response = _post(
        client, base, editor, {"type": "UpdateRelationship", "relationship_id": "dep-1", "source_multiplicity": "0..*"}
    )

    assert response.status_code == 422


@pytest.mark.django_db
def test_a_dependency_can_still_be_renamed(setup):
    client, base, editor = setup
    _post(client, base, editor, _dependency_body())

    response = _post(client, base, editor, {"type": "UpdateRelationship", "relationship_id": "dep-1", "name": "usa"})

    assert response.status_code == 200
