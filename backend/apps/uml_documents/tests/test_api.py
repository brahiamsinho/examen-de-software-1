"""HTTP integration tests for `/api/orgs/{org_slug}/documents` (spec's
Document Creation, Document Read, Command Submission requirements).
"""
import pytest

from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents.models import UmlDocument


@pytest.mark.django_db
class TestCreateDocument:
    def test_editor_creates_empty_document(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        auth_client.force_login(editor)

        response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )

        assert response.status_code == 201
        body = response.json()
        assert body["revision"] == 1
        assert body["model"] == {
            "classes": [],
            "enumerations": [],
            "relationships": [],
            "generation_metadata": {},
        }
        assert body["layout"] == {"positions": {}}
        assert body["owner_id"] == str(editor.id)

    def test_viewer_is_denied_creation(self, auth_client):
        organization, _owner, _editor, viewer, _outsider = make_org_with_roles()
        auth_client.force_login(viewer)

        response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )

        assert response.status_code == 403
        assert not UmlDocument.all_objects.filter(organization=organization).exists()


@pytest.mark.django_db
class TestGetDocument:
    def test_any_member_reads_back_the_persisted_document(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        auth_client.force_login(owner)
        create_response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )
        doc_id = create_response.json()["id"]

        auth_client.force_login(viewer)
        response = auth_client.get(f"/api/orgs/{organization.slug}/documents/{doc_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["revision"] == 1
        assert body["id"] == doc_id

    def test_cross_tenant_read_returns_404(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        other_organization, other_owner, *_rest = make_org_with_roles()
        auth_client.force_login(owner)
        create_response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )
        doc_id = create_response.json()["id"]

        auth_client.force_login(other_owner)
        response = auth_client.get(f"/api/orgs/{other_organization.slug}/documents/{doc_id}")

        assert response.status_code == 404


@pytest.mark.django_db
class TestSubmitCommand:
    def test_sequential_commands_persist_across_calls(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        auth_client.force_login(editor)
        create_response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )
        doc_id = create_response.json()["id"]

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
        model = get_response.json()["model"]
        assert len(model["classes"]) == 1
        assert len(model["classes"][0]["attributes"]) == 1

    def test_viewer_is_denied_command_submission(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        auth_client.force_login(owner)
        create_response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )
        doc_id = create_response.json()["id"]

        auth_client.force_login(viewer)
        response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
            data={"type": "AddClass", "class_id": "c1", "name": "Order"},
            content_type="application/json",
        )

        assert response.status_code == 403
        document = UmlDocument.all_objects.get(id=doc_id)
        assert document.revision == 1

    def test_add_relationship_with_nonexistent_target_returns_violations(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        auth_client.force_login(editor)
        create_response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )
        doc_id = create_response.json()["id"]

        auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
            data={"type": "AddClass", "class_id": "c1", "name": "A"},
            content_type="application/json",
        )

        response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
            data={
                "type": "AddRelationship",
                "relationship": {
                    "id": "r1",
                    "kind": "association",
                    "source": {"class_id": "c1", "multiplicity": "1"},
                    "target": {"class_id": "does-not-exist", "multiplicity": "1"},
                },
            },
            content_type="application/json",
        )

        assert response.status_code == 200
        body = response.json()
        assert body["revision"] == 3
        codes = {violation["code"] for violation in body["validation"]["violations"]}
        assert "INVALID_RELATIONSHIP_ENDPOINT" in codes

    def test_malformed_attribute_type_returns_422_not_500(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        auth_client.force_login(editor)
        create_response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )
        doc_id = create_response.json()["id"]
        auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
            data={"type": "AddClass", "class_id": "c1", "name": "A"},
            content_type="application/json",
        )

        response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
            data={
                "type": "AddAttribute",
                "class_id": "c1",
                "attribute": {"id": "a1", "name": "bad", "type": {"not_a_valid_shape": True}},
            },
            content_type="application/json",
        )

        assert response.status_code == 422
        assert response.json()["code"] == "invalid_command_payload"
        document = UmlDocument.all_objects.get(id=doc_id)
        assert document.revision == 2

    def test_malformed_multiplicity_returns_422_not_500(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        auth_client.force_login(editor)
        create_response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )
        doc_id = create_response.json()["id"]
        auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
            data={"type": "AddClass", "class_id": "c1", "name": "A"},
            content_type="application/json",
        )
        auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
            data={"type": "AddClass", "class_id": "c2", "name": "B"},
            content_type="application/json",
        )

        response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{doc_id}/commands",
            data={
                "type": "AddRelationship",
                "relationship": {
                    "id": "r1",
                    "kind": "association",
                    "source": {"class_id": "c1", "multiplicity": "not-a-multiplicity"},
                    "target": {"class_id": "c2", "multiplicity": "1"},
                },
            },
            content_type="application/json",
        )

        assert response.status_code == 422
        assert response.json()["code"] == "invalid_command_payload"
        document = UmlDocument.all_objects.get(id=doc_id)
        assert document.revision == 3
