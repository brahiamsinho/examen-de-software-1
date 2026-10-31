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
from apps.ai_assistant.service import (
    apply_image_command,
    apply_voice_command,
    confirm_image_import,
    preview_image_import,
)
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


class FakeImageGeminiClient:
    """Same double as `FakeGeminiClient`, for the image-import seam
    (`generate_function_calls_from_image`)."""

    def __init__(self, calls: list[GeminiFunctionCall]):
        self._calls = calls
        self.received = None

    def generate_function_calls_from_image(
        self, *, system_instruction, image_bytes, image_mime_type, tools
    ):
        self.received = {
            "system_instruction": system_instruction,
            "image_bytes": image_bytes,
            "image_mime_type": image_mime_type,
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


@pytest.mark.django_db
class TestApplyImageCommand:
    """Reuses the exact same per-command translate/submit pipeline and
    partial-failure policy as `apply_voice_command` — only the LLM seam
    (`generate_function_calls_from_image`) and the system instruction
    differ. See `TestApplyVoiceCommand` above for the equivalent transcript
    coverage this mirrors."""

    def test_a_single_command_is_applied_through_the_real_pipeline(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeImageGeminiClient(
            [GeminiFunctionCall(name="add_class", args={"name": "Persona"})]
        )

        result = apply_image_command(
            organization=organization,
            doc_id=document.id,
            image_bytes=b"fake-png-bytes",
            image_mime_type="image/png",
            now=timezone.now(),
            gemini=gemini,
        )

        assert result.revision == document.revision + 1
        assert result.applied == [
            type(result.applied[0])(ok=True, message="Created class 'Persona'")
        ]
        reloaded = services.get_document(organization=organization, doc_id=document.id)
        assert [c.name for c in reloaded.model.classes] == ["Persona"]

    def test_forwards_the_image_bytes_mime_type_and_tool_schema(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeImageGeminiClient([])

        apply_image_command(
            organization=organization,
            doc_id=document.id,
            image_bytes=b"fake-png-bytes",
            image_mime_type="image/png",
            now=timezone.now(),
            gemini=gemini,
        )

        assert gemini.received["image_bytes"] == b"fake-png-bytes"
        assert gemini.received["image_mime_type"] == "image/png"
        assert [tool["name"] for tool in gemini.received["tools"]] == ["extract_uml_diagram"]

    def test_a_multi_command_image_applies_every_command_in_order(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeImageGeminiClient(
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

        result = apply_image_command(
            organization=organization,
            doc_id=document.id,
            image_bytes=b"fake-png-bytes",
            image_mime_type="image/png",
            now=timezone.now(),
            gemini=gemini,
        )

        assert result.revision == document.revision + 2
        assert [item.ok for item in result.applied] == [True, True]
        reloaded = services.get_document(organization=organization, doc_id=document.id)
        [persona] = reloaded.model.classes
        assert persona.name == "Persona"
        assert [a.name for a in persona.attributes] == ["edad"]

    def test_a_structured_image_extraction_creates_attributes_and_relationships(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeImageGeminiClient(
            [
                GeminiFunctionCall(
                    name="extract_uml_diagram",
                    args={
                        "classes": [
                            {
                                "name": "Venta",
                                "attributes": [
                                    {"name": "id", "type": "Integer"},
                                    {"name": "fecha", "type": "DateTime"},
                                ],
                                "operations": [],
                            },
                            {
                                "name": "Cliente",
                                "attributes": [
                                    {"name": "id", "type": "Integer"},
                                    {"name": "nombre", "type": "String"},
                                    {"name": "email", "type": "String"},
                                ],
                                "operations": [],
                            },
                        ],
                        "relationships": [
                            {
                                "kind": "association",
                                "source_class_name": "Venta",
                                "target_class_name": "Cliente",
                                "source_multiplicity": "*",
                                "target_multiplicity": "1",
                            }
                        ],
                    },
                )
            ]
        )

        result = apply_image_command(
            organization=organization,
            doc_id=document.id,
            image_bytes=b"fake-png-bytes",
            image_mime_type="image/png",
            now=timezone.now(),
            gemini=gemini,
        )

        assert [item.ok for item in result.applied] == [True] * 8
        reloaded = services.get_document(organization=organization, doc_id=document.id)
        venta = next(uml_class for uml_class in reloaded.model.classes if uml_class.name == "Venta")
        cliente = next(uml_class for uml_class in reloaded.model.classes if uml_class.name == "Cliente")
        assert [attribute.name for attribute in venta.attributes] == ["id", "fecha"]
        assert [attribute.name for attribute in cliente.attributes] == ["id", "nombre", "email"]
        [relationship] = reloaded.model.relationships
        assert relationship.source.class_id == venta.id
        assert relationship.target.class_id == cliente.id
        assert relationship.source.multiplicity.upper is None

    def test_preview_keeps_the_document_unchanged_until_confirmation(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        apply_voice_command(
            organization=organization,
            doc_id=document.id,
            transcript="creá una clase Producto",
            now=timezone.now(),
            gemini=FakeGeminiClient([GeminiFunctionCall(name="add_class", args={"name": "Producto"})]),
        )
        image = FakeImageGeminiClient(
            [GeminiFunctionCall(name="extract_uml_diagram", args={"classes": [], "relationships": []})]
        )

        preview = preview_image_import(
            organization=organization,
            doc_id=document.id,
            image_bytes=b"fake-png-bytes",
            image_mime_type="image/png",
            gemini=image,
        )

        assert [change.message for change in preview.changes] == ["Removed class 'Producto'"]
        assert [uml_class.name for uml_class in services.get_document(organization=organization, doc_id=document.id).model.classes] == ["Producto"]

        result = confirm_image_import(
            organization=organization, doc_id=document.id, plan_id=preview.plan_id, now=timezone.now()
        )

        assert [item.ok for item in result.applied] == [True]
        assert services.get_document(organization=organization, doc_id=document.id).model.classes == ()

    def test_stale_preview_cannot_delete_changes_made_after_preview(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        apply_voice_command(
            organization=organization,
            doc_id=document.id,
            transcript="creá Producto",
            now=timezone.now(),
            gemini=FakeGeminiClient([GeminiFunctionCall(name="add_class", args={"name": "Producto"})]),
        )
        preview = preview_image_import(
            organization=organization,
            doc_id=document.id,
            image_bytes=b"fake-png-bytes",
            image_mime_type="image/png",
            gemini=FakeImageGeminiClient(
                [GeminiFunctionCall(name="extract_uml_diagram", args={"classes": [], "relationships": []})]
            ),
        )
        apply_voice_command(
            organization=organization,
            doc_id=document.id,
            transcript="creá Cliente",
            now=timezone.now(),
            gemini=FakeGeminiClient([GeminiFunctionCall(name="add_class", args={"name": "Cliente"})]),
        )

        with pytest.raises(ValueError, match="diagram changed after this preview"):
            confirm_image_import(
                organization=organization, doc_id=document.id, plan_id=preview.plan_id, now=timezone.now()
            )

        current = services.get_document(organization=organization, doc_id=document.id)
        assert [uml_class.name for uml_class in current.model.classes] == ["Producto", "Cliente"]

    def test_a_failing_command_does_not_roll_back_earlier_successes_or_block_later_ones(self):
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)
        gemini = FakeImageGeminiClient(
            [
                GeminiFunctionCall(name="add_class", args={"name": "Persona"}),
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

        result = apply_image_command(
            organization=organization,
            doc_id=document.id,
            image_bytes=b"fake-png-bytes",
            image_mime_type="image/png",
            now=timezone.now(),
            gemini=gemini,
        )

        assert [item.ok for item in result.applied] == [True, False, True]
        reloaded = services.get_document(organization=organization, doc_id=document.id)
        assert sorted(c.name for c in reloaded.model.classes) == ["Mascota", "Persona"]

    def test_missing_api_key_raises_when_no_gemini_client_is_injected(self, settings):
        settings.LLM_PROVIDER = "gemini"
        settings.GEMINI_API_KEY = ""
        organization = make_organization()
        owner = organization.memberships.get().user
        document = _create_document(organization, owner)

        with pytest.raises(MissingApiKeyError):
            apply_image_command(
                organization=organization,
                doc_id=document.id,
                image_bytes=b"fake-png-bytes",
                image_mime_type="image/png",
                now=timezone.now(),
            )

    def test_an_unknown_document_raises_http404(self):
        from django.http import Http404

        organization = make_organization()
        gemini = FakeImageGeminiClient([])

        with pytest.raises(Http404):
            apply_image_command(
                organization=organization,
                doc_id="00000000-0000-0000-0000-000000000000",
                image_bytes=b"fake-png-bytes",
                image_mime_type="image/png",
                now=timezone.now(),
                gemini=gemini,
            )
