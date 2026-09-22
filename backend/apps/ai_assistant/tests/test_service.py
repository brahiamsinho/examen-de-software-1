"""Integration tests for `apps/ai_assistant/service.py`.

Only the Gemini call is mocked (`FakeGeminiClient`, injected via
`gemini=`) — every translated command still runs through the REAL
`apps.uml_documents.services.command_from_payload`/`submit_command`
pipeline against a real (test) database document, so these tests prove the
whole seam actually works, not just the translator in isolation.
"""
import datetime

import pytest
from django.utils import timezone

from apps.ai_assistant.errors import MissingApiKeyError
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.ai_assistant.service import apply_voice_command
from apps.organizations.tests.factories import make_organization
from apps.uml_documents import services


class FakeGeminiClient:
    """A hand-written `GeminiClientProtocol` double: returns whatever
    function-call list the test configured, and records the call it
    received for assertions on the prompt-building side."""

    def __init__(self, calls: list[GeminiFunctionCall]):
        self._calls = calls
        self.received = None

    def generate_function_calls(self, *, system_instruction, transcript, tools):
        self.received = {
            "system_instruction": system_instruction,
            "transcript": transcript,
            "tools": tools,
        }
        return self._calls


def _create_document(organization, owner):
    return services.create_document(
        organization=organization, owner_id=str(owner.id), name="Voice Diagram", now=timezone.now()
    )


@pytest.mark.django_db
class TestApplyVoiceCommand:
    def test_a_single_command_is_applied_through_the_real_pipeline(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeGeminiClient([GeminiFunctionCall(name="add_class", args={"name": "Persona"})])

        result = apply_voice_command(
            organization=organization,
            doc_id=document.id,
            transcript="creá una clase Persona",
            now=timezone.now(),
            gemini=gemini,
        )

        assert result.revision == document.revision + 1
        assert result.applied == [
            type(result.applied[0])(ok=True, message="Created class 'Persona'")
        ]
        reloaded = services.get_document(organization=organization, doc_id=document.id)
        assert [c.name for c in reloaded.model.classes] == ["Persona"]

    def test_forwards_the_transcript_and_tool_schema_to_gemini(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeGeminiClient([])

        apply_voice_command(
            organization=organization,
            doc_id=document.id,
            transcript="creá una clase Persona",
            now=timezone.now(),
            gemini=gemini,
        )

        assert "creá una clase Persona" in gemini.received["transcript"]
        assert len(gemini.received["tools"]) == 9

    def test_a_multi_command_utterance_applies_every_command_in_order(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeGeminiClient(
            [
                GeminiFunctionCall(name="add_class", args={"name": "Persona"}),
                GeminiFunctionCall(
                    name="add_attribute",
                    args={
                        "class_name": "Persona",
                        "attribute_name": "edad",
                        "attribute_type": "Integer",
                    },
                ),
            ]
        )

        result = apply_voice_command(
            organization=organization,
            doc_id=document.id,
            transcript="creá una clase Persona con un atributo edad",
            now=timezone.now(),
            gemini=gemini,
        )

        assert result.revision == document.revision + 2
        assert [item.ok for item in result.applied] == [True, True]
        reloaded = services.get_document(organization=organization, doc_id=document.id)
        [persona] = reloaded.model.classes
        assert persona.name == "Persona"
        assert [a.name for a in persona.attributes] == ["edad"]

    def test_a_failing_command_does_not_roll_back_earlier_successes_or_block_later_ones(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeGeminiClient(
            [
                GeminiFunctionCall(name="add_class", args={"name": "Persona"}),
                # References a class that was never created — fails to translate.
                GeminiFunctionCall(
                    name="add_attribute",
                    args={
                        "class_name": "Ghost",
                        "attribute_name": "edad",
                        "attribute_type": "Integer",
                    },
                ),
                GeminiFunctionCall(name="add_class", args={"name": "Mascota"}),
            ]
        )

        result = apply_voice_command(
            organization=organization,
            doc_id=document.id,
            transcript="tres comandos, el segundo falla",
            now=timezone.now(),
            gemini=gemini,
        )

        assert [item.ok for item in result.applied] == [True, False, True]
        assert result.applied[0].message == "Created class 'Persona'"
        assert "Ghost" in result.applied[1].message
        assert result.applied[2].message == "Created class 'Mascota'"
        reloaded = services.get_document(organization=organization, doc_id=document.id)
        assert sorted(c.name for c in reloaded.model.classes) == ["Mascota", "Persona"]
        # Only the 2 successful commands bumped the revision — the failed
        # translation was never submitted at all.
        assert reloaded.revision == document.revision + 2

    def test_a_malformed_command_payload_is_reported_not_raised(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        # Gemini invented a class type outside the declared enum — should
        # have been impossible given the tool schema, but the translator
        # still must not crash the whole request if it happens anyway.
        gemini = FakeGeminiClient(
            [GeminiFunctionCall(name="add_class", args={"name": "Persona"})]
            + [
                GeminiFunctionCall(
                    name="add_attribute",
                    args={
                        "class_name": "Persona",
                        "attribute_name": "edad",
                        "attribute_type": "NotAType",
                    },
                )
            ]
        )

        result = apply_voice_command(
            organization=organization,
            doc_id=document.id,
            transcript="test",
            now=timezone.now(),
            gemini=gemini,
        )

        assert result.applied[0].ok is True
        assert result.applied[1].ok is False

    def test_missing_api_key_raises_when_no_gemini_client_is_injected(self, settings):
        # Force the provider explicitly (design.md DD180): this test must
        # not depend on whatever LLM_PROVIDER/OPENAI_API_KEY happen to be
        # set to in the real environment pytest runs in.
        settings.LLM_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = ""
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)

        with pytest.raises(MissingApiKeyError):
            apply_voice_command(
                organization=organization,
                doc_id=document.id,
                transcript="creá una clase Persona",
                now=timezone.now(),
            )

    def test_an_unknown_document_raises_http404(self):
        from django.http import Http404

        organization = make_organization()
        gemini = FakeGeminiClient([])

        with pytest.raises(Http404):
            apply_voice_command(
                organization=organization,
                doc_id="00000000-0000-0000-0000-000000000000",
                transcript="creá una clase Persona",
                now=timezone.now(),
                gemini=gemini,
            )
