"""HTTP tests for the diagram group chat (issue #16)."""
from unittest import mock

import pytest
from django.utils import timezone

from apps.ai_assistant.errors import GeminiRequestError
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services


class _Model:
    def __init__(self, reply="Hola equipo", error=None):
        self._reply, self._error = reply, error

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        if self._error:
            raise self._error
        return [GeminiFunctionCall(name="reply_in_chat", args={"message": self._reply})]


def _patched(model=None):
    return mock.patch("apps.ai_assistant.chat.get_active_llm_client", return_value=model or _Model())


def _document(organization, owner):
    return services.create_document(organization=organization, owner_id=str(owner.id), name="Board", now=timezone.now())


def _url(organization, doc_id) -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/chat"


def _say(client, organization, doc_id, content, model=None):
    with _patched(model):
        return client.post(_url(organization, doc_id), data={"content": content}, content_type="application/json")


@pytest.mark.django_db
class TestChatApi:
    def test_an_editor_writes_and_everyone_can_read_the_history(self, auth_client):
        organization, owner, editor, viewer, _outsider = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)

        posted = _say(auth_client, organization, document.id, "hola equipo")

        assert posted.status_code == 201
        body = posted.json()
        assert body["message"]["content"] == "hola equipo"
        assert body["message"]["author"] == (editor.full_name or editor.email)
        assert body["reply"] is None and body["ai_error"] is None

        auth_client.force_login(viewer)
        listed = auth_client.get(_url(organization, document.id))
        assert listed.status_code == 200
        assert [m["content"] for m in listed.json()] == ["hola equipo"]

    def test_mentioning_the_ai_returns_its_reply_in_the_same_response(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)

        body = _say(auth_client, organization, document.id, "@IA ayuda", _Model(reply="Con gusto")).json()

        assert body["reply"]["is_ai"] is True and body["reply"]["author"] == "IA"
        assert body["reply"]["content"] == "Con gusto"

    def test_when_the_model_fails_the_message_is_kept_and_the_error_is_reported(self, auth_client):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)

        response = _say(auth_client, organization, document.id, "@IA ayuda", _Model(error=GeminiRequestError("x")))

        assert response.status_code == 201
        assert response.json()["reply"] is None and response.json()["ai_error"]
        assert [m["content"] for m in auth_client.get(_url(organization, document.id)).json()] == ["@IA ayuda"]

    def test_a_viewer_can_read_but_cannot_write(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(viewer)

        response = _say(auth_client, organization, document.id, "hola")

        assert response.status_code == 403
        assert auth_client.get(_url(organization, document.id)).json() == []

    def test_another_organization_gets_404_for_reading_and_writing(self, auth_client):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)
        other, _other_owner, other_editor, *_ = make_org_with_roles()
        auth_client.force_login(other_editor)

        write = _say(auth_client, other, document.id, "hola")
        read = auth_client.get(_url(other, document.id))
        cross = auth_client.get(_url(organization, document.id))

        assert write.status_code == 404 and read.status_code == 404
        assert cross.status_code in (403, 404)

    @pytest.mark.parametrize("content", ["", "   "])
    def test_a_blank_message_answers_422(self, auth_client, content):
        organization, owner, editor, *_ = make_org_with_roles()
        document = _document(organization, owner)
        auth_client.force_login(editor)

        assert _say(auth_client, organization, document.id, content).status_code == 422

    def test_an_anonymous_client_is_rejected(self, client):
        organization, owner, *_ = make_org_with_roles()
        document = _document(organization, owner)

        assert client.get(_url(organization, document.id)).status_code == 401
