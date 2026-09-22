"""Tests for `apps/ai_assistant/translator.py`: name -> id resolution,
new-class registration within one batch, relationship lookup/ambiguity, and
the malformed/unsupported-call failure paths.
"""
import pytest

from apps.ai_assistant.errors import (
    AmbiguousRelationshipError,
    RelationshipNotFoundError,
    UnknownClassReferenceError,
    UnsupportedFunctionCallError,
)
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.ai_assistant.translator import Translator
from apps.uml_documents import schemas
from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.tests.factories import a_class, a_model, a_relationship, an_attribute


def _call(function_name: str, **args) -> GeminiFunctionCall:
    return GeminiFunctionCall(name=function_name, args=args)


class TestUnsupportedFunctionCall:
    def test_an_unknown_function_name_raises(self):
        translator = Translator(a_model())

        with pytest.raises(UnsupportedFunctionCallError):
            translator.translate(_call("delete_everything"))


class TestAddClass:
    def test_allocates_a_fresh_id_and_registers_the_name(self):
        translator = Translator(a_model())

        translated = translator.translate(_call("add_class", name="Persona"))

        assert isinstance(translated.payload, schemas.AddClassIn)
        assert translated.payload.name == "Persona"
        assert translated.payload.class_id  # non-empty, freshly allocated
        assert translated.description == "Created class 'Persona'"

    def test_two_add_class_calls_in_the_same_batch_get_distinct_ids(self):
        translator = Translator(a_model())

        first = translator.translate(_call("add_class", name="Persona"))
        second = translator.translate(_call("add_class", name="Mascota"))

        assert first.payload.class_id != second.payload.class_id

    def test_a_missing_required_argument_raises_key_error(self):
        translator = Translator(a_model())

        with pytest.raises(KeyError):
            translator.translate(_call("add_class"))


class TestClassNameResolution:
    def test_resolves_an_existing_class_by_exact_name(self):
        persona = a_class(name="Persona")
        translator = Translator(a_model(classes=(persona,)))

        translated = translator.translate(
            _call("rename_class", class_name="Persona", new_name="Cliente")
        )

        assert translated.payload.class_id == persona.id

    def test_resolves_case_insensitively_and_trims_whitespace(self):
        persona = a_class(name="Persona")
        translator = Translator(a_model(classes=(persona,)))

        translated = translator.translate(
            _call("rename_class", class_name="  persona  ", new_name="Cliente")
        )

        assert translated.payload.class_id == persona.id

    def test_an_unknown_class_name_raises(self):
        translator = Translator(a_model())

        with pytest.raises(UnknownClassReferenceError):
            translator.translate(_call("rename_class", class_name="Ghost", new_name="X"))

    def test_a_class_created_earlier_in_the_same_batch_is_resolvable(self):
        translator = Translator(a_model())

        created = translator.translate(_call("add_class", name="Persona"))
        translated = translator.translate(
            _call(
                "add_attribute",
                class_name="Persona",
                attribute_name="edad",
                attribute_type="Integer",
            )
        )

        assert translated.payload.class_id == created.payload.class_id
        assert translated.description == "Added attribute 'edad' to 'Persona'"

    def test_a_class_not_yet_created_in_the_batch_is_not_resolvable(self):
        translator = Translator(a_model())

        with pytest.raises(UnknownClassReferenceError):
            translator.translate(
                _call(
                    "add_attribute",
                    class_name="Persona",
                    attribute_name="edad",
                    attribute_type="Integer",
                )
            )
        # add_class for "Persona" never ran, so it stays unresolvable —
        # order matters, exactly like a human applying commands one at a time.


class TestAddAttribute:
    def test_defaults_visibility_to_private(self):
        persona = a_class(name="Persona")
        translator = Translator(a_model(classes=(persona,)))

        translated = translator.translate(
            _call(
                "add_attribute",
                class_name="Persona",
                attribute_name="edad",
                attribute_type="Integer",
            )
        )

        assert translated.payload.attribute.visibility == "private"
        assert translated.payload.attribute.type == "Integer"


class TestRemoveAttribute:
    def test_removes_by_name(self):
        edad = an_attribute(name="edad")
        persona = a_class(name="Persona", attributes=(edad,))
        translator = Translator(a_model(classes=(persona,)))

        translated = translator.translate(
            _call("remove_attribute", class_name="Persona", attribute_name="edad")
        )

        assert isinstance(translated.payload, schemas.RemoveAttributeIn)
        assert translated.payload.attribute_id == edad.id

    def test_an_unknown_attribute_name_raises(self):
        persona = a_class(name="Persona")
        translator = Translator(a_model(classes=(persona,)))

        with pytest.raises(UnknownClassReferenceError):
            translator.translate(
                _call("remove_attribute", class_name="Persona", attribute_name="ghost")
            )


class TestAddOperation:
    def test_defaults_visibility_to_public_and_allows_no_return_type(self):
        persona = a_class(name="Persona")
        translator = Translator(a_model(classes=(persona,)))

        translated = translator.translate(
            _call("add_operation", class_name="Persona", operation_name="saludar")
        )

        assert translated.payload.operation.visibility == "public"
        assert translated.payload.operation.return_type is None


class TestAddRelationship:
    def test_resolves_both_endpoints_and_defaults_multiplicities(self):
        persona = a_class(name="Persona")
        mascota = a_class(name="Mascota")
        translator = Translator(a_model(classes=(persona, mascota)))

        translated = translator.translate(
            _call(
                "add_relationship",
                kind="association",
                source_class_name="Persona",
                target_class_name="Mascota",
            )
        )

        relationship = translated.payload.relationship
        assert relationship.source.class_id == persona.id
        assert relationship.target.class_id == mascota.id
        assert relationship.kind == "association"
        assert relationship.source.multiplicity == "0..1"
        assert relationship.target.multiplicity == "0..*"

    def test_an_unknown_endpoint_raises(self):
        persona = a_class(name="Persona")
        translator = Translator(a_model(classes=(persona,)))

        with pytest.raises(UnknownClassReferenceError):
            translator.translate(
                _call(
                    "add_relationship",
                    kind="association",
                    source_class_name="Persona",
                    target_class_name="Ghost",
                )
            )


class TestRemoveAndUpdateRelationship:
    def test_finds_the_single_relationship_between_two_classes(self):
        persona = a_class(name="Persona")
        mascota = a_class(name="Mascota")
        relationship = a_relationship(source_id=persona.id, target_id=mascota.id)
        translator = Translator(
            a_model(classes=(persona, mascota), relationships=(relationship,))
        )

        translated = translator.translate(
            _call(
                "remove_relationship",
                source_class_name="Persona",
                target_class_name="Mascota",
            )
        )

        assert translated.payload.relationship_id == relationship.id

    def test_no_relationship_between_the_two_classes_raises(self):
        persona = a_class(name="Persona")
        mascota = a_class(name="Mascota")
        translator = Translator(a_model(classes=(persona, mascota)))

        with pytest.raises(RelationshipNotFoundError):
            translator.translate(
                _call(
                    "remove_relationship",
                    source_class_name="Persona",
                    target_class_name="Mascota",
                )
            )

    def test_two_relationships_between_the_same_pair_without_a_kind_is_ambiguous(self):
        persona = a_class(name="Persona")
        mascota = a_class(name="Mascota")
        association = a_relationship(
            kind=RelationshipKind.ASSOCIATION, source_id=persona.id, target_id=mascota.id
        )
        aggregation = a_relationship(
            kind=RelationshipKind.AGGREGATION, source_id=persona.id, target_id=mascota.id
        )
        translator = Translator(
            a_model(classes=(persona, mascota), relationships=(association, aggregation))
        )

        with pytest.raises(AmbiguousRelationshipError):
            translator.translate(
                _call(
                    "remove_relationship",
                    source_class_name="Persona",
                    target_class_name="Mascota",
                )
            )

    def test_a_stated_kind_disambiguates(self):
        persona = a_class(name="Persona")
        mascota = a_class(name="Mascota")
        association = a_relationship(
            kind=RelationshipKind.ASSOCIATION, source_id=persona.id, target_id=mascota.id
        )
        aggregation = a_relationship(
            kind=RelationshipKind.AGGREGATION, source_id=persona.id, target_id=mascota.id
        )
        translator = Translator(
            a_model(classes=(persona, mascota), relationships=(association, aggregation))
        )

        translated = translator.translate(
            _call(
                "remove_relationship",
                source_class_name="Persona",
                target_class_name="Mascota",
                kind="aggregation",
            )
        )

        assert translated.payload.relationship_id == aggregation.id

    def test_update_relationship_only_carries_the_fields_gemini_supplied(self):
        persona = a_class(name="Persona")
        mascota = a_class(name="Mascota")
        relationship = a_relationship(source_id=persona.id, target_id=mascota.id)
        translator = Translator(
            a_model(classes=(persona, mascota), relationships=(relationship,))
        )

        translated = translator.translate(
            _call(
                "update_relationship",
                source_class_name="Persona",
                target_class_name="Mascota",
                name="posee",
            )
        )

        assert translated.payload.relationship_id == relationship.id
        assert "name" in translated.payload.model_fields_set
        assert "source_multiplicity" not in translated.payload.model_fields_set
