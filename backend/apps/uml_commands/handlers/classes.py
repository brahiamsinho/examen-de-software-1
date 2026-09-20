"""Handlers for class-level commands: add, remove (with relationship
cascade), rename (DD5).

No handler raises; a missing target short-circuits to the unchanged
model (DD6) before any `dataclasses.replace`.
"""
import dataclasses

from apps.uml_modeling.domain.elements import UmlClass
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.commands import AddClass, RemoveClass, RenameClass
from apps.uml_commands.handlers.generation_profile import prune_generation_metadata


def add_class(model: CanonicalUmlModel, command: AddClass) -> CanonicalUmlModel:
    new_class = UmlClass(id=command.class_id, name=command.name)
    return dataclasses.replace(model, classes=model.classes + (new_class,))


def remove_class(model: CanonicalUmlModel, command: RemoveClass) -> CanonicalUmlModel:
    target = model.class_by_id(command.class_id)
    if target is None:
        return model

    classes = tuple(uml_class for uml_class in model.classes if uml_class.id != command.class_id)
    relationships = tuple(
        relationship
        for relationship in model.relationships
        if relationship.source.class_id != command.class_id
        and relationship.target.class_id != command.class_id
    )
    removed = frozenset({command.class_id, *(attribute.id for attribute in target.attributes)})
    metadata = prune_generation_metadata(model.generation_metadata, removed)
    return dataclasses.replace(
        model, classes=classes, relationships=relationships, generation_metadata=metadata
    )


def rename_class(model: CanonicalUmlModel, command: RenameClass) -> CanonicalUmlModel:
    existing = model.class_by_id(command.class_id)
    if existing is None:
        return model

    renamed = dataclasses.replace(existing, name=command.new_name)
    classes = tuple(renamed if uml_class.id == command.class_id else uml_class for uml_class in model.classes)
    return dataclasses.replace(model, classes=classes)
