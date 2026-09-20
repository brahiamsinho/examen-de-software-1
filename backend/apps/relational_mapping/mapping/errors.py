"""Defense-in-depth exceptions `map_to_relational` raises for the four
structures it cannot represent (design.md DD18). The primary line of
defense for the multi-parent case is the `MULTI_PARENT_GENERALIZATION`
validation rule (`apps.uml_modeling`); these exist so a caller that
bypasses validation fails loudly instead of the mapper silently
dropping a parent, a cycle member, an unresolved enum reference, or a
dangling relationship endpoint.
"""
from apps.uml_modeling.domain.ids import ElementId


class UnmappableModelError(Exception):
    """Base for every error `map_to_relational` raises."""


class MultipleGeneralizationParentsError(UnmappableModelError):
    def __init__(self, class_id: ElementId, parent_ids: tuple[ElementId, ...]):
        self.class_id = class_id
        self.parent_ids = tuple(parent_ids)
        super().__init__(
            f"Class {class_id!r} has multiple generalization parents: {self.parent_ids!r}"
        )


class GeneralizationCycleError(UnmappableModelError):
    def __init__(self, class_ids: tuple[ElementId, ...]):
        self.class_ids = tuple(class_ids)
        super().__init__(f"Generalization cycle detected among classes: {self.class_ids!r}")


class UnknownEnumerationError(UnmappableModelError):
    def __init__(self, attribute_id: ElementId, enumeration_id: ElementId):
        self.attribute_id = attribute_id
        self.enumeration_id = enumeration_id
        super().__init__(
            f"Attribute {attribute_id!r} references unknown enumeration {enumeration_id!r}"
        )


class DanglingRelationshipEndpointError(UnmappableModelError):
    def __init__(self, relationship_id: ElementId):
        self.relationship_id = relationship_id
        super().__init__(f"Relationship {relationship_id!r} has a dangling endpoint")


class InvalidGenerationProfileError(UnmappableModelError):
    """A `"profile"` entry of `generation_metadata` is malformed (DD136).
    Raised for the first offending entry, before any table work.
    """

    def __init__(self, element_id: ElementId, reason: str, key: str | None = None):
        self.element_id = element_id
        self.key = key
        self.reason = reason
        if key is None:
            super().__init__(f"Invalid generation profile for element {element_id!r}: {reason}")
        else:
            super().__init__(
                f"Invalid generation profile for element {element_id!r}, key {key!r}: {reason}"
            )
