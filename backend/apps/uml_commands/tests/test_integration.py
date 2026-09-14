"""End-to-end integration: apply all 7 commands in sequence against one
evolving `ProjectDocument`, asserting the final model's shape and that
every intermediate `CommandResult.document.revision` increments by
exactly 1 over the previous step.
"""
import datetime

from apps.uml_modeling.domain.elements import Relationship, RelationshipEnd, RelationshipKind, UmlAttribute
from apps.uml_modeling.domain.ids import new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.types import Multiplicity, PrimitiveType
from apps.uml_commands.commands import (
    AddAttribute,
    AddClass,
    AddRelationship,
    RemoveAttribute,
    RemoveClass,
    RemoveRelationship,
    RenameClass,
)
from apps.uml_commands.dispatcher import apply

from .factories import a_document

_NOW = datetime.datetime(2026, 3, 1, tzinfo=datetime.timezone.utc)


def test_applying_all_seven_commands_in_sequence_evolves_the_model():
    document = a_document(model=CanonicalUmlModel())
    revisions = [document.revision]

    order_id = new_id()
    customer_id = new_id()
    attribute_id = new_id()
    relationship_id = new_id()

    steps = [
        AddClass(class_id=order_id, name="Order"),
        AddClass(class_id=customer_id, name="Customer"),
        AddAttribute(
            class_id=order_id,
            attribute=UmlAttribute(id=attribute_id, name="total", type=PrimitiveType.DECIMAL),
        ),
        AddRelationship(
            relationship=Relationship(
                id=relationship_id,
                kind=RelationshipKind.ASSOCIATION,
                source=RelationshipEnd(class_id=order_id, multiplicity=Multiplicity(1, 1)),
                target=RelationshipEnd(class_id=customer_id, multiplicity=Multiplicity(0, None)),
            )
        ),
        RenameClass(class_id=order_id, new_name="PurchaseOrder"),
        RemoveAttribute(class_id=order_id, attribute_id=attribute_id),
        RemoveRelationship(relationship_id=relationship_id),
        RemoveClass(class_id=customer_id),
    ]

    for command in steps:
        result = apply(document, command, now=_NOW)
        revisions.append(result.document.revision)
        document = result.document

    for previous, current in zip(revisions, revisions[1:]):
        assert current == previous + 1

    final_model = document.model
    assert len(final_model.classes) == 1
    remaining_class = final_model.classes[0]
    assert remaining_class.id == order_id
    assert remaining_class.name == "PurchaseOrder"
    assert remaining_class.attributes == ()
    assert final_model.relationships == ()
