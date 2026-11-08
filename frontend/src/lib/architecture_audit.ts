import { apiFetch } from "@/lib/api";
import { saveBlobAsFile } from "@/lib/save_blob";

export type ArchitectureAuditSeverity = "ERROR" | "WARNING" | "INFO";

export type ArchitectureAuditFinding = {
  id: string;
  rule_id: string;
  rule_name: string;
  rule_purpose: string;
  severity: ArchitectureAuditSeverity;
  title: string;
  explanation: string;
  evidence: string;
  element_ids: string[];
  recommendation: string;
};

export type ArchitectureAuditReport = {
  contract_version: string;
  rules_version: string;
  document: { id: string; revision: number };
  summary: Record<ArchitectureAuditSeverity, number>;
  findings: ArchitectureAuditFinding[];
};

export function getArchitectureAudit(orgSlug: string, docId: string): Promise<ArchitectureAuditReport> {
  return apiFetch<ArchitectureAuditReport>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/architecture-audit`,
  );
}

function fileStem(documentName: string): string {
  return documentName.trim().replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase() || "modelia";
}

export function downloadArchitectureAudit(report: ArchitectureAuditReport, documentName: string, format: "json" | "markdown"): void {
  const body = format === "json" ? `${JSON.stringify(report, null, 2)}\n` : markdown(report);
  saveBlobAsFile(
    new Blob([body], { type: format === "json" ? "application/json;charset=utf-8" : "text/markdown;charset=utf-8" }),
    `${fileStem(documentName)}-architecture-audit.${format === "json" ? "json" : "md"}`,
  );
}

function markdown(report: ArchitectureAuditReport): string {
  const lines = [
    "# Auditoria arquitectonica",
    "",
    `- Documento: \`${report.document.id}\``,
    `- Revision: ${report.document.revision}`,
    `- Contrato: ${report.contract_version}`,
    `- Reglas: ${report.rules_version}`,
    `- Resumen: ERROR ${report.summary.ERROR}, WARNING ${report.summary.WARNING}, INFO ${report.summary.INFO}`,
    "",
  ];
  if (report.findings.length === 0) return `${lines.join("\n")}No se encontraron hallazgos arquitectonicos.\n`;
  for (const finding of report.findings) {
    lines.push(
      `## [${finding.severity}] ${finding.title}`,
      "",
      `- Id: \`${finding.id}\``,
      `- Regla: \`${finding.rule_id}\` - ${finding.rule_name}`,
      `- Proposito de la regla: ${finding.rule_purpose}`,
      `- Explicacion: ${finding.explanation}`,
      `- Evidencia: ${finding.evidence}`,
      `- Elementos: ${finding.element_ids.map((id) => `\`${id}\``).join(", ")}`,
      `- Recomendacion: ${finding.recommendation}`,
      "",
    );
  }
  return lines.join("\n");
}
