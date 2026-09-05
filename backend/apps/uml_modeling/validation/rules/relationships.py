"""Relationship rules: dangling endpoints, generalization cycles, and
self-associations.
"""
from collections import defaultdict

from apps.uml_modeling.domain.elements import RelationshipKind
from apps.uml_modeling.domain.ids import ElementId
from apps.uml_modeling.domain.model import CanonicalUmlModel
from apps.uml_modeling.validation.diagnostics import (
    Diagnostic,
    DiagnosticCode,
    ElementKind,
    ElementRef,
    Severity,
    class_path,
    relationship_path,
)

_WHITE, _GRAY, _BLACK = 0, 1, 2


def invalid_relationship_endpoint(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag every relationship whose source or target id does not match
    any class in the model.
    """
    known_class_ids = {uml_class.id for uml_class in model.classes}

    diagnostics: list[Diagnostic] = []
    for relationship in model.relationships:
        if (
            relationship.source.class_id in known_class_ids
            and relationship.target.class_id in known_class_ids
        ):
            continue
        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                code=DiagnosticCode.INVALID_RELATIONSHIP_ENDPOINT,
                message=f"Relationship {relationship.id!r} has an endpoint outside the model",
                path=relationship_path(relationship.id),
                element_ref=ElementRef(kind=ElementKind.RELATIONSHIP, id=relationship.id),
            )
        )
    return tuple(diagnostics)


def generalization_cycle(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Detect cycles in the child->parent generalization digraph.

    `GENERALIZATION` direction is normative: `source` is the specific
    (child) class, `target` is the general (parent) class (see
    `domain/elements.py::Relationship`). Emits exactly one diagnostic
    per detected cycle, anchored at the lowest-sorted participating
    class id, so the count is deterministic regardless of cycle size.
    A self-generalization (`source == target`) is a length-1 cycle.
    """
    children_of: dict[ElementId, list[ElementId]] = defaultdict(list)
    for relationship in model.relationships:
        if relationship.kind is RelationshipKind.GENERALIZATION:
            children_of[relationship.source.class_id].append(relationship.target.class_id)

    color: dict[ElementId, int] = {}
    reported_cycles: set[frozenset[ElementId]] = set()
    diagnostics: list[Diagnostic] = []

    for start in list(children_of):
        if color.get(start, _WHITE) != _WHITE:
            continue

        path: list[ElementId] = [start]
        color[start] = _GRAY
        frames = [iter(children_of.get(start, ()))]

        while frames:
            try:
                child = next(frames[-1])
            except StopIteration:
                color[path.pop()] = _BLACK
                frames.pop()
                continue

            state = color.get(child, _WHITE)
            if state == _GRAY:
                cycle_members = path[path.index(child):]
                key = frozenset(cycle_members)
                if key not in reported_cycles:
                    reported_cycles.add(key)
                    anchor = min(cycle_members)
                    diagnostics.append(
                        Diagnostic(
                            severity=Severity.ERROR,
                            code=DiagnosticCode.GENERALIZATION_CYCLE,
                            message="Generalization cycle detected",
                            path=class_path(anchor),
                            element_ref=ElementRef(kind=ElementKind.CLASS, id=anchor),
                        )
                    )
            elif state == _WHITE:
                color[child] = _GRAY
                path.append(child)
                frames.append(iter(children_of.get(child, ())))
            # _BLACK: already fully explored, no new cycle through this edge

    return tuple(diagnostics)


def self_association(model: CanonicalUmlModel) -> tuple[Diagnostic, ...]:
    """Flag an `ASSOCIATION` relationship whose source and target are
    the same class. Scoped to `ASSOCIATION` only: a self-generalization
    is reported by `generalization_cycle` instead (never both).
    """
    diagnostics: list[Diagnostic] = []
    for relationship in model.relationships:
        if relationship.kind is not RelationshipKind.ASSOCIATION:
            continue
        if relationship.source.class_id != relationship.target.class_id:
            continue
        diagnostics.append(
            Diagnostic(
                severity=Severity.WARNING,
                code=DiagnosticCode.SELF_ASSOCIATION,
                message=f"Association {relationship.id!r} references the same class as both ends",
                path=relationship_path(relationship.id),
                element_ref=ElementRef(kind=ElementKind.RELATIONSHIP, id=relationship.id),
            )
        )
    return tuple(diagnostics)
