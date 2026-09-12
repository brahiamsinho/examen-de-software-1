"""The command dispatcher: exact-type handler lookup, pure model
transform, always-runs validation (DD2, DD4).

`_HANDLERS` starts empty and is populated by `handlers/{classes,
attributes,relationships}.py` as they import and register their
functions (Phases 4-6).
"""
import datetime
from collections.abc import Callable
from dataclasses import dataclass

from apps.uml_modeling.documents import ProjectDocument
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.validation.diagnostics import ValidationResult
from apps.uml_modeling.validation.engine import RULES, validate
from apps.uml_commands.commands import (
    AddAttribute,
    AddClass,
    AddRelationship,
    RemoveAttribute,
    RemoveClass,
    RemoveRelationship,
    RenameClass,
    UmlCommand,
)
from apps.uml_commands.handlers.attributes import add_attribute, remove_attribute
from apps.uml_commands.handlers.classes import add_class, remove_class, rename_class
from apps.uml_commands.handlers.relationships import add_relationship, remove_relationship

Handler = Callable[[CanonicalUmlModel, UmlCommand], CanonicalUmlModel]

_HANDLERS: dict[type, Handler] = {
    AddClass: add_class,
    RemoveClass: remove_class,
    RenameClass: rename_class,
    AddAttribute: add_attribute,
    RemoveAttribute: remove_attribute,
    AddRelationship: add_relationship,
    RemoveRelationship: remove_relationship,
}


@dataclass(frozen=True)
class CommandResult:
    document: ProjectDocument
    validation_result: ValidationResult


def apply(document: ProjectDocument, command: UmlCommand, *, now: datetime.datetime) -> CommandResult:
    """Apply `command` to `document`, never mutating the input.

    Looks up the handler by exact command type, runs it as a pure
    transform, wraps the result through `document.with_model(...)`
    (revision + 1), and always runs `validate(...)` — even when the
    resulting model is invalid (Always-Apply Diagnostics Policy).
    """
    handler = _HANDLERS[type(command)]
    new_model = handler(document.model, command)
    new_document = document.with_model(new_model, now=now)
    return CommandResult(
        document=new_document,
        validation_result=validate(new_document.model, rules=RULES),
    )
