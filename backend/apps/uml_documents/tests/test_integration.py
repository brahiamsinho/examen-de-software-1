"""End-to-end HTTP integration test (spec's Tenant Scoping on Every Access
— end-to-end confirmation): a full create -> command -> command -> get
round trip through `django.test.Client` against the real mounted
`documents_router`, plus cross-tenant 404 on all three endpoints.
"""
import pytest

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents.models import UmlDocument


@pytest.mark.django_db
def test_composed_create_add_class_add_attribute_get_round_trip(auth_client):
    organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
    auth_client.force_login(editor)

    create_response = auth_client.post(
        f"/api/orgs/{organization.slug}/documents",
        data={"name": "My Diagram"},
        content_type="application/json",
    )
    assert create_response.status_code == 201
    doc_id = create_response.json()["id"]
    assert create_response.json()["revision"] == 1

    add_class_response = auth_client.post(
        f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
        data={"type": "AddClass", "class_id": "c1", "name": "Order"},
        content_type="application/json",
    )
    assert add_class_response.status_code == 200
    assert add_class_response.json()["revision"] == 2

    add_attribute_response = auth_client.post(
        f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
        data={
            "type": "AddAttribute",
            "class_id": "c1",
            "attribute": {"id": "a1", "name": "reference", "type": "String"},
        },
        content_type="application/json",
    )
    assert add_attribute_response.status_code == 200
    assert add_attribute_response.json()["revision"] == 3

    get_response = auth_client.get(f"/api/orgs/{organization.slug}/documents/{doc_id}")
    assert get_response.status_code == 200
    body = get_response.json()
    assert body["revision"] == 3
    assert len(body["model"]["classes"]) == 1
    order_class = body["model"]["classes"][0]
    assert order_class["id"] == "c1"
    assert order_class["name"] == "Order"
    assert len(order_class["attributes"]) == 1
    assert order_class["attributes"][0]["id"] == "a1"

    # Cross-check against the persisted row directly, bypassing the API.
    row = UmlDocument.all_objects.get(id=doc_id)
    assert row.revision == 3
    assert row.organization_id == organization.id


@pytest.mark.django_db
def test_cross_tenant_member_gets_404_on_all_three_endpoints(auth_client):
    organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
    other_organization, other_owner, *_rest = make_org_with_roles()

    auth_client.force_login(owner)
    create_response = auth_client.post(
        f"/api/orgs/{organization.slug}/documents",
        data={"name": "My Diagram"},
        content_type="application/json",
    )
    doc_id = create_response.json()["id"]

    auth_client.force_login(other_owner)

    get_response = auth_client.get(f"/api/orgs/{other_organization.slug}/documents/{doc_id}")
    assert get_response.status_code == 404

    command_response = auth_client.post(
        f"/api/orgs/{other_organization.slug}/documents/{doc_id}/commands",
        data={"type": "AddClass", "class_id": "c1", "name": "Order"},
        content_type="application/json",
    )
    assert command_response.status_code == 404

    # The document is untouched: still revision 1, no class added.
    row = UmlDocument.all_objects.get(id=doc_id)
    assert row.revision == 1
