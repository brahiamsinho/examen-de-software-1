"""Unit tests for class-level handlers: `add_class`, `remove_class`
(with relationship cascade), `rename_class`.
"""
from apps.uml_modeling.domain.elements import Enumeration, UmlAttribute, UmlOperation, Visibility
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import PrimitiveType
from apps.uml_modeling.validation.diagnostics import DiagnosticCode
from apps.uml_modeling.validation.engine import RULES, validate
from apps.uml_commands.commands import AddClass, RemoveClass, RenameClass
from apps.uml_commands.handlers.classes import add_class, remove_class, rename_class

from ..factories import a_class, a_relationship, a_relationship_end


def test_add_class_appends_new_class():
    model = CanonicalUmlModel(classes=(a_class(name="Existing"),))
    class_id = new_id()
    command = AddClass(class_id=class_id, name="Order")

    new_model = add_class(model, command)

    assert len(new_model.classes) == 2
    assert new_model.classes[-1].id == class_id
    assert new_model.classes[-1].name == "Order"


def test_remove_class_removes_matching_class_and_leaves_others_unchanged():
    class_a = a_class(name="A")
    class_b = a_class(name="B")
    enumeration = Enumeration(id=new_id(), name="Status")
    unrelated_relationship = a_relationship(
        source=a_relationship_end(class_id=class_b.id),
        target=a_relationship_end(class_id=class_b.id),
    )
    model = CanonicalUmlModel(
        classes=(class_a, class_b),
        enumerations=(enumeration,),
        relationships=(unrelated_relationship,),
    )

    new_model = remove_class(model, RemoveClass(class_id=class_a.id))

    assert new_model.classes == (class_b,)
    assert new_model.enumerations == (enumeration,)
    assert new_model.relationships == (unrelated_relationship,)


def test_remove_class_cascades_referencing_relationships():
    class_a = a_class(name="A")
    class_b = a_class(name="B")
    relationship = a_relationship(
        source=a_relationship_end(class_id=class_a.id),
        target=a_relationship_end(class_id=class_b.id),
    )
    model = CanonicalUmlModel(classes=(class_a, class_b), relationships=(relationship,))

    new_model = remove_class(model, RemoveClass(class_id=class_a.id))

    assert class_a not in new_model.classes
    assert relationship not in new_model.relationships
    result = validate(new_model, rules=RULES)
    assert not any(d.code == DiagnosticCode.INVALID_RELATIONSHIP_ENDPOINT for d in result.diagnostics)


def test_remove_class_unknown_id_is_a_no_op():
    model = CanonicalUmlModel(classes=(a_class(),))

    new_model = remove_class(model, RemoveClass(class_id=new_id()))

    assert new_model is model


def test_rename_class_preserves_identity_and_changes_only_name():
    attribute = UmlAttribute(id=new_id(), name="field", type=PrimitiveType.STRING)
    operation = UmlOperation(id=new_id(), name="doStuff")
    original = a_class(
        name="Original",
        attributes=(attribute,),
        operations=(operation,),
    )
    model = CanonicalUmlModel(classes=(original,))

    new_model = rename_class(model, RenameClass(class_id=original.id, new_name="Renamed"))

    renamed = new_model.class_by_id(original.id)
    assert renamed.id == original.id
    assert renamed.name == "Renamed"
    assert renamed.attributes == original.attributes
    assert renamed.operations == original.operations
    assert renamed.visibility == original.visibility


def test_rename_class_unknown_id_is_a_no_op():
    model = CanonicalUmlModel(classes=(a_class(),))

    new_model = rename_class(model, RenameClass(class_id=new_id(), new_name="X"))

    assert new_model is model
