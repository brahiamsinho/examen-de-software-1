"""HTTP tests for `POST .../documents/import-xmi` and `GET .../documents/{id}/export-xmi`."""
import pathlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.organizations.tests.factories import make_org_with_roles

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "ea-basico.xml"


def _import(client, organization, content: bytes, name="ea-basico.xml"):
    return client.post(
        f"/api/orgs/{organization.slug}/documents/import-xmi",
        {"file": SimpleUploadedFile(name, content, content_type="application/xml")},
    )


@pytest.mark.django_db
class TestImportXmi:
    def test_editor_imports_the_ea_sample_and_gets_a_document_with_warnings(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        auth_client.force_login(editor)

        response = _import(auth_client, organization, FIXTURE.read_bytes())

        assert response.status_code == 201
        body = response.json()
        assert body["metadata"]["name"] == "Basic Class Diagram with Multiplicities"
        assert sorted(c["name"] for c in body["model"]["classes"]) == ["Class A", "Class B"]
        assert len(body["layout"]["positions"]) == 2
        assert isinstance(body["warnings"], list)
        # The new document is a real, listable document.
        fetched = auth_client.get(f"/api/orgs/{organization.slug}/documents/{body['id']}")
        assert fetched.status_code == 200 and fetched.json()["revision"] == 1

    def test_viewer_cannot_import(self, auth_client):
        organization, _owner, _editor, viewer, _outsider = make_org_with_roles()
        auth_client.force_login(viewer)

        assert _import(auth_client, organization, FIXTURE.read_bytes()).status_code == 403

    @pytest.mark.parametrize(
        "content, code",
        [(b"definitely not xml", "invalid_xmi"), (b"<html/>", "unsupported_xmi")],
    )
    def test_garbage_is_a_422_with_a_stable_code(self, auth_client, content, code):
        organization, owner, *_ = make_org_with_roles()
        auth_client.force_login(owner)

        response = _import(auth_client, organization, content)

        assert response.status_code == 422
        assert response.json()["code"] == code and response.json()["detail"]


@pytest.mark.django_db
class TestExportXmi:
    def test_any_member_downloads_the_document_as_an_xml_attachment(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        auth_client.force_login(owner)
        doc_id = _import(auth_client, organization, FIXTURE.read_bytes()).json()["id"]

        auth_client.force_login(viewer)  # read-only member is enough
        response = auth_client.get(f"/api/orgs/{organization.slug}/documents/{doc_id}/export-xmi")

        assert response.status_code == 200
        assert response["Content-Type"] == "application/xml"
        assert response["Content-Disposition"] == 'attachment; filename="basic-class-diagram-with-multiplicities.xml"'
        assert b"Class A" in response.content and b"UML:Association" in response.content

    def test_outsider_gets_no_access(self, auth_client):
        organization, owner, _editor, _viewer, outsider = make_org_with_roles()
        auth_client.force_login(owner)
        doc_id = _import(auth_client, organization, FIXTURE.read_bytes()).json()["id"]

        auth_client.force_login(outsider)
        response = auth_client.get(f"/api/orgs/{organization.slug}/documents/{doc_id}/export-xmi")

        assert response.status_code in (403, 404)
