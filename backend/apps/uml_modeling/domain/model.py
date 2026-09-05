"""The canonical UML model: the single convergence point every manual,
voice, image, and XMI input channel normalizes to.
"""
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from apps.uml_modeling.domain.elements import Enumeration, Relationship, UmlClass
from apps.uml_modeling.domain.ids import ElementId


@dataclass(frozen=True)
class CanonicalUmlModel:
    """A flat (no `Package`), DB-free UML model.

    `generation_metadata` is a structurally separate, opaque container
    keyed by element id: it never adds a field to any UML element
    dataclass, keeping pure UML elements free of generation concerns.
    """

    classes: tuple[UmlClass, ...] = ()
    enumerations: tuple[Enumeration, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    generation_metadata: Mapping[ElementId, Mapping[str, object]] = field(default_factory=dict)

    def class_by_id(self, class_id: ElementId) -> UmlClass | None:
        for uml_class in self.classes:
            if uml_class.id == class_id:
                return uml_class
        return None

    def enumeration_by_id(self, enumeration_id: ElementId) -> Enumeration | None:
        for enumeration in self.enumerations:
            if enumeration.id == enumeration_id:
                return enumeration
        return None

    def iter_named_elements(self) -> Iterable[object]:
        """Yield every named element in the model: classes and their
        attributes/operations, enumerations and their literals.
        """
        for uml_class in self.classes:
            yield uml_class
            yield from uml_class.attributes
            yield from uml_class.operations
        for enumeration in self.enumerations:
            yield enumeration
            yield from enumeration.literals


UmlModel = CanonicalUmlModel
