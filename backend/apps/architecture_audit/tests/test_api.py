from uuid import uuid4

import pytest

from apps.organizations.tests.factories import make_org_with_roles


def _create_document(client, organization, user) -> str:
    client.force_login(user)
    response = client.post(f"/api/orgs/{organization.slug}/documents", data={"name": "Audit"}, content_type="application/json")
    return response.json()["id"]


def _add_class(client, organization, doc_id: str, class_id: str, name: str) -> None:
    response = client.post(
        f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
        data={"type": "AddClass", "class_id": class_id, "name": name}, content_type="application/json",
    )
    assert response.status_code == 200


def _url(organization, doc_id: str) -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/architecture-audit"


@pytest.mark.django_db
class TestArchitectureAuditApi:
    def test_viewer_reads_a_stable_report_without_modifying_the_document(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        _add_class(auth_client, organization, doc_id, "alone", "Alone")
        before = auth_client.get(f"/api/orgs/{organization.slug}/documents/{doc_id}").json()

        auth_client.force_login(viewer)
        first = auth_client.get(_url(organization, doc_id))
        second = auth_client.get(_url(organization, doc_id))

        assert first.status_code == 200
        assert first.json() == second.json()
        assert first.json()["summary"] == {"ERROR": 0, "WARNING": 0, "INFO": 1}
        assert first.json()["findings"][0]["element_ids"] == ["alone"]
        assert auth_client.get(f"/api/orgs/{organization.slug}/documents/{doc_id}").json() == before

    def test_non_member_cannot_read_or_export_another_organization_document(self, auth_client):
        organization, owner, _editor, _viewer, outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        auth_client.force_login(outsider)

        assert auth_client.get(_url(organization, doc_id)).status_code == 404
        assert auth_client.get(f"{_url(organization, doc_id)}/export?format=json").status_code == 404

    def test_exports_json_and_markdown_for_an_authorized_member(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(auth_client, organization, owner)
        auth_client.force_login(viewer)

        json_response = auth_client.get(f"{_url(organization, doc_id)}/export?format=json")
        markdown_response = auth_client.get(f"{_url(organization, doc_id)}/export?format=markdown")

        assert json_response.status_code == 200
        assert json_response["Content-Type"].startswith("application/json")
        assert json_response.json()["document"]["id"] == doc_id
        assert markdown_response.status_code == 200
        assert "Auditoria arquitectonica" in markdown_response.content.decode()

    def test_anonymous_user_gets_401(self, auth_client):
        organization, *_rest = make_org_with_roles()
        assert auth_client.get(_url(organization, uuid4())).status_code == 401
