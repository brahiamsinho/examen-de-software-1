"""Gemini function-declaration schema.

Plain dicts (a JSON-Schema-shaped `parameters`), not `google.genai.types`
objects — `google.genai.types.Tool(function_declarations=TOOLS)` accepts
this shape directly, and keeping it as plain dicts means `translator.py`
and its tests never need the `google-genai` package importable.

Reasons in names, never raw element ids (design.md): Gemini reasons about
the diagram in natural language, so every function signature below takes
class/attribute/operation/relationship *names* as strings; `translator.py`
resolves those names to the document's real `ElementId`s.

Only 9 of the 11 `UmlCommand`s are exposed (a documented judgment call,
also called out in the implementation handoff): `RemoveClass` is left out
because a misheard class name would silently delete a whole class and
cascade-remove every relationship touching it — too destructive a blast
radius for a voice channel with no undo. `SetGenerationProfile` is a
low-level backend-generation knob (JPA/DB profile keys) nobody naturally
describes in spoken language, so it stays manual-UI-only.
"""
from apps.uml_modeling.domain.types import PrimitiveType

_VISIBILITIES = ["public", "private", "protected", "package"]
_ATTRIBUTE_TYPES = [member.value for member in PrimitiveType]
_RELATIONSHIP_KINDS = ["association", "aggregation", "composition", "generalization"]
_MULTIPLICITY_DESCRIPTION = (
    "UML multiplicity: one of '1', '0..1', '0..*', '1..*' (also accepts a bare "
    "number or 'n..m')."
)

ADD_CLASS = {
    "name": "add_class",
    "description": "Create a new UML class with the given name.",
    "parameters": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "The new class's name."}},
        "required": ["name"],
    },
}

RENAME_CLASS = {
    "name": "rename_class",
    "description": "Rename an existing UML class.",
    "parameters": {
        "type": "object",
        "properties": {
            "class_name": {"type": "string", "description": "The existing class's current name."},
            "new_name": {"type": "string", "description": "The class's new name."},
        },
        "required": ["class_name", "new_name"],
    },
}

ADD_ATTRIBUTE = {
    "name": "add_attribute",
    "description": "Add an attribute (field) to an existing UML class.",
    "parameters": {
        "type": "object",
        "properties": {
            "class_name": {"type": "string", "description": "The class to add the attribute to."},
            "attribute_name": {"type": "string", "description": "The new attribute's name."},
            "attribute_type": {
                "type": "string",
                "enum": _ATTRIBUTE_TYPES,
                "description": "The attribute's primitive type.",
            },
            "visibility": {
                "type": "string",
                "enum": _VISIBILITIES,
                "description": "Defaults to 'private' if not stated.",
            },
        },
        "required": ["class_name", "attribute_name", "attribute_type"],
    },
}

REMOVE_ATTRIBUTE = {
    "name": "remove_attribute",
    "description": "Remove an existing attribute from a UML class.",
    "parameters": {
        "type": "object",
        "properties": {
            "class_name": {"type": "string"},
            "attribute_name": {"type": "string"},
        },
        "required": ["class_name", "attribute_name"],
    },
}

ADD_OPERATION = {
    "name": "add_operation",
    "description": "Add an operation (method) to an existing UML class.",
    "parameters": {
        "type": "object",
        "properties": {
            "class_name": {"type": "string"},
            "operation_name": {"type": "string"},
            "return_type": {
                "type": "string",
                "enum": _ATTRIBUTE_TYPES,
                "description": "Omit for a void operation.",
            },
            "visibility": {
                "type": "string",
                "enum": _VISIBILITIES,
                "description": "Defaults to 'public' if not stated.",
            },
        },
        "required": ["class_name", "operation_name"],
    },
}

REMOVE_OPERATION = {
    "name": "remove_operation",
    "description": "Remove an existing operation from a UML class.",
    "parameters": {
        "type": "object",
        "properties": {
            "class_name": {"type": "string"},
            "operation_name": {"type": "string"},
        },
        "required": ["class_name", "operation_name"],
    },
}

ADD_RELATIONSHIP = {
    "name": "add_relationship",
    "description": "Create a relationship between two existing (or just-created) UML classes.",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": _RELATIONSHIP_KINDS},
            "source_class_name": {
                "type": "string",
                "description": "For 'generalization', the specific (child) class.",
            },
            "target_class_name": {
                "type": "string",
                "description": "For 'generalization', the general (parent) class.",
            },
            "source_multiplicity": {"type": "string", "description": _MULTIPLICITY_DESCRIPTION},
            "target_multiplicity": {"type": "string", "description": _MULTIPLICITY_DESCRIPTION},
            "name": {"type": "string", "description": "Optional relationship name/label."},
        },
        "required": ["kind", "source_class_name", "target_class_name"],
    },
}

REMOVE_RELATIONSHIP = {
    "name": "remove_relationship",
    "description": (
        "Remove an existing relationship between two classes. If more than one "
        "relationship connects them, also state 'kind' to disambiguate."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "source_class_name": {"type": "string"},
            "target_class_name": {"type": "string"},
            "kind": {"type": "string", "enum": _RELATIONSHIP_KINDS},
        },
        "required": ["source_class_name", "target_class_name"],
    },
}

UPDATE_RELATIONSHIP = {
    "name": "update_relationship",
    "description": (
        "Change an existing relationship's name and/or multiplicities. If more than "
        "one relationship connects the two classes, also state 'kind' to disambiguate."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "source_class_name": {"type": "string"},
            "target_class_name": {"type": "string"},
            "kind": {"type": "string", "enum": _RELATIONSHIP_KINDS},
            "name": {"type": "string", "description": "The relationship's new name."},
            "source_multiplicity": {"type": "string", "description": _MULTIPLICITY_DESCRIPTION},
            "target_multiplicity": {"type": "string", "description": _MULTIPLICITY_DESCRIPTION},
        },
        "required": ["source_class_name", "target_class_name"],
    },
}

TOOLS = [
    ADD_CLASS,
    RENAME_CLASS,
    ADD_ATTRIBUTE,
    REMOVE_ATTRIBUTE,
    ADD_OPERATION,
    REMOVE_OPERATION,
    ADD_RELATIONSHIP,
    REMOVE_RELATIONSHIP,
    UPDATE_RELATIONSHIP,
]
