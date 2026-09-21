"use client";

import { AlertCircle } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { ApiError } from "@/lib/api";

type DeleteDiagramDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Shown in the description so the user sees exactly what is being deleted. */
  diagramName: string;
  /** Performs the delete; a rejection keeps the dialog open with an error. */
  onConfirm: () => Promise<void>;
};

function friendlyError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 403) return "No tienes permiso para eliminar este diagrama.";
    if (err.status === 404) return "Este diagrama ya no existe.";
  }
  return "No se pudo eliminar el diagrama. Intenta de nuevo.";
}

/**
 * Presentational confirmation for the destructive "Eliminar diagrama" action,
 * shared by the dashboard cards and the editor header. Owns only the
 * pending/error state of one attempt; the container supplies `onConfirm`
 * (API call + refresh + navigation). The dialog closes itself only when
 * `onConfirm` resolves, so a failed request keeps the message on screen.
 */
export function DeleteDiagramDialog({
  open,
  onOpenChange,
  diagramName,
  onConfirm,
}: DeleteDiagramDialogProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleOpenChange(next: boolean) {
    if (pending) return; // do not dismiss while the request is in flight
    if (!next) setError(null);
    onOpenChange(next);
  }

  async function handleConfirm() {
    setError(null);
    setPending(true);
    try {
      await onConfirm();
      onOpenChange(false);
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={handleOpenChange}
      title="Eliminar diagrama"
      description={`¿Eliminar este diagrama? Esta acción no se puede deshacer.${
        diagramName.trim() ? ` Se eliminará «${diagramName.trim()}».` : ""
      }`}
    >
      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={pending}>
          Cancelar
        </Button>
        <Button type="button" variant="destructive" onClick={handleConfirm} disabled={pending}>
          {pending ? "Eliminando..." : "Eliminar diagrama"}
        </Button>
      </div>
    </Dialog>
  );
}
