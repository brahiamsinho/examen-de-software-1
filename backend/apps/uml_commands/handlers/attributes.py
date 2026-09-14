"""Handlers for attribute-level commands: add, remove (DD5).

No handler raises; a missing class or attribute id short-circuits to
the unchanged model (DD6) before any `dataclasses.replace`.
"""
import dataclasses

from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.commands import AddAttribute, RemoveAttribute


def add_attribute(model: CanonicalUmlModel, command: AddAttribute) -> CanonicalUmlModel:
    target = model.class_by_id(command.class_id)
    if target is None:
        return model

    updated = dataclasses.replace(target, attributes=target.attributes + (command.attribute,))
    classes = tuple(updated if uml_class.id == command.class_id else uml_class for uml_class in model.classes)
    return dataclasses.replace(model, classes=classes)


def remove_attribute(model: CanonicalUmlModel, command: RemoveAttribute) -> CanonicalUmlModel:
    target = model.class_by_id(command.class_id)
    if target is None:
        return model
    if not any(attribute.id == command.attribute_id for attribute in target.attributes):
        return model

    remaining = tuple(
        attribute for attribute in target.attributes if attribute.id != command.attribute_id
    )
    updated = dataclasses.replace(target, attributes=remaining)
    classes = tuple(updated if uml_class.id == command.class_id else uml_class for uml_class in model.classes)
    return dataclasses.replace(model, classes=classes)
