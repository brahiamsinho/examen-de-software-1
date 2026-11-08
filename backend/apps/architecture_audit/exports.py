"""Stable human-readable export for architecture audit reports."""
from __future__ import annotations


def markdown(report: dict) -> str:
    document = report["document"]
    summary = report["summary"]
    lines = [
        "# Auditoria arquitectonica",
        "",
        f"- Documento: `{document['id']}`",
        f"- Revision: {document['revision']}",
        f"- Contrato: {report['contract_version']}",
        f"- Reglas: {report['rules_version']}",
        f"- Resumen: ERROR {summary['ERROR']}, WARNING {summary['WARNING']}, INFO {summary['INFO']}",
        "",
    ]
    if not report["findings"]:
        return "\n".join(lines + ["No se encontraron hallazgos arquitectonicos.", ""])
    for finding in report["findings"]:
        lines.extend((
            f"## [{finding['severity']}] {finding['title']}",
            "",
            f"- Id: `{finding['id']}`",
            f"- Regla: `{finding['rule_id']}` - {finding['rule_name']}",
            f"- Proposito de la regla: {finding['rule_purpose']}",
            f"- Explicacion: {finding['explanation']}",
            f"- Evidencia: {finding['evidence']}",
            f"- Elementos: {', '.join(f'`{element_id}`' for element_id in finding['element_ids'])}",
            f"- Recomendacion: {finding['recommendation']}",
            "",
        ))
    return "\n".join(lines)
