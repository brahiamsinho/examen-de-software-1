"""Handlers for relationship-level commands: add, remove (DD5).

`add_relationship` performs a blind append — no endpoint-existence
check. The always-apply policy is enforced at the dispatcher/validation
level (`validate()` flags a dangling endpoint via
`INVALID_RELATIONSHIP_ENDPOINT`), never by refusing to apply here.
"""
import dataclasses

from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.commands import AddRelationship, RemoveRelationship


def add_relationship(model: CanonicalUmlModel, command: AddRelationship) -> CanonicalUmlModel:
    return dataclasses.replace(model, relationships=model.relationships + (command.relationship,))


def remove_relationship(model: CanonicalUmlModel, command: RemoveRelationship) -> CanonicalUmlModel:
    if not any(relationship.id == command.relationship_id for relationship in model.relationships):
        return model

    relationships = tuple(
        relationship for relationship in model.relationships if relationship.id != command.relationship_id
    )
    return dataclasses.replace(model, relationships=relationships)
