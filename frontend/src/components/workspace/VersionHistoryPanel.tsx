"use client";

import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import {
  compareVersions,
  createTemplate,
  createVersion,
  listVersions,
  restoreVersion,
  type UmlVersionSummary,
  type VersionChange,
  type VersionDiff,
} from "@/lib/uml_documents";

type Props = {
  orgSlug: string;
  docId: string;
  revision: number;
  canEdit: boolean;
  onRestored: () => Promise<void>;
};

function describe(change: VersionChange): string {
  return change.class_name ? `${change.class_name}.${change.name ?? change.id}` : (change.name ?? change.id);
}

function ChangeList({ title, changes }: { title: string; changes: { added: VersionChange[]; removed: VersionChange[] } }) {
  if (changes.added.length === 0 && changes.removed.length === 0) return null;
  return (
    <div className="text-sm">
      <p className="font-medium">{title}</p>
      {changes.added.map((change) => <p key={`add-${change.id}`} className="text-success">+ {describe(change)}</p>)}
      {changes.removed.map((change) => <p key={`remove-${change.id}`} className="text-destructive">− {describe(change)}</p>)}
    </div>
  );
}

export function VersionHistoryPanel({ orgSlug, docId, revision, canEdit, onRestored }: Props) {
  const [versions, setVersions] = useState<UmlVersionSummary[]>([]);
  const [description, setDescription] = useState("");
  const [templateName, setTemplateName] = useState("");
  const [fromId, setFromId] = useState("");
  const [toId, setToId] = useState("");
  const [diff, setDiff] = useState<VersionDiff | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    try {
      const next = await listVersions(orgSlug, docId);
      setVersions(next);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo cargar el historial.");
    }
  }

  useEffect(() => {
    let cancelled = false;
    void listVersions(orgSlug, docId)
      .then((next) => {
        if (!cancelled) {
          setVersions(next);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "No se pudo cargar el historial.");
      });
    return () => { cancelled = true; };
  }, [orgSlug, docId, revision]);

  async function saveVersion() {
    setBusy(true);
    try {
      await createVersion(orgSlug, docId, { description, expected_revision: revision });
      setDescription("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo guardar la versión.");
    } finally {
      setBusy(false);
    }
  }

  async function publishTemplate() {
    if (!templateName.trim()) return;
    setBusy(true);
    try {
      await createTemplate(orgSlug, docId, { name: templateName.trim() });
      setTemplateName("");
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo guardar la plantilla.");
    } finally {
      setBusy(false);
    }
  }

  async function showDiff() {
    if (!fromId || !toId || fromId === toId) return;
    setBusy(true);
    try {
      setDiff(await compareVersions(orgSlug, docId, fromId, toId));
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudieron comparar las versiones.");
    } finally {
      setBusy(false);
    }
  }

  async function restore(version: UmlVersionSummary) {
    if (!window.confirm(`Se restaurará la versión ${version.number} como una nueva revisión. ¿Continuar?`)) return;
    setBusy(true);
    try {
      await restoreVersion(orgSlug, docId, version.id, revision);
      await onRestored();
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo restaurar la versión.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {canEdit ? (
        <div className="flex gap-2">
          <input aria-label="Descripción de versión" className="min-w-0 flex-1 rounded-md border bg-background px-3 py-2 text-sm" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Descripción opcional" maxLength={500} />
          <Button type="button" onClick={saveVersion} disabled={busy}>Guardar versión</Button>
        </div>
      ) : null}
      {canEdit ? (
        <div className="flex gap-2">
          <input aria-label="Nombre de plantilla" className="min-w-0 flex-1 rounded-md border bg-background px-3 py-2 text-sm" value={templateName} onChange={(event) => setTemplateName(event.target.value)} placeholder="Nombre de plantilla" maxLength={255} />
          <Button type="button" variant="outline" onClick={publishTemplate} disabled={busy || !templateName.trim()}>Guardar plantilla</Button>
        </div>
      ) : null}
      {versions.length === 0 ? <p className="text-sm text-muted-foreground">Todavía no hay versiones guardadas.</p> : (
        <div className="flex flex-col gap-2">
          {versions.map((version) => (
            <div key={version.id} className="flex items-center justify-between gap-2 rounded-md border p-2 text-sm">
              <span>V{version.number} · revisión {version.source_revision}{version.description ? ` · ${version.description}` : ""}</span>
              {canEdit ? <Button type="button" variant="outline" size="sm" onClick={() => void restore(version)} disabled={busy}>Restaurar</Button> : null}
            </div>
          ))}
        </div>
      )}
      {versions.length > 1 ? (
        <div className="flex flex-wrap gap-2">
          <select aria-label="Versión inicial" className="rounded-md border bg-background px-2 text-sm" value={fromId} onChange={(event) => setFromId(event.target.value)}><option value="">Desde</option>{versions.map((version) => <option key={version.id} value={version.id}>V{version.number}</option>)}</select>
          <select aria-label="Versión final" className="rounded-md border bg-background px-2 text-sm" value={toId} onChange={(event) => setToId(event.target.value)}><option value="">Hasta</option>{versions.map((version) => <option key={version.id} value={version.id}>V{version.number}</option>)}</select>
          <Button type="button" variant="outline" onClick={showDiff} disabled={busy || !fromId || !toId || fromId === toId}>Comparar</Button>
        </div>
      ) : null}
      {diff ? <div className="flex flex-col gap-2 rounded-md bg-muted/40 p-3"><ChangeList title="Clases" changes={diff.classes} /><ChangeList title="Atributos" changes={diff.attributes} /><ChangeList title="Relaciones" changes={diff.relationships} /></div> : null}
      {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
    </div>
  );
}
