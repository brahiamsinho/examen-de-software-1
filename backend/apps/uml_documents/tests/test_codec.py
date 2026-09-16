"""Codec round-trip correctness (spec: Codec Round-Trip Correctness).

Encoding a non-trivial `CanonicalUmlModel`/`DiagramLayout` fixture to JSON
and decoding it back must yield a value equal to the original, including
`ElementId`-keyed mappings and nested tuple structure, and both
`AttributeType` branches.
"""
import datetime

import pytest

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import codec, services
from apps.uml_documents.schemas import DocumentOut
from apps.uml_documents.tests.factories import a_layout, a_metadata, a_model
from apps.uml_modeling.documents import DiagramLayout, ProjectMetadata
from apps.uml_modeling.domain.model import CanonicalUmlModel


def test_round_trips_non_trivial_fixture_exactly():
    metadata = a_metadata()
    model = a_model()
    layout = a_layout(model)

    data = codec.to_json(metadata, model, layout)
    decoded_metadata, decoded_model, decoded_layout = codec.from_json(data)

    assert decoded_metadata == metadata
    assert decoded_model == model
    assert decoded_layout == layout


@pytest.mark.django_db
def test_document_out_matches_get_response_byte_for_byte():
    """Pin/golden test (design.md DD6, tasks 2.4/2.5): `codec.document_out`
    must produce EXACTLY what `GET .../documents/{doc_id}` returns, since
    the WS broadcast payload (task 2.7) reuses this same function. Written
    against today's `api._document_out` before the promotion in 2.5, then
    re-run unchanged afterwards to confirm the promoted function still
    matches byte-for-byte.
    """
    from django.test import Client

    organization, owner, *_rest = make_org_with_roles()
    document = services.create_document(
        organization=organization,
        owner_id=str(owner.id),
        name="Pin Fixture",
        now=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
    )

    auth_client = Client()
    auth_client.force_login(owner)
    response = auth_client.get(f"/api/orgs/{organization.slug}/documents/{document.id}")
    assert response.status_code == 200

    persisted = services.get_document(organization=organization, doc_id=document.id)
    computed = DocumentOut.model_validate(codec.document_out(persisted)).model_dump(mode="json")

    assert computed == response.json()


def test_round_trips_generation_metadata_keys_and_values():
    model = a_model()
    data = codec.to_json(a_metadata(), model, DiagramLayout())
    _metadata, decoded_model, _layout = codec.from_json(data)

    assert set(decoded_model.generation_metadata.keys()) == set(model.generation_metadata.keys())
    for key, value in model.generation_metadata.items():
        assert decoded_model.generation_metadata[key] == value


def test_round_trips_primitive_and_enumeration_ref_attribute_types():
    model = a_model()
    data = codec.to_json(a_metadata(), model, DiagramLayout())
    _metadata, decoded_model, _layout = codec.from_json(data)

    order_class = decoded_model.class_by_id(model.classes[0].id)
    original_order_class = model.classes[0]
    assert order_class is not None
    assert order_class.attributes == original_order_class.attributes


def test_round_trips_empty_collections():
    metadata = ProjectMetadata(name="Empty")
    model = CanonicalUmlModel()
    layout = DiagramLayout()

    data = codec.to_json(metadata, model, layout)
    decoded_metadata, decoded_model, decoded_layout = codec.from_json(data)

    assert decoded_metadata == metadata
    assert decoded_model == model
    assert decoded_layout == layout
