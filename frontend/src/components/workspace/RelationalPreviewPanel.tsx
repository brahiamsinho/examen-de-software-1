"use client";

import { AlertCircle, Check, Copy, Database, Download, LoaderCircle } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import {
  downloadRelationalSql,
  getRelationalPreview,
  type RelationalPreview,
} from "@/lib/relational_preview";

type RelationalPreviewPanelProps = {
  orgSlug: string;
  docId: string;
  documentName: string;
};

export function RelationalPreviewPanel({ orgSlug, docId, documentName }: RelationalPreviewPanelProps) {
  const [preview, setPreview] = useState<RelationalPreview | null>(null);
  const [pending, setPending] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadPreview() {
    setPending(true);
    setError(null);
    try {
      setPreview(await getRelationalPreview(orgSlug, docId));
    } catch (err) {
      setPreview(null);
      setError(err instanceof ApiError ? err.detail : "No se pudo cargar la vista previa. Intenta de nuevo.");
    } finally {
      setPending(false);
    }
  }

  async function copySql() {
    if (preview === null) return;
    try {
      await navigator.clipboard.writeText(preview.sql);
      setCopied(true);
    } catch {
      setError("No se pudo copiar el SQL. Selecciónalo manualmente para copiarlo.");
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-heading text-base font-semibold">Vista previa relacional</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Derivada del diagrama actual. No crea tablas ni modifica el documento.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={loadPreview} disabled={pending}>
          {pending ? <LoaderCircle className="animate-spin" /> : <Database />}
          {pending ? "Generando..." : preview === null ? "Generar vista previa" : "Actualizar"}
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      {preview?.tables.map((table) => (
        <section key={table.name} className="overflow-hidden rounded-lg border border-border">
          <h3 className="border-b border-border bg-muted/40 px-3 py-2 font-mono text-sm font-semibold">{table.name}</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-muted-foreground">
                <tr><th className="px-3 py-2 font-medium">Columna</th><th className="px-3 py-2 font-medium">Tipo</th><th className="px-3 py-2 font-medium">Claves</th></tr>
              </thead>
              <tbody>
                {table.columns.map((column) => {
                  const foreignKey = table.foreign_keys.find((key) => key.columns.includes(column.name));
                  return (
                    <tr key={column.name} className="border-t border-border/60">
                      <td className="px-3 py-2 font-mono">{column.name}</td>
                      <td className="px-3 py-2 font-mono text-muted-foreground">{column.type}{column.nullable ? "" : " NOT NULL"}</td>
                      <td className="px-3 py-2">{column.primary_key ? <span className="font-medium text-primary">PK</span> : null}{column.primary_key && foreignKey ? " · " : null}{foreignKey ? <span className="font-medium text-amber-700 dark:text-amber-400">FK → {foreignKey.referenced_table}</span> : null}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {table.foreign_keys.length > 0 ? (
            <p className="border-t border-border bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
              {table.foreign_keys.map((key) => `${key.columns.join(", ")} → ${key.referenced_table} (${key.on_delete})`).join("; ")}
            </p>
          ) : null}
        </section>
      ))}

      {preview ? (
        <section className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-heading text-sm font-semibold">SQL PostgreSQL</h3>
            <div className="flex gap-2">
              <Button type="button" size="sm" variant="outline" onClick={copySql}>
                {copied ? <Check /> : <Copy />}{copied ? "Copiado" : "Copiar SQL"}
              </Button>
              <Button type="button" size="sm" variant="outline" onClick={() => downloadRelationalSql(preview.sql, documentName)}>
                <Download />Descargar SQL
              </Button>
            </div>
          </div>
          <pre className="max-h-80 overflow-auto rounded-lg border border-border bg-muted/40 p-3 text-xs leading-5"><code>{preview.sql}</code></pre>
        </section>
      ) : null}
    </div>
  );
}
