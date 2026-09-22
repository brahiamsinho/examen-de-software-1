"""Handlers for relationship-level commands: add, remove, update (DD5).

`add_relationship` performs a blind append — no endpoint-existence
check. The always-apply policy is enforced at the dispatcher/validation
level (`validate()` flags a dangling endpoint via
`INVALID_RELATIONSHIP_ENDPOINT`), never by refusing to apply here.
"""
import dataclasses

from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_commands.commands import UNSET, AddRelationship, RemoveRelationship, UpdateRelationship


def add_relationship(model: CanonicalUmlModel, command: AddRelationship) -> CanonicalUmlModel:
    return dataclasses.replace(model, relationships=model.relationships + (command.relationship,))


def remove_relationship(model: CanonicalUmlModel, command: RemoveRelationship) -> CanonicalUmlModel:
    if not any(relationship.id == command.relationship_id for relationship in model.relationships):
        return model

    relationships = tuple(
        relationship for relationship in model.relationships if relationship.id != command.relationship_id
    )
    return dataclasses.replace(model, relationships=relationships)


def update_relationship(model: CanonicalUmlModel, command: UpdateRelationship) -> CanonicalUmlModel:
    """Partial update; an unknown id short-circuits to the unchanged model
    (DD6). Multiplicities never change on a generalization (it has none);
    the API service rejects that case loudly before the handler runs.
    """
    existing = next((r for r in model.relationships if r.id == command.relationship_id), None)
    if existing is None:
        return model

    updated = existing
    if command.name is not UNSET:
        name = (command.name or "").strip() or None
        updated = dataclasses.replace(updated, name=name)
    if existing.kind is not RelationshipKind.GENERALIZATION:
        if command.source_multiplicity is not None:
            updated = dataclasses.replace(
                updated,
                source=dataclasses.replace(updated.source, multiplicity=command.source_multiplicity),
            )
        if command.target_multiplicity is not None:
            updated = dataclasses.replace(
                updated,
                target=dataclasses.replace(updated.target, multiplicity=command.target_multiplicity),
            )

    relationships = tuple(updated if r.id == command.relationship_id else r for r in model.relationships)
    return dataclasses.replace(model, relationships=relationships)
