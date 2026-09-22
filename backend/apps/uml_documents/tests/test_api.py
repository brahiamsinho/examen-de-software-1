"""HTTP integration tests for `/api/orgs/{org_slug}/documents` (spec's
Document Creation, Document Read, Command Submission requirements).
"""
from unittest import mock

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
class TestListDocuments:
    def test_viewer_lists_documents_for_their_organization(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        auth_client.force_login(owner)
        auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "First"},
            content_type="application/json",
        )
        second_response = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "Second"},
            content_type="application/json",
        )
        second_id = second_response.json()["id"]

        auth_client.force_login(viewer)
        response = auth_client.get(f"/api/orgs/{organization.slug}/documents")

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert body[0]["id"] == second_id
        for item in body:
            assert set(item.keys()) == {"id", "name", "revision", "updated_at"}

    def test_owner_and_editor_can_also_list(self, auth_client):
        organization, owner, editor, _viewer, _outsider = make_org_with_roles()
        auth_client.force_login(owner)
        auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )

        owner_response = auth_client.get(f"/api/orgs/{organization.slug}/documents")
        assert owner_response.status_code == 200
        assert len(owner_response.json()) == 1

        auth_client.force_login(editor)
        editor_response = auth_client.get(f"/api/orgs/{organization.slug}/documents")
        assert editor_response.status_code == 200
        assert len(editor_response.json()) == 1

    def test_cross_tenant_documents_are_absent_not_404(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        other_organization, other_owner, *_rest = make_org_with_roles()
        auth_client.force_login(owner)
        auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        )

        auth_client.force_login(other_owner)
        response = auth_client.get(f"/api/orgs/{other_organization.slug}/documents")

        assert response.status_code == 200
        assert response.json() == []

    def test_non_member_gets_404(self, auth_client):
        organization, *_rest = make_org_with_roles()
        outsider = _rest[-1]
        auth_client.force_login(outsider)

        response = auth_client.get(f"/api/orgs/{organization.slug}/documents")

        assert response.status_code == 404

    def test_empty_organization_returns_empty_list(self, auth_client):
        organization, owner, *_rest = make_org_with_roles()
        auth_client.force_login(owner)

        response = auth_client.get(f"/api/orgs/{organization.slug}/documents")

        assert response.status_code == 200
        assert response.json() == []


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


@pytest.mark.django_db
class TestSetGenerationProfile:
    def _seed(self, auth_client, actor, organization):
        """A document holding class `c1` with attribute `a1`; returns the commands URL."""
        auth_client.force_login(actor)
        doc_id = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        ).json()["id"]
        url = f"/api/orgs/{organization.slug}/documents/{doc_id}/commands"
        auth_client.post(
            url,
            data={"type": "AddClass", "class_id": "c1", "name": "Order"},
            content_type="application/json",
        )
        auth_client.post(
            url,
            data={
                "type": "AddAttribute",
                "class_id": "c1",
                "attribute": {"id": "a1", "name": "reference", "type": "String"},
            },
            content_type="application/json",
        )
        return doc_id, url

    def _profile(self, auth_client, url, element_id, profile):
        return auth_client.post(
            url,
            data={"type": "SetGenerationProfile", "element_id": element_id, "profile": profile},
            content_type="application/json",
        )

    @pytest.mark.parametrize("role", ["owner", "editor"])
    def test_owner_and_editor_set_a_profile(self, auth_client, role):
        organization, owner, editor, _viewer, _outsider = make_org_with_roles()
        actor = {"owner": owner, "editor": editor}[role]
        doc_id, url = self._seed(auth_client, actor, organization)

        response = self._profile(auth_client, url, "c1", {"entity": True})

        assert response.status_code == 200
        assert response.json()["revision"] == 4
        stored = UmlDocument.all_objects.get(id=doc_id).data["model"]["generation_metadata"]
        assert stored == {"c1": {"profile": {"entity": True}}}

    def test_viewer_is_denied(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        doc_id, url = self._seed(auth_client, owner, organization)
        auth_client.force_login(viewer)

        response = self._profile(auth_client, url, "c1", {"entity": True})

        assert response.status_code == 403
        assert UmlDocument.all_objects.get(id=doc_id).revision == 3

    def test_invalid_profile_returns_422_with_the_parser_message_and_writes_nothing(
        self, auth_client
    ):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        doc_id, url = self._seed(auth_client, editor, organization)

        response = self._profile(auth_client, url, "c1", {"bogus": True})

        assert response.status_code == 422
        assert response.json() == {
            "detail": (
                "Invalid generation profile for element 'c1', key 'bogus': "
                "unknown table-level profile key"
            ),
            "code": "invalid_command_payload",
        }
        assert UmlDocument.all_objects.get(id=doc_id).revision == 3

    def test_unknown_element_id_returns_422(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        _doc_id, url = self._seed(auth_client, editor, organization)

        response = self._profile(auth_client, url, "ghost", None)

        assert response.status_code == 422
        assert response.json()["code"] == "invalid_command_payload"

    def test_cross_organization_member_gets_404(self, auth_client):
        organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
        other_organization, other_owner, *_rest = make_org_with_roles()
        doc_id, _url = self._seed(auth_client, owner, organization)
        auth_client.force_login(other_owner)

        response = self._profile(
            auth_client,
            f"/api/orgs/{other_organization.slug}/documents/{doc_id}/commands",
            "c1",
            {"entity": True},
        )

        assert response.status_code == 404
        assert UmlDocument.all_objects.get(id=doc_id).revision == 3

    def test_clear_removes_the_profile_and_broadcasts_once(
        self, auth_client, django_capture_on_commit_callbacks
    ):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        doc_id, url = self._seed(auth_client, editor, organization)
        self._profile(auth_client, url, "c1", {"entity": True})

        with mock.patch("apps.uml_documents.services.broadcast_document") as broadcast:
            with django_capture_on_commit_callbacks(execute=True):
                response = self._profile(auth_client, url, "c1", None)

        assert response.status_code == 200
        assert response.json()["revision"] == 5
        assert UmlDocument.all_objects.get(id=doc_id).data["model"]["generation_metadata"] == {}
        assert broadcast.call_count == 1


@pytest.mark.django_db
class TestDeleteDocument:
    def _create(self, client, organization, user) -> str:
        client.force_login(user)
        return client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "Doomed"},
            content_type="application/json",
        ).json()["id"]

    def test_editor_deletes_and_the_document_is_gone(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        doc_id = self._create(auth_client, organization, editor)
        url = f"/api/orgs/{organization.slug}/documents/{doc_id}"

        assert auth_client.delete(url).status_code == 204
        assert auth_client.get(url).status_code == 404
        assert auth_client.delete(url).status_code == 404

    def test_viewer_is_forbidden_and_the_document_survives(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        doc_id = self._create(auth_client, organization, owner)
        auth_client.force_login(viewer)

        response = auth_client.delete(f"/api/orgs/{organization.slug}/documents/{doc_id}")

        assert response.status_code == 403
        assert UmlDocument.all_objects.filter(id=doc_id).exists()


@pytest.mark.django_db
class TestUpdateRelationship:
    def _seed(self, auth_client, actor, organization, kind="association"):
        auth_client.force_login(actor)
        doc_id = auth_client.post(
            f"/api/orgs/{organization.slug}/documents",
            data={"name": "My Diagram"},
            content_type="application/json",
        ).json()["id"]
        url = f"/api/orgs/{organization.slug}/documents/{doc_id}/commands"
        for class_id in ("c1", "c2"):
            auth_client.post(
                url,
                data={"type": "AddClass", "class_id": class_id, "name": class_id.upper()},
                content_type="application/json",
            )
        auth_client.post(
            url,
            data={
                "type": "AddRelationship",
                "relationship": {
                    "id": "r1",
                    "kind": kind,
                    "name": "old",
                    "source": {"class_id": "c1", "multiplicity": "1"},
                    "target": {"class_id": "c2", "multiplicity": "1"},
                },
            },
            content_type="application/json",
        )
        return doc_id, url

    def _update(self, auth_client, url, relationship_id="r1", **fields):
        return auth_client.post(
            url,
            data={"type": "UpdateRelationship", "relationship_id": relationship_id, **fields},
            content_type="application/json",
        )

    def test_editor_updates_name_and_multiplicities_and_it_persists(self, auth_client):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        doc_id, url = self._seed(auth_client, editor, organization)

        response = self._update(
            auth_client, url, name="places", source_multiplicity="0..1", target_multiplicity="1..*"
        )

        assert response.status_code == 200
        assert response.json()["revision"] == 5
        stored = UmlDocument.all_objects.get(id=doc_id).data["model"]["relationships"][0]
        assert stored["name"] == "places"
        assert stored["source"]["multiplicity"] == {"lower": 0, "upper": 1}
        assert stored["target"]["multiplicity"] == {"lower": 1, "upper": None}

    def test_viewer_is_denied(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        _doc_id, url = self._seed(auth_client, owner, organization)
        auth_client.force_login(viewer)

        assert self._update(auth_client, url, name="x").status_code == 403

    @pytest.mark.parametrize(
        ("relationship_id", "kind", "fields"),
        [
            ("nope", "association", {"name": "x"}),
            ("r1", "generalization", {"source_multiplicity": "0..1"}),
            ("r1", "association", {"source_multiplicity": "not-a-multiplicity"}),
        ],
    )
    def test_rejected_updates_return_422_and_write_nothing(
        self, auth_client, relationship_id, kind, fields
    ):
        organization, _owner, editor, _viewer, _outsider = make_org_with_roles()
        doc_id, url = self._seed(auth_client, editor, organization, kind=kind)

        response = self._update(auth_client, url, relationship_id, **fields)

        assert response.status_code == 422
        assert response.json()["code"] == "invalid_command_payload"
        assert UmlDocument.all_objects.get(id=doc_id).revision == 4
