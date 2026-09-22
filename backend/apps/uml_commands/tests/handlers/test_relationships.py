"""Unit tests for relationship-level handlers: `add_relationship`,
`remove_relationship`.
"""
import dataclasses

import pytest

from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity
from apps.uml_commands.commands import AddRelationship, RemoveRelationship, UpdateRelationship
from apps.uml_commands.handlers.relationships import (
    add_relationship,
    remove_relationship,
    update_relationship,
)

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


def _association(name=None):
    relationship = a_relationship(
        source=a_relationship_end(multiplicity=Multiplicity(1, 1)),
        target=a_relationship_end(multiplicity=Multiplicity(0, None)),
    )
    return dataclasses.replace(relationship, name=name)


def test_update_relationship_changes_name_and_both_multiplicities():
    relationship = _association(name="old")
    other = a_relationship()
    model = CanonicalUmlModel(relationships=(relationship, other))

    new_model = update_relationship(
        model,
        UpdateRelationship(
            relationship_id=relationship.id,
            name="  places  ",
            source_multiplicity=Multiplicity(0, 1),
            target_multiplicity=Multiplicity(1, None),
        ),
    )

    updated = new_model.relationships[0]
    assert (updated.name, updated.source.multiplicity, updated.target.multiplicity) == (
        "places",
        Multiplicity(0, 1),
        Multiplicity(1, None),
    )
    assert new_model.relationships[1] is other
    assert updated.source.class_id == relationship.source.class_id


@pytest.mark.parametrize("cleared", [None, "", "   "])
def test_update_relationship_clears_the_name(cleared):
    relationship = _association(name="old")
    model = CanonicalUmlModel(relationships=(relationship,))

    new_model = update_relationship(
        model, UpdateRelationship(relationship_id=relationship.id, name=cleared)
    )

    assert new_model.relationships[0].name is None


def test_update_relationship_omitted_fields_are_left_untouched():
    relationship = _association(name="keep")
    model = CanonicalUmlModel(relationships=(relationship,))

    new_model = update_relationship(
        model, UpdateRelationship(relationship_id=relationship.id, target_multiplicity=Multiplicity(2, 3))
    )

    updated = new_model.relationships[0]
    assert updated.name == "keep"
    assert updated.source.multiplicity == Multiplicity(1, 1)
    assert updated.target.multiplicity == Multiplicity(2, 3)


def test_update_relationship_unknown_id_is_a_no_op():
    model = CanonicalUmlModel(relationships=(_association(),))

    assert update_relationship(model, UpdateRelationship(relationship_id=new_id(), name="x")) is model


def test_update_relationship_never_changes_generalization_multiplicities():
    generalization = a_relationship(kind=RelationshipKind.GENERALIZATION)
    model = CanonicalUmlModel(relationships=(generalization,))

    new_model = update_relationship(
        model,
        UpdateRelationship(
            relationship_id=generalization.id, name="is a", source_multiplicity=Multiplicity(5, 6)
        ),
    )

    updated = new_model.relationships[0]
    assert updated.name == "is a"
    assert updated.source.multiplicity == generalization.source.multiplicity
