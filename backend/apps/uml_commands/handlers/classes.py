"""Handlers for class-level commands: add, remove (with relationship
cascade), rename (DD5).

No handler raises; a missing target short-circuits to the unchanged
model (DD6) before any `dataclasses.replace`.
"""
import dataclasses

from apps.uml_modeling.domain.elements import UmlClass
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.commands import AddClass, RemoveClass, RenameClass


def add_class(model: CanonicalUmlModel, command: AddClass) -> CanonicalUmlModel:
    new_class = UmlClass(id=command.class_id, name=command.name)
    return dataclasses.replace(model, classes=model.classes + (new_class,))


def remove_class(model: CanonicalUmlModel, command: RemoveClass) -> CanonicalUmlModel:
    if model.class_by_id(command.class_id) is None:
        return model

    classes = tuple(uml_class for uml_class in model.classes if uml_class.id != command.class_id)
    relationships = tuple(
        relationship
        for relationship in model.relationships
        if relationship.source.class_id != command.class_id
        and relationship.target.class_id != command.class_id
    )
    return dataclasses.replace(model, classes=classes, relationships=relationships)


def rename_class(model: CanonicalUmlModel, command: RenameClass) -> CanonicalUmlModel:
    existing = model.class_by_id(command.class_id)
    if existing is None:
        return model

    renamed = dataclasses.replace(existing, name=command.new_name)
    classes = tuple(renamed if uml_class.id == command.class_id else uml_class for uml_class in model.classes)
    return dataclasses.replace(model, classes=classes)
