"""Unit tests for the dispatcher skeleton: `apply()` looks up a handler by
exact command type, never mutates the input document/model, always
increments the revision by exactly 1, and always populates
`validation_result` via `validate(new_model, rules=RULES)`.
"""
import dataclasses
import datetime

from apps.uml_modeling.domain.elements import UmlAttribute
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import PrimitiveType
from apps.uml_modeling.validation.diagnostics import DiagnosticCode
from apps.uml_modeling.validation.engine import RULES, validate
from apps.uml_commands import dispatcher
from apps.uml_commands.commands import (
    AddAttribute,
    AddOperation,
    AddRelationship,
    RemoveAttribute,
    RemoveClass,
    RemoveOperation,
    RemoveRelationship,
)
from apps.uml_commands.dispatcher import CommandResult, apply
from apps.uml_modeling.domain.elements import UmlOperation

from .factories import a_class, a_document, a_relationship, a_relationship_end

_NOW = datetime.datetime(2026, 2, 1, tzinfo=datetime.timezone.utc)


@dataclasses.dataclass(frozen=True)
class _FakeCommand:
    pass


def test_apply_returns_a_command_result(monkeypatch):
    document = a_document()

    def _fake_handler(model, command):
        return model

    monkeypatch.setitem(dispatcher._HANDLERS, _FakeCommand, _fake_handler)

    result = apply(document, _FakeCommand(), now=_NOW)

    assert isinstance(result, CommandResult)


def test_apply_does_not_mutate_the_input_document_or_model(monkeypatch):
    original_class = a_class(name="Existing")
    document = a_document(model=CanonicalUmlModel(classes=(original_class,)))
    original_model = document.model
    original_revision = document.revision
    new_class = a_class(name="Added")

    def _fake_handler(model, command):
        return dataclasses.replace(model, classes=model.classes + (new_class,))

    monkeypatch.setitem(dispatcher._HANDLERS, _FakeCommand, _fake_handler)

    apply(document, _FakeCommand(), now=_NOW)

    assert document.model is original_model
    assert document.revision == original_revision
    assert document.model.classes == (original_class,)


def test_apply_increments_revision_by_exactly_one(monkeypatch):
    document = a_document()
    original_revision = document.revision

    def _fake_handler(model, command):
        return model

    monkeypatch.setitem(dispatcher._HANDLERS, _FakeCommand, _fake_handler)

    result = apply(document, _FakeCommand(), now=_NOW)

    assert result.document.revision == original_revision + 1


def test_apply_always_populates_validation_result(monkeypatch):
    original_class = a_class(name="Existing")
    document = a_document(model=CanonicalUmlModel(classes=(original_class,)))
    new_class = a_class(name="Added")

    def _fake_handler(model, command):
        return dataclasses.replace(model, classes=model.classes + (new_class,))

    monkeypatch.setitem(dispatcher._HANDLERS, _FakeCommand, _fake_handler)

    result = apply(document, _FakeCommand(), now=_NOW)

    assert result.validation_result is not None
    assert result.validation_result == validate(result.document.model, rules=RULES)


def test_handlers_registry_has_exactly_nine_entries():
    assert len(dispatcher._HANDLERS) == 9


def test_apply_never_raises_and_surfaces_invalid_endpoint_diagnostics():
    class_a = a_class(name="A")
    document = a_document(model=CanonicalUmlModel(classes=(class_a,)))
    relationship = a_relationship(
        source=a_relationship_end(class_id=class_a.id),
        target=a_relationship_end(class_id=new_id()),
    )

    result = apply(document, AddRelationship(relationship=relationship), now=_NOW)

    assert relationship in result.document.model.relationships
    assert result.validation_result.diagnostics
    assert any(
        diagnostic.code == DiagnosticCode.INVALID_RELATIONSHIP_ENDPOINT
        for diagnostic in result.validation_result.diagnostics
    )


def test_apply_remove_class_unknown_id_is_a_no_op_through_the_real_dispatcher():
    original_model = CanonicalUmlModel(classes=(a_class(),))
    document = a_document(model=original_model)
    original_revision = document.revision

    result = apply(document, RemoveClass(class_id=new_id()), now=_NOW)

    assert result.document.model.classes == original_model.classes
    assert result.document.model.enumerations == original_model.enumerations
    assert result.document.model.relationships == original_model.relationships
    assert result.document.revision == original_revision + 1


def test_apply_remove_attribute_unknown_ids_is_a_no_op_through_the_real_dispatcher():
    original_model = CanonicalUmlModel(classes=(a_class(),))
    document = a_document(model=original_model)
    original_revision = document.revision

    result = apply(
        document, RemoveAttribute(class_id=new_id(), attribute_id=new_id()), now=_NOW
    )

    assert result.document.model.classes == original_model.classes
    assert result.document.revision == original_revision + 1


def test_apply_remove_relationship_unknown_id_is_a_no_op_through_the_real_dispatcher():
    original_model = CanonicalUmlModel(relationships=(a_relationship(),))
    document = a_document(model=original_model)
    original_revision = document.revision

    result = apply(document, RemoveRelationship(relationship_id=new_id()), now=_NOW)

    assert result.document.model.relationships == original_model.relationships
    assert result.document.revision == original_revision + 1


def test_apply_add_attribute_unknown_class_id_is_a_no_op_through_the_real_dispatcher():
    original_model = CanonicalUmlModel(classes=(a_class(),))
    document = a_document(model=original_model)
    original_revision = document.revision
    attribute = UmlAttribute(id=new_id(), name="field", type=PrimitiveType.STRING)

    result = apply(document, AddAttribute(class_id=new_id(), attribute=attribute), now=_NOW)

    assert result.document.model.classes == original_model.classes
    assert result.document.revision == original_revision + 1


def test_apply_add_operation_appends_through_the_real_dispatcher():
    original_class = a_class(name="Existing")
    document = a_document(model=CanonicalUmlModel(classes=(original_class,)))
    original_revision = document.revision
    operation = UmlOperation(id=new_id(), name="crearUsuario", return_type=PrimitiveType.STRING)

    result = apply(document, AddOperation(class_id=original_class.id, operation=operation), now=_NOW)

    updated_class = result.document.model.class_by_id(original_class.id)
    assert updated_class.operations == (operation,)
    assert result.document.revision == original_revision + 1


def test_apply_add_operation_unknown_class_id_is_a_no_op_through_the_real_dispatcher():
    original_model = CanonicalUmlModel(classes=(a_class(),))
    document = a_document(model=original_model)
    original_revision = document.revision
    operation = UmlOperation(id=new_id(), name="crearUsuario")

    result = apply(document, AddOperation(class_id=new_id(), operation=operation), now=_NOW)

    assert result.document.model.classes == original_model.classes
    assert result.document.revision == original_revision + 1


def test_apply_remove_operation_unknown_ids_is_a_no_op_through_the_real_dispatcher():
    original_model = CanonicalUmlModel(classes=(a_class(),))
    document = a_document(model=original_model)
    original_revision = document.revision

    result = apply(
        document, RemoveOperation(class_id=new_id(), operation_id=new_id()), now=_NOW
    )

    assert result.document.model.classes == original_model.classes
    assert result.document.revision == original_revision + 1
