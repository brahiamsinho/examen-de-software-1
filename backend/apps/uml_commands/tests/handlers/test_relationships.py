"""Unit tests for relationship-level handlers: `add_relationship`,
`remove_relationship`.
"""
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.commands import AddRelationship, RemoveRelationship
from apps.uml_commands.handlers.relationships import add_relationship, remove_relationship

from ..factories import a_relationship, a_relationship_end


def test_add_relationship_appends_referencing_source_and_target():
    model = CanonicalUmlModel()
    source_id = new_id()
    target_id = new_id()
    relationship = a_relationship(
        source=a_relationship_end(class_id=source_id),
        target=a_relationship_end(class_id=target_id),
    )

    new_model = add_relationship(model, AddRelationship(relationship=relationship))

    assert new_model.relationships == (relationship,)
    assert new_model.relationships[0].source.class_id == source_id
    assert new_model.relationships[0].target.class_id == target_id


def test_add_relationship_performs_no_endpoint_existence_check():
    model = CanonicalUmlModel()
    relationship = a_relationship(
        source=a_relationship_end(class_id=new_id()),
        target=a_relationship_end(class_id=new_id()),
    )

    new_model = add_relationship(model, AddRelationship(relationship=relationship))

    assert relationship in new_model.relationships


def test_remove_relationship_removes_matching_and_leaves_others_unchanged():
    kept = a_relationship()
    removed = a_relationship()
    model = CanonicalUmlModel(relationships=(kept, removed))

    new_model = remove_relationship(model, RemoveRelationship(relationship_id=removed.id))

    assert new_model.relationships == (kept,)


def test_remove_relationship_unknown_id_is_a_no_op():
    model = CanonicalUmlModel(relationships=(a_relationship(),))

    new_model = remove_relationship(model, RemoveRelationship(relationship_id=new_id()))

    assert new_model is model
