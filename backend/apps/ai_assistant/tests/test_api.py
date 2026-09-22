"""HTTP tests for `POST /api/orgs/{org_slug}/documents/{doc_id}/voice-command`.

The LLM call is mocked at the one seam `service.py` reads it from
(`apps.ai_assistant.service.get_active_llm_client`) — everything downstream
(translation, `command_from_payload`, `submit_command`) runs for real
against the test database, same as `test_service.py`.
"""
from unittest import mock
from uuid import uuid4

import pytest

from apps.ai_assistant.errors import GeminiRequestError
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.organizations.tests.factories import make_org_with_roles
from apps.uml_documents import services
from django.utils import timezone


def _create_document(organization, owner) -> str:
    document = services.create_document(
        organization=organization, owner_id=str(owner.id), name="Voice Diagram", now=timezone.now()
    )
    return str(document.id)


def _url(organization, doc_id) -> str:
    return f"/api/orgs/{organization.slug}/documents/{doc_id}/voice-command"


class _FakeGeminiClient:
    def __init__(self, calls):
        self._calls = calls

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        return self._calls


def _patched_gemini(calls):
    return mock.patch(
        "apps.ai_assistant.service.get_active_llm_client",
        return_value=_FakeGeminiClient(calls),
    )


@pytest.mark.django_db
class TestVoiceCommandView:
    def test_editor_applies_a_voice_command(self, auth_client):
        organization, owner, editor, _viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(organization, owner)
        auth_client.force_login(editor)

        with _patched_gemini([GeminiFunctionCall(name="add_class", args={"name": "Persona"})]):
            response = auth_client.post(
                _url(organization, doc_id),
                data={"transcript": "creá una clase Persona"},
                content_type="application/json",
            )

        assert response.status_code == 200
        body = response.json()
        assert body["revision"] == 2
        assert body["applied"] == [{"ok": True, "message": "Created class 'Persona'"}]

    def test_owner_applies_a_voice_command(self, auth_client):
        organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(organization, owner)
        auth_client.force_login(owner)

        with _patched_gemini([]):
            response = auth_client.post(
                _url(organization, doc_id),
                data={"transcript": "no hagas nada"},
                content_type="application/json",
            )

        assert response.status_code == 200
        assert response.json() == {"revision": 1, "applied": []}

    def test_viewer_is_denied(self, auth_client):
        organization, owner, _editor, viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(organization, owner)
        auth_client.force_login(viewer)

        with _patched_gemini([]):
            response = auth_client.post(
                _url(organization, doc_id),
                data={"transcript": "creá una clase Persona"},
                content_type="application/json",
            )

        assert response.status_code == 403

    def test_anonymous_user_gets_401(self, auth_client):
        organization, *_rest = make_org_with_roles()

        response = auth_client.post(
            _url(organization, uuid4()),
            data={"transcript": "creá una clase Persona"},
            content_type="application/json",
        )

        assert response.status_code == 401

    def test_non_member_gets_404(self, auth_client):
        organization, owner, _editor, _viewer, outsider = make_org_with_roles()
        doc_id = _create_document(organization, owner)
        auth_client.force_login(outsider)

        with _patched_gemini([]):
            response = auth_client.post(
                _url(organization, doc_id),
                data={"transcript": "creá una clase Persona"},
                content_type="application/json",
            )

        assert response.status_code == 404

    def test_unknown_document_gets_404(self, auth_client):
        organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
        auth_client.force_login(owner)

        with _patched_gemini([]):
            response = auth_client.post(
                _url(organization, uuid4()),
                data={"transcript": "creá una clase Persona"},
                content_type="application/json",
            )

        assert response.status_code == 404

    def test_missing_api_key_answers_503(self, auth_client, settings):
        # Force the provider explicitly (design.md DD180): this test must
        # not depend on whatever LLM_PROVIDER/OPENAI_API_KEY happen to be
        # set to in the real environment pytest runs in.
        settings.LLM_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = ""
        organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(organization, owner)
        auth_client.force_login(owner)

        response = auth_client.post(
            _url(organization, doc_id),
            data={"transcript": "creá una clase Persona"},
            content_type="application/json",
        )

        assert response.status_code == 503
        assert response.json()["code"] == "gemini_api_key_missing"

    def test_a_gemini_failure_answers_502(self, auth_client):
        organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(organization, owner)
        auth_client.force_login(owner)

        failing_client = mock.Mock()
        failing_client.generate_function_calls.side_effect = GeminiRequestError("boom")
        with mock.patch(
            "apps.ai_assistant.service.get_active_llm_client", return_value=failing_client
        ):
            response = auth_client.post(
                _url(organization, doc_id),
                data={"transcript": "creá una clase Persona"},
                content_type="application/json",
            )

        assert response.status_code == 502
        assert response.json()["code"] == "gemini_request_failed"

    def test_a_multi_command_utterance_with_a_partial_failure(self, auth_client):
        organization, owner, _editor, _viewer, _outsider = make_org_with_roles()
        doc_id = _create_document(organization, owner)
        auth_client.force_login(owner)
        calls = [
            GeminiFunctionCall(name="add_class", args={"name": "Persona"}),
            GeminiFunctionCall(
                name="add_attribute",
                args={"class_name": "Ghost", "attribute_name": "edad", "attribute_type": "Integer"},
            ),
        ]

        with _patched_gemini(calls):
            response = auth_client.post(
                _url(organization, doc_id),
                data={"transcript": "creá Persona y agregale edad a Ghost"},
                content_type="application/json",
            )

        assert response.status_code == 200
        body = response.json()
        assert body["applied"][0] == {"ok": True, "message": "Created class 'Persona'"}
        assert body["applied"][1]["ok"] is False
