"""Handlers for operation-level commands: add, remove (DD2).

Verbatim mirror of `handlers/attributes.py`. No handler raises; a missing
class or operation id short-circuits to the unchanged model before any
`dataclasses.replace`.
"""
import dataclasses

from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_commands.commands import AddOperation, RemoveOperation


def add_operation(model: CanonicalUmlModel, command: AddOperation) -> CanonicalUmlModel:
    target = model.class_by_id(command.class_id)
    if target is None:
        return model

    updated = dataclasses.replace(target, operations=target.operations + (command.operation,))
    classes = tuple(updated if uml_class.id == command.class_id else uml_class for uml_class in model.classes)
    return dataclasses.replace(model, classes=classes)


def remove_operation(model: CanonicalUmlModel, command: RemoveOperation) -> CanonicalUmlModel:
    target = model.class_by_id(command.class_id)
    if target is None:
        return model
    if not any(operation.id == command.operation_id for operation in target.operations):
        return model

    remaining = tuple(
        operation for operation in target.operations if operation.id != command.operation_id
    )
    updated = dataclasses.replace(target, operations=remaining)
    classes = tuple(updated if uml_class.id == command.class_id else uml_class for uml_class in model.classes)
    return dataclasses.replace(model, classes=classes)
