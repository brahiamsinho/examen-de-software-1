"use client";

import { AlertCircle, CheckCircle2, Download, LoaderCircle, ScanSearch, TriangleAlert } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import {
  downloadArchitectureAudit,
  getArchitectureAudit,
  type ArchitectureAuditFinding,
  type ArchitectureAuditReport,
} from "@/lib/architecture_audit";

type ArchitectureAuditPanelProps = {
  orgSlug: string;
  docId: string;
  documentName: string;
};

function severityClass(severity: ArchitectureAuditFinding["severity"]): string {
  if (severity === "ERROR") return "text-destructive";
  if (severity === "WARNING") return "text-amber-700 dark:text-amber-400";
  return "text-primary";
}

export function ArchitectureAuditPanel({ orgSlug, docId, documentName }: ArchitectureAuditPanelProps) {
  const [report, setReport] = useState<ArchitectureAuditReport | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runAudit() {
    setPending(true);
    setError(null);
    try {
      setReport(await getArchitectureAudit(orgSlug, docId));
    } catch (err) {
      setReport(null);
      setError(err instanceof ApiError ? err.detail : "No se pudo ejecutar la auditoría. Intenta de nuevo.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-heading text-base font-semibold">Auditoría arquitectónica</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Evalúa riesgos estructurales del modelo actual. No modifica el diagrama ni sustituye la validación UML.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={runAudit} disabled={pending}>
          {pending ? <LoaderCircle className="animate-spin" /> : <ScanSearch />}
          {pending ? "Auditando..." : report === null ? "Ejecutar auditoría" : "Actualizar"}
        </Button>
      </div>

      {error ? <Alert variant="destructive"><AlertCircle /><AlertDescription>{error}</AlertDescription></Alert> : null}

      {report ? (
        <>
          <div className="flex flex-wrap gap-2 text-xs">
            {(["ERROR", "WARNING", "INFO"] as const).map((severity) => (
              <span key={severity} className="rounded-full border border-border px-2 py-1">
                <span className={severityClass(severity)}>{severity}</span>: {report.summary[severity]}
              </span>
            ))}
            <span className="ml-auto text-muted-foreground">Reglas {report.rules_version} · revisión {report.document.revision}</span>
          </div>

          {report.findings.length === 0 ? (
            <Alert variant="success"><CheckCircle2 /><AlertDescription>No se encontraron riesgos arquitectónicos con las reglas actuales.</AlertDescription></Alert>
          ) : report.findings.map((finding) => (
            <section key={finding.id} className="flex flex-col gap-2 rounded-lg border border-border p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <TriangleAlert className={severityClass(finding.severity)} aria-hidden="true" />
                <h3 className="font-semibold">{finding.title}</h3>
                <span className={`font-mono text-xs ${severityClass(finding.severity)}`}>{finding.severity}</span>
              </div>
              <p className="text-muted-foreground">{finding.explanation}</p>
              <p><span className="font-medium">Regla {finding.rule_id} · {finding.rule_name}:</span> {finding.rule_purpose}</p>
              <p><span className="font-medium">Evidencia:</span> {finding.evidence}</p>
              <p><span className="font-medium">Recomendación:</span> {finding.recommendation}</p>
              <p className="font-mono text-xs text-muted-foreground">Elementos: {finding.element_ids.join(", ")}</p>
            </section>
          ))}

          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="outline" onClick={() => downloadArchitectureAudit(report, documentName, "json")}>
              <Download />Descargar JSON
            </Button>
            <Button type="button" size="sm" variant="outline" onClick={() => downloadArchitectureAudit(report, documentName, "markdown")}>
              <Download />Descargar Markdown
            </Button>
          </div>
        </>
      ) : null}
    </div>
  );
}
