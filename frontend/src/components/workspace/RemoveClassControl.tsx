"use client";

import { AlertCircle, AlertTriangle } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import type { CommandResult, Relationship, UmlClass, UmlCommandIn } from "@/lib/uml_documents";

type RemoveClassControlProps = {
  classes: UmlClass[];
  relationships: Relationship[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  disabled?: boolean;
};

/**
 * Presentational (design.md DD2/DD3/DD4/DD5). The selected id is derived
 * fresh every render (`classes.find(...)`), so a stale id left behind by a
 * refetch collapses to `null` in the same render pass — no effect, no
 * remount. Destruction is gated behind a second render branch (`confirming`)
 * that states the exact cascade count, derived from `relationships` and
 * never stored, mirroring `remove_class`'s own source-or-target filter.
 */
export function RemoveClassControl({
  classes,
  relationships,
  onSubmit,
  disabled = false,
}: RemoveClassControlProps) {
  const [classId, setClassId] = useState("");
  const selectedClass = classes.find((c) => c.id === classId) ?? null;
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const cascadeCount = selectedClass
    ? relationships.filter(
        (r) => r.source.class_id === selectedClass.id || r.target.class_id === selectedClass.id,
      ).length
    : 0;

  async function handleConfirm() {
    if (selectedClass === null) return;
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({ type: "RemoveClass", class_id: selectedClass.id });
      setClassId("");
      setConfirming(false);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (confirming && selectedClass !== null) {
    return (
      <div className="flex flex-col gap-3">
        <Alert variant="caution">
          <AlertTriangle />
          <AlertDescription>
            <p>
              Se eliminará la clase <span className="font-mono font-medium">«{selectedClass.name}»</span>.
            </p>
            {cascadeCount > 0 ? (
              <p>Se eliminarán también {cascadeCount} relación(es) que la referencian.</p>
            ) : null}
          </AlertDescription>
        </Alert>

        {error ? (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}

        <div className="flex gap-2">
          <Button
            type="button"
            variant="caution"
            size="sm"
            disabled={submitting || disabled}
            onClick={handleConfirm}
          >
            Confirmar eliminación
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={() => setConfirming(false)}>
            Cancelar
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="remove-class-select">Clase</Label>
        <Select
          id="remove-class-select"
          value={selectedClass?.id ?? ""}
          onChange={(event) => setClassId(event.target.value)}
        >
          <option value="">Selecciona una clase</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Button
        type="button"
        variant="caution"
        size="sm"
        className="self-start"
        disabled={selectedClass === null || disabled}
        onClick={() => setConfirming(true)}
      >
        Eliminar
      </Button>
    </div>
  );
}
