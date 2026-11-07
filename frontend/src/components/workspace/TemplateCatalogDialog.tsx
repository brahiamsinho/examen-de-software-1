"use client";

import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { listTemplates, type UmlDocument, type UmlTemplateSummary } from "@/lib/uml_documents";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  orgSlug: string;
  onInstantiate: (templateId: string, input: { name: string }) => Promise<UmlDocument>;
};

export function TemplateCatalogDialog({ open, onOpenChange, orgSlug, onInstantiate }: Props) {
  const [templates, setTemplates] = useState<UmlTemplateSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    void listTemplates(orgSlug)
      .then((items) => {
        if (!cancelled) {
          setTemplates(items);
          setSelectedId(items[0]?.id ?? "");
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : "No se pudieron cargar las plantillas.");
      });
    return () => { cancelled = true; };
  }, [open, orgSlug]);

  async function instantiate() {
    if (!selectedId || !name.trim()) return;
    setBusy(true);
    try {
      await onInstantiate(selectedId, { name: name.trim() });
      onOpenChange(false);
      setName("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo crear el diagrama desde la plantilla.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Plantillas" description="Crea un diagrama nuevo a partir de una plantilla de tu organización.">
      <div className="flex flex-col gap-4">
        {templates.length === 0 ? <p className="text-sm text-muted-foreground">Todavía no hay plantillas disponibles.</p> : (
          <select aria-label="Plantilla" className="h-9 rounded-md border bg-background px-3 text-sm" value={selectedId} onChange={(event) => setSelectedId(event.target.value)}>
            {templates.map((template) => <option key={template.id} value={template.id}>{template.name}</option>)}
          </select>
        )}
        <Input aria-label="Nombre del nuevo diagrama" value={name} onChange={(event) => setName(event.target.value)} placeholder="Nombre del nuevo diagrama" />
        {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
        <Button type="button" onClick={instantiate} disabled={busy || !selectedId || !name.trim()}>Usar plantilla</Button>
      </div>
    </Dialog>
  );
}
