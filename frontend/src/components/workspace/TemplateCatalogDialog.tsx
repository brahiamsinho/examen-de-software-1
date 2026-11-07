"use client";

import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { TemplatePreviewThumbnail } from "@/components/workspace/TemplatePreviewThumbnail";
import { ApiError } from "@/lib/api";
import { listTemplates, type UmlDocument, type UmlTemplateSummary } from "@/lib/uml_documents";
import { cn } from "@/lib/utils";

function plural(count: number, singular: string, pluralForm: string): string {
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

function summarize(template: UmlTemplateSummary): string {
  const { classes, relationships } = template.preview;
  return `${plural(classes.length, "clase", "clases")} · ${plural(relationships.length, "relación", "relaciones")}`;
}

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
    <Dialog open={open} onOpenChange={onOpenChange} className="max-w-2xl" title="Plantillas" description="Crea un diagrama nuevo a partir de una plantilla de tu organización.">
      <div className="flex flex-col gap-4">
        {templates.length === 0 ? <p className="text-sm text-muted-foreground">Todavía no hay plantillas disponibles.</p> : (
          <div role="radiogroup" aria-label="Plantilla" className="grid max-h-[28rem] grid-cols-1 gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
            {templates.map((template) => (
              <label
                key={template.id}
                className={cn(
                  "flex cursor-pointer flex-col gap-2 rounded-lg border p-2 text-sm transition-colors has-focus-visible:ring-3 has-focus-visible:ring-ring/50",
                  template.id === selectedId ? "border-ring bg-accent/40" : "border-border hover:border-ring/60",
                )}
              >
                <input
                  type="radio"
                  name="template"
                  className="sr-only"
                  checked={template.id === selectedId}
                  onChange={() => setSelectedId(template.id)}
                />
                <TemplatePreviewThumbnail preview={template.preview} />
                <span className="font-medium">{template.name}</span>
                <span className="text-xs text-muted-foreground">{summarize(template)}</span>
              </label>
            ))}
          </div>
        )}
        <Input aria-label="Nombre del nuevo diagrama" value={name} onChange={(event) => setName(event.target.value)} placeholder="Nombre del nuevo diagrama" />
        {error ? <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert> : null}
        <Button type="button" onClick={instantiate} disabled={busy || !selectedId || !name.trim()}>Usar plantilla</Button>
      </div>
    </Dialog>
  );
}
