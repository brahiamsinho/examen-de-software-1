"""HTTP tests for AI board proposals (issue #15). The LLM is mocked at the one
seam `proposals.py` reads it from; everything else runs for real."""
from unittest import mock
from uuid import uuid4

import pytest
from django.utils import timezone

from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services


class _FakeClient:
    def __init__(self, calls):
        self._calls = calls

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        return self._calls


def _patched(calls):
    return mock.patch("apps.ai_assistant.proposals.get_active_llm_client", return_value=_FakeClient(calls))


def _document(organization, owner):
    return services.create_document(
        organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now()
    )


def _url(organization, doc_id, suffix="") -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/ai-proposals{suffix}"


def _propose(client, organization, doc_id, prompt="What is missing?", calls=None):
    calls = calls if calls is not None else [GeminiFunctionCall(name="add_class", args={"name": "Pedido"})]
    with _patched(calls):
        return client.post(_url(organization, doc_id), data={"prompt": prompt}, content_type="application/json")


@pytest.mark.django_db
class TestProposalsApi:
    def test_an_editor_asks_the_ai_and_gets_a_pending_draft_without_touching_the_diagram(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)

        response = _propose(auth_client, organization, document.id)

        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "pending"
        assert body["requested_by"] == (editor.full_name or editor.email)
        assert body["changes"][0]["ok"] is True
        assert body["calls"] == [{"name": "add_class", "args": {"name": "Pedido"}}]
        after = services.get_document(organization=organization, doc_id=document.id)
        assert after.revision == document.revision and after.model.classes == ()

    def test_a_viewer_can_list_proposals_but_cannot_ask_approve_or_reject(self, auth_client):
        organization, owner, editor, viewer, _outsider = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        proposal_id = _propose(auth_client, organization, document.id).json()["id"]

        auth_client.force_login(viewer)
        listed = auth_client.get(_url(organization, document.id))
        asked = _propose(auth_client, organization, document.id)
        approved = auth_client.post(_url(organization, document.id, f"/{proposal_id}/approve"))
        rejected = auth_client.post(_url(organization, document.id, f"/{proposal_id}/reject"))

        assert listed.status_code == 200 and [p["id"] for p in listed.json()] == [proposal_id]
        assert asked.status_code == 403
        assert approved.status_code == 403
        assert rejected.status_code == 403
        assert auth_client.get(_url(organization, document.id)).json()[0]["status"] == "pending"

    def test_approving_applies_the_change_and_returns_the_decided_proposal(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        proposal_id = _propose(auth_client, organization, document.id).json()["id"]

        response = auth_client.post(_url(organization, document.id, f"/{proposal_id}/approve"))

        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        assert response.json()["decided_by"] == (editor.full_name or editor.email)
        after = services.get_document(organization=organization, doc_id=document.id)
        assert [c.name for c in after.model.classes] == ["Pedido"]
        assert auth_client.get(_url(organization, document.id)).json() == []

    def test_approving_with_a_selection_applies_only_those_changes(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        calls = [
            GeminiFunctionCall(name="add_class", args={"name": "Pedido"}),
            GeminiFunctionCall(name="add_class", args={"name": "Cliente"}),
        ]
        proposal_id = _propose(auth_client, organization, document.id, calls=calls).json()["id"]

        response = auth_client.post(
            _url(organization, document.id, f"/{proposal_id}/approve"),
            data={"selected": [1]},
            content_type="application/json",
        )

        assert response.status_code == 200
        assert response.json()["applied_indices"] == [1]
        names = [c.name for c in services.get_document(organization=organization, doc_id=document.id).model.classes]
        assert names == ["Cliente"]

    def test_a_selection_that_drops_a_dependency_answers_409_and_changes_nothing(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        calls = [
            GeminiFunctionCall(name="add_class", args={"name": "Pedido"}),
            GeminiFunctionCall(
                name="add_attribute",
                args={"class_name": "Pedido", "attribute_name": "total", "attribute_type": "Decimal"},
            ),
        ]
        proposal_id = _propose(auth_client, organization, document.id, calls=calls).json()["id"]

        response = auth_client.post(
            _url(organization, document.id, f"/{proposal_id}/approve"),
            data={"selected": [1]},
            content_type="application/json",
        )

        assert response.status_code == 409
        assert "depend" in response.json()["detail"]
        assert services.get_document(organization=organization, doc_id=document.id).revision == document.revision

    def test_a_malformed_approval_body_answers_422_and_applies_nothing(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        proposal_id = _propose(auth_client, organization, document.id).json()["id"]

        response = auth_client.post(
            _url(organization, document.id, f"/{proposal_id}/approve"),
            data={"selected": "all"},
            content_type="application/json",
        )

        assert response.status_code == 422
        assert services.get_document(organization=organization, doc_id=document.id).revision == document.revision

    def test_a_structured_suggestion_arrives_with_attributes_and_relationships(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        suggestion = GeminiFunctionCall(
            name="suggest_uml_additions",
            args={
                "classes": [
                    {"name": "Pedido", "attributes": [{"name": "total", "type": "Decimal"}], "operations": []},
                    {"name": "Cliente", "attributes": [], "operations": []},
                ],
                "relationships": [
                    {"kind": "association", "source_class_name": "Cliente", "target_class_name": "Pedido"}
                ],
            },
        )

        body = _propose(auth_client, organization, document.id, calls=[suggestion]).json()

        assert [call["name"] for call in body["calls"]] == [
            "add_class",
            "add_class",
            "add_attribute",
            "add_relationship",
        ]
        assert all(change["ok"] for change in body["changes"])

    def test_rejecting_keeps_the_diagram_unchanged(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        proposal_id = _propose(auth_client, organization, document.id).json()["id"]

        response = auth_client.post(_url(organization, document.id, f"/{proposal_id}/reject"))

        assert response.status_code == 200 and response.json()["status"] == "rejected"
        after = services.get_document(organization=organization, doc_id=document.id)
        assert after.revision == document.revision

    def test_a_stale_proposal_answers_409_and_is_not_applied(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        proposal_id = _propose(auth_client, organization, document.id).json()["id"]
        auth_client.post(
            f"/api/orgs/{organization.slug}/documents/{document.id}/commands",
            data={"type": "AddClass", "class_id": "x", "name": "Persona"},
            content_type="application/json",
        )

        response = auth_client.post(_url(organization, document.id, f"/{proposal_id}/approve"))

        assert response.status_code == 409
        assert "changed" in response.json()["detail"]
        names = [c.name for c in services.get_document(organization=organization, doc_id=document.id).model.classes]
        assert names == ["Persona"]

    def test_no_suggestions_answers_422_with_guidance(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)

        response = _propose(auth_client, organization, document.id, calls=[])

        assert response.status_code == 422
        assert "no suggestions" in response.json()["detail"]

    def test_an_empty_prompt_is_rejected_before_calling_the_model(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)

        response = _propose(auth_client, organization, document.id, prompt="   ")

        assert response.status_code == 422

    def test_anonymous_gets_401_and_other_organizations_get_404(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        other_organization, other_owner, *_rest = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)
        proposal_id = _propose(auth_client, organization, document.id).json()["id"]

        auth_client.logout()
        assert auth_client.get(_url(organization, document.id)).status_code == 401

        auth_client.force_login(other_owner)
        assert auth_client.get(_url(other_organization, document.id)).status_code == 404
        assert (
            auth_client.post(_url(other_organization, document.id, f"/{proposal_id}/approve")).status_code == 404
        )
        assert auth_client.post(_url(organization, document.id, f"/{uuid4()}/reject")).status_code == 404
