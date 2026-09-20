"""HTTP tests for `GET /api/orgs/{org_slug}/documents/{doc_id}/generate`."""
import io
import zipfile
from uuid import uuid4

import pytest

from apps.organizations.tests.factories import make_org_with_roles


def _create_document(client, organization, user, *, name="Sales Demo") -> str:
    client.force_login(user)
    response = client.post(
        f"/api/orgs/{organization.slug}/documents",
        data={"name": name},
        content_type="application/json",
    )
    return response.json()["id"]


def _add_class(client, organization, doc_id, *, name="Order", class_id="c1"):
    base = f"/api/orgs/{organization.slug}/documents/{doc_id}/commands"
    client.post(
        base,
        data={"type": "AddClass", "class_id": class_id, "name": name},
        content_type="application/json",
    )
    client.post(
        base,
        data={
            "type": "AddAttribute",
            "class_id": class_id,
            "attribute": {"id": f"{class_id}-a", "name": "reference", "type": "String"},
        },
        content_type="application/json",
    )


def _url(organization, doc_id) -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/generate"


@pytest.mark.django_db
class TestGenerateBackend:
    def test_member_downloads_a_zip_with_attachment_headers(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        _add_class(auth_client, organization, doc_id)

        auth_client.force_login(viewer)  # read-only member is enough
        response = auth_client.get(_url(organization, doc_id))

        assert response.status_code == 200
        assert response["Content-Type"] == "application/zip"
        assert response["Content-Disposition"] == 'attachment; filename="sales-demo-backend.zip"'
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            names = archive.namelist()
        assert "sales-demo/build.gradle" in names
        assert any(name.endswith("/Order.java") for name in names)

    def test_anonymous_user_gets_401(self, auth_client):
        organization, *_rest = make_org_with_roles()

        response = auth_client.get(_url(organization, uuid4()))

        assert response.status_code == 401

    def test_non_member_gets_404_like_the_document_endpoints(self, auth_client):
        organization, owner, _editor, _viewer, outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        _add_class(auth_client, organization, doc_id)

        auth_client.force_login(outsider)
        response = auth_client.get(_url(organization, doc_id))

        assert response.status_code == 404

    def test_cross_tenant_document_gets_404(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        other_organization, other_owner, *_rest = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)

        auth_client.force_login(other_owner)
        response = auth_client.get(_url(other_organization, doc_id))

        assert response.status_code == 404

    def test_unknown_document_gets_404(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        auth_client.force_login(owner)

        response = auth_client.get(_url(organization, uuid4()))

        assert response.status_code == 404

    def test_document_without_classes_gets_422_nothing_to_generate(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)

        response = auth_client.get(_url(organization, doc_id))

        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "nothing_to_generate"
        assert body["detail"]

    def test_class_name_with_spaces_gets_422_generation_failed(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        _add_class(auth_client, organization, doc_id, name="Order Item")

        response = auth_client.get(_url(organization, doc_id))

        assert response.status_code == 422
        body = response.json()
        assert body["code"] == "generation_failed"
        assert isinstance(body["detail"], str) and body["detail"]
        assert "Traceback" not in body["detail"]
