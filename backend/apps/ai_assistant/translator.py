"""Gemini function-call -> `apps.uml_documents.schemas.CommandIn` translator.

The one seam that turns Gemini's name-based function calls into the exact
same `CommandIn` shapes the manual UI submits, so every command still runs
through the real, already-tested `command_from_payload`/`submit_command`
pipeline (no duplicated validation logic).

Multi-command batches: one `Translator` instance is built per whole voice
utterance, not per call. Each `add_class` translation immediately
registers `name -> freshly allocated ElementId` in `self._name_to_id`, so a
later call in the SAME utterance ("creá una clase Persona con un atributo
edad") can refer to a class Gemini itself just asked to create, before
that class has ever reached the database. Name lookup is case-insensitive
and whitespace-trimmed (speech-to-text transcripts vary in capitalization
and spacing); the ORIGINAL casing Gemini supplied is always what gets
written into the model.

Judgment call: only class creation is tracked across a batch. A
relationship added earlier in the same utterance and referenced again
later in that same utterance (e.g. "create it, then immediately rename
it") is NOT visible to `_find_relationship` — it still resolves against
the document's state at the START of the request. This mirrors how the
class registry would behave if it only tracked names, not full model
deltas; relationships have no stable natural-language name to key a
registry on in general (unlike classes), so this narrower scope was kept
deliberately simple rather than simulating the whole handler pipeline
in-memory.
"""
import dataclasses
from collections.abc import Mapping

from apps.ai_assistant.errors import (
    AmbiguousRelationshipError,
    RelationshipNotFoundError,
    UnknownClassReferenceError,
    UnsupportedFunctionCallError,
)
from apps.ai_assistant.gemini_client import GeminiFunctionCall
from apps.uml_documents import schemas
from apps.uml_modeling.domain.elements import Relationship
from apps.uml_modeling.domain.ids import ElementId, new_id
from apps.uml_modeling.domain.model import CanonicalUmlModel


@dataclasses.dataclass(frozen=True)
class TranslatedCommand:
    """One successfully translated function call: the exact `CommandIn`
    `command_from_payload` expects, plus the human-readable description the
    API response reports back."""

    payload: "schemas.CommandIn"
    description: str


def _normalize(name: str) -> str:
    return name.strip().casefold()


class Translator:
    def __init__(self, model: CanonicalUmlModel):
        self._model = model
        self._name_to_id: dict[str, ElementId] = {
            _normalize(uml_class.name): uml_class.id for uml_class in model.classes
        }

    def translate(self, call: GeminiFunctionCall) -> TranslatedCommand:
        handler = _HANDLERS.get(call.name)
        if handler is None:
            raise UnsupportedFunctionCallError(call.name)
        return handler(self, call.args)

    def _resolve_class_id(self, name: str) -> ElementId:
        class_id = self._name_to_id.get(_normalize(name))
        if class_id is None:
            raise UnknownClassReferenceError(name)
        return class_id

    def _register_new_class(self, name: str) -> ElementId:
        class_id = new_id()
        self._name_to_id[_normalize(name)] = class_id
        return class_id

    def _find_relationship(
        self, source_name: str, target_name: str, kind: str | None
    ) -> Relationship:
        source_id = self._resolve_class_id(source_name)
        target_id = self._resolve_class_id(target_name)
        matches = [
            relationship
            for relationship in self._model.relationships
            if relationship.source.class_id == source_id
            and relationship.target.class_id == target_id
            and (kind is None or relationship.kind.value == kind)
        ]
        if not matches:
            raise RelationshipNotFoundError(source_name, target_name)
        if len(matches) > 1:
            raise AmbiguousRelationshipError(source_name, target_name, len(matches))
        return matches[0]


def _add_class(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    name = str(args["name"])
    class_id = translator._register_new_class(name)
    payload = schemas.AddClassIn(type="AddClass", class_id=class_id, name=name)
    return TranslatedCommand(payload, f"Created class {name!r}")


def _rename_class(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    class_name = str(args["class_name"])
    new_name = str(args["new_name"])
    class_id = translator._resolve_class_id(class_name)
    payload = schemas.RenameClassIn(type="RenameClass", class_id=class_id, new_name=new_name)
    return TranslatedCommand(payload, f"Renamed class {class_name!r} to {new_name!r}")


def _add_attribute(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    class_name = str(args["class_name"])
    attribute_name = str(args["attribute_name"])
    class_id = translator._resolve_class_id(class_name)
    visibility = str(args.get("visibility") or "private")
    payload = schemas.AddAttributeIn(
        type="AddAttribute",
        class_id=class_id,
        attribute=schemas.UmlAttributeIn(
            id=new_id(),
            name=attribute_name,
            type=str(args["attribute_type"]),
            visibility=visibility,
        ),
    )
    return TranslatedCommand(payload, f"Added attribute {attribute_name!r} to {class_name!r}")


def _remove_attribute(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    class_name = str(args["class_name"])
    attribute_name = str(args["attribute_name"])
    class_id = translator._resolve_class_id(class_name)
    uml_class = translator._model.class_by_id(class_id)
    attribute = next(
        (a for a in uml_class.attributes if _normalize(a.name) == _normalize(attribute_name)),
        None,
    )
    if attribute is None:
        raise UnknownClassReferenceError(f"{class_name}.{attribute_name}")
    payload = schemas.RemoveAttributeIn(
        type="RemoveAttribute", class_id=class_id, attribute_id=attribute.id
    )
    return TranslatedCommand(payload, f"Removed attribute {attribute_name!r} from {class_name!r}")


def _add_operation(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    class_name = str(args["class_name"])
    operation_name = str(args["operation_name"])
    class_id = translator._resolve_class_id(class_name)
    return_type = args.get("return_type")
    visibility = str(args.get("visibility") or "public")
    payload = schemas.AddOperationIn(
        type="AddOperation",
        class_id=class_id,
        operation=schemas.UmlOperationIn(
            id=new_id(),
            name=operation_name,
            return_type=str(return_type) if return_type else None,
            visibility=visibility,
        ),
    )
    return TranslatedCommand(payload, f"Added operation {operation_name!r} to {class_name!r}")


def _remove_operation(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    class_name = str(args["class_name"])
    operation_name = str(args["operation_name"])
    class_id = translator._resolve_class_id(class_name)
    uml_class = translator._model.class_by_id(class_id)
    operation = next(
        (o for o in uml_class.operations if _normalize(o.name) == _normalize(operation_name)),
        None,
    )
    if operation is None:
        raise UnknownClassReferenceError(f"{class_name}.{operation_name}")
    payload = schemas.RemoveOperationIn(
        type="RemoveOperation", class_id=class_id, operation_id=operation.id
    )
    return TranslatedCommand(payload, f"Removed operation {operation_name!r} from {class_name!r}")


def _add_relationship(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    source_name = str(args["source_class_name"])
    target_name = str(args["target_class_name"])
    kind = str(args["kind"])
    source_id = translator._resolve_class_id(source_name)
    target_id = translator._resolve_class_id(target_name)
    payload = schemas.AddRelationshipIn(
        type="AddRelationship",
        relationship=schemas.RelationshipIn(
            id=new_id(),
            kind=kind,
            source=schemas.RelationshipEndIn(
                class_id=source_id, multiplicity=str(args.get("source_multiplicity") or "0..1")
            ),
            target=schemas.RelationshipEndIn(
                class_id=target_id, multiplicity=str(args.get("target_multiplicity") or "0..*")
            ),
            name=args.get("name"),
        ),
    )
    return TranslatedCommand(
        payload, f"Added a {kind} relationship from {source_name!r} to {target_name!r}"
    )


def _remove_relationship(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    source_name = str(args["source_class_name"])
    target_name = str(args["target_class_name"])
    relationship = translator._find_relationship(source_name, target_name, args.get("kind"))
    payload = schemas.RemoveRelationshipIn(
        type="RemoveRelationship", relationship_id=relationship.id
    )
    return TranslatedCommand(
        payload, f"Removed the relationship between {source_name!r} and {target_name!r}"
    )


def _update_relationship(translator: Translator, args: Mapping[str, object]) -> TranslatedCommand:
    source_name = str(args["source_class_name"])
    target_name = str(args["target_class_name"])
    relationship = translator._find_relationship(source_name, target_name, args.get("kind"))
    kwargs: dict[str, object] = {"type": "UpdateRelationship", "relationship_id": relationship.id}
    # Only pass fields Gemini actually supplied (mirrors the manual UI's
    # `model_fields_set` omitted/explicit distinction in
    # `services._command_from_payload`): an absent key means "leave
    # unchanged", not "clear".
    if "name" in args:
        kwargs["name"] = args["name"]
    if "source_multiplicity" in args:
        kwargs["source_multiplicity"] = args["source_multiplicity"]
    if "target_multiplicity" in args:
        kwargs["target_multiplicity"] = args["target_multiplicity"]
    payload = schemas.UpdateRelationshipIn(**kwargs)
    return TranslatedCommand(
        payload, f"Updated the relationship between {source_name!r} and {target_name!r}"
    )


_HANDLERS = {
    "add_class": _add_class,
    "rename_class": _rename_class,
    "add_attribute": _add_attribute,
    "remove_attribute": _remove_attribute,
    "add_operation": _add_operation,
    "remove_operation": _remove_operation,
    "add_relationship": _add_relationship,
    "remove_relationship": _remove_relationship,
    "update_relationship": _update_relationship,
}
