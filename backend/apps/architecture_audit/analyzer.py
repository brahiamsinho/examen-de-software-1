"""Pure architectural audit rules over the canonical UML model.

This module intentionally has no Django, HTTP, persistence, clock, random, or
LLM dependency. Formal UML validation remains in ``uml_modeling.validation``;
these findings describe design risks only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json

from apps.uml_modeling.domain.elements import RelationshipKind, UmlClass
from apps.uml_modeling.domain.model import CanonicalUmlModel

REPORT_CONTRACT_VERSION = "1.0"
RULES_VERSION = "1.0"


@dataclass(frozen=True)
class AuditRule:
    id: str
    name: str
    purpose: str
    severity: str
    threshold: int | None
    limitation: str


@dataclass(frozen=True)
class Finding:
    id: str
    rule_id: str
    rule_name: str
    rule_purpose: str
    severity: str
    title: str
    explanation: str
    evidence: str
    element_ids: tuple[str, ...]
    recommendation: str


RULES = (
    AuditRule(
        id="AR-001",
        name="Clase aislada",
        purpose="Detecta clases que no participan en ninguna relación del modelo.",
        severity="INFO",
        threshold=None,
        limitation="Una clase de valor o un diseño incompleto puede estar aislado intencionalmente.",
    ),
    AuditRule(
        id="AR-002",
        name="Acoplamiento elevado",
        purpose="Detecta clases conectadas con muchas relaciones directas.",
        severity="WARNING",
        threshold=5,
        limitation="El conteo no pondera el tipo, dirección ni importancia de cada relación.",
    ),
    AuditRule(
        id="AR-003",
        name="Jerarquía de herencia profunda",
        purpose="Detecta cadenas de generalización difíciles de comprender o mantener.",
        severity="WARNING",
        threshold=4,
        limitation="Solo cuenta generalizaciones presentes en el diagrama; no conoce comportamiento heredado real.",
    ),
    AuditRule(
        id="AR-004",
        name="Clase sobredimensionada",
        purpose="Detecta clases con muchos atributos u operaciones como señal de responsabilidad amplia.",
        severity="WARNING",
        threshold=10,
        limitation="No mide complejidad interna, visibilidad ni el contenido de las operaciones.",
    ),
    AuditRule(
        id="AR-005",
        name="Dependencia cíclica",
        purpose="Detecta ciclos dirigidos entre relaciones no generalización.",
        severity="WARNING",
        threshold=None,
        limitation="Las asociaciones UML pueden ser bidireccionales por intención; revise el contexto antes de refactorizar.",
    ),
)

RULE_BY_ID = {rule.id: rule for rule in RULES}


def _finding(rule_id: str, title: str, explanation: str, evidence: str, element_ids: tuple[str, ...], recommendation: str) -> Finding:
    rule = RULE_BY_ID[rule_id]
    stable_input = json.dumps(
        {"rule_id": rule_id, "element_ids": element_ids, "evidence": evidence},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return Finding(
        id=f"{rule_id.lower()}-{sha256(stable_input.encode()).hexdigest()[:16]}",
        rule_id=rule_id,
        rule_name=rule.name,
        rule_purpose=rule.purpose,
        severity=rule.severity,
        title=title,
        explanation=explanation,
        evidence=evidence,
        element_ids=element_ids,
        recommendation=recommendation,
    )


def _classes(model: CanonicalUmlModel) -> tuple[UmlClass, ...]:
    return tuple(sorted(model.classes, key=lambda uml_class: (uml_class.name.casefold(), str(uml_class.id))))


def _strongly_connected_components(graph: dict[str, tuple[str, ...]]) -> tuple[tuple[str, ...], ...]:
    """Tarjan's algorithm with sorted traversal for deterministic components."""
    index = 0
    indexes: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    in_stack: set[str] = set()
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indexes[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        in_stack.add(node)
        for adjacent in graph[node]:
            if adjacent not in indexes:
                visit(adjacent)
                lowlinks[node] = min(lowlinks[node], lowlinks[adjacent])
            elif adjacent in in_stack:
                lowlinks[node] = min(lowlinks[node], indexes[adjacent])
        if lowlinks[node] == indexes[node]:
            component: list[str] = []
            while True:
                adjacent = stack.pop()
                in_stack.remove(adjacent)
                component.append(adjacent)
                if adjacent == node:
                    break
            components.append(tuple(sorted(component)))

    for node in sorted(graph):
        if node not in indexes:
            visit(node)
    return tuple(sorted(components))


def audit(model: CanonicalUmlModel) -> tuple[Finding, ...]:
    """Return stable architectural findings for one canonical UML model."""
    classes = _classes(model)
    class_names = {str(uml_class.id): uml_class.name for uml_class in classes}
    known_ids = set(class_names)
    relationships = tuple(
        sorted(
            (
                relationship
                for relationship in model.relationships
                if str(relationship.source.class_id) in known_ids and str(relationship.target.class_id) in known_ids
            ),
            key=lambda relationship: str(relationship.id),
        )
    )
    findings: list[Finding] = []

    incident_counts = {class_id: 0 for class_id in known_ids}
    for relationship in relationships:
        source_id, target_id = str(relationship.source.class_id), str(relationship.target.class_id)
        incident_counts[source_id] += 1
        if target_id != source_id:
            incident_counts[target_id] += 1
    for uml_class in classes:
        class_id = str(uml_class.id)
        if incident_counts[class_id] == 0:
            findings.append(_finding(
                "AR-001", f"{uml_class.name} no participa en relaciones",
                "La clase no está conectada con ninguna otra clase mediante una relación UML.",
                f"Clase {uml_class.name} ({class_id}) con 0 relaciones incidentes.",
                (class_id,),
                "Confirma si representa un concepto independiente; si no, modela sus colaboraciones o elimina la clase innecesaria.",
            ))

    coupling_threshold = RULE_BY_ID["AR-002"].threshold
    assert coupling_threshold is not None
    for uml_class in classes:
        class_id = str(uml_class.id)
        count = incident_counts[class_id]
        if count >= coupling_threshold:
            findings.append(_finding(
                "AR-002", f"{uml_class.name} tiene acoplamiento elevado",
                "La clase participa directamente en muchas relaciones, lo que puede concentrar dependencias.",
                f"Clase {uml_class.name} ({class_id}) con {count} relaciones incidentes; umbral {coupling_threshold}.",
                (class_id,),
                "Evalúa si sus responsabilidades pueden dividirse o si algunas relaciones pueden encapsularse tras una abstracción.",
            ))

    size_threshold = RULE_BY_ID["AR-004"].threshold
    assert size_threshold is not None
    for uml_class in classes:
        class_id = str(uml_class.id)
        members = len(uml_class.attributes) + len(uml_class.operations)
        if members >= size_threshold:
            findings.append(_finding(
                "AR-004", f"{uml_class.name} concentra muchos miembros",
                "Una clase con muchos atributos u operaciones puede reunir responsabilidades no relacionadas.",
                f"Clase {uml_class.name} ({class_id}) con {len(uml_class.attributes)} atributos y {len(uml_class.operations)} operaciones ({members} miembros); umbral {size_threshold}.",
                (class_id,),
                "Revisa cohesión y extrae responsabilidades que cambien por motivos distintos.",
            ))

    parents = {class_id: [] for class_id in known_ids}
    for relationship in relationships:
        if relationship.kind == RelationshipKind.GENERALIZATION:
            parents[str(relationship.source.class_id)].append(str(relationship.target.class_id))
    for child_id in parents:
        parents[child_id].sort()

    def depth(class_id: str, trail: tuple[str, ...] = ()) -> int:
        if class_id in trail:
            return 0  # Formal validation owns generalization-cycle diagnostics.
        return max((1 + depth(parent, trail + (class_id,)) for parent in parents[class_id]), default=0)

    depth_threshold = RULE_BY_ID["AR-003"].threshold
    assert depth_threshold is not None
    for uml_class in classes:
        class_id = str(uml_class.id)
        inheritance_depth = depth(class_id)
        if inheritance_depth >= depth_threshold:
            findings.append(_finding(
                "AR-003", f"{uml_class.name} está en una jerarquía profunda",
                "Las cadenas de herencia largas incrementan el contexto necesario para comprender una clase.",
                f"Clase {uml_class.name} ({class_id}) a profundidad de herencia {inheritance_depth}; umbral {depth_threshold}.",
                (class_id,),
                "Considera composición, interfaces o agrupar comportamiento común en una jerarquía menos profunda.",
            ))

    graph = {class_id: [] for class_id in known_ids}
    for relationship in relationships:
        if relationship.kind != RelationshipKind.GENERALIZATION:
            graph[str(relationship.source.class_id)].append(str(relationship.target.class_id))
    normalized_graph = {class_id: tuple(sorted(set(targets))) for class_id, targets in graph.items()}
    for component in _strongly_connected_components(normalized_graph):
        has_self_cycle = len(component) == 1 and component[0] in normalized_graph[component[0]]
        if len(component) > 1 or has_self_cycle:
            names = ", ".join(class_names[class_id] for class_id in component)
            findings.append(_finding(
                "AR-005", "Se detectó una dependencia cíclica",
                "Las relaciones no generalización forman un ciclo dirigido entre estas clases.",
                f"Ciclo entre {names}; clases: {', '.join(component)}.",
                component,
                "Evalúa si una interfaz, un servicio intermedio o una inversión de dependencia puede romper el ciclo.",
            ))

    return tuple(sorted(findings, key=lambda finding: (finding.rule_id, finding.element_ids, finding.id)))


def report(model: CanonicalUmlModel, *, document_id: str, revision: int) -> dict:
    findings = audit(model)
    summary = {severity: sum(finding.severity == severity for finding in findings) for severity in ("ERROR", "WARNING", "INFO")}
    return {
        "contract_version": REPORT_CONTRACT_VERSION,
        "rules_version": RULES_VERSION,
        "document": {"id": document_id, "revision": revision},
        "summary": summary,
        "findings": [asdict(finding) for finding in findings],
    }
