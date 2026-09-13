"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import type { CommandResult, UmlClass, UmlCommandIn } from "@/lib/uml_documents";

const MULTIPLICITY_OPTIONS = ["1", "0..1", "0..*", "1..*"] as const;
type MultiplicityString = (typeof MULTIPLICITY_OPTIONS)[number];

type AddRelationshipControlProps = {
  pendingSourceId: string | null;
  pendingTargetId: string | null;
  classes: UmlClass[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  onCancel: () => void;
};

/**
 * Presentational: the click-click state (`pendingSourceId`/`pendingTargetId`)
 * lives in the container (DD8); this control only renders the affordance
 * for whatever state it is given and builds the `association`
 * `AddRelationship` command with `crypto.randomUUID()` (DD10) on submit. A
 * successful submission calls `onCancel` to clear both pending ids — the
 * same reset the container's "tap again = cancel" path performs.
 */
export function AddRelationshipControl({
  pendingSourceId,
  pendingTargetId,
  classes,
  onSubmit,
  onCancel,
}: AddRelationshipControlProps) {
  const [sourceMultiplicity, setSourceMultiplicity] = useState<MultiplicityString>("1");
  const [targetMultiplicity, setTargetMultiplicity] = useState<MultiplicityString>("1");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (pendingSourceId === null) {
    return null;
  }

  const sourceClass = classes.find((c) => c.id === pendingSourceId);

  if (pendingTargetId === null) {
    return (
      <div className="flex flex-col gap-2">
        <p>Origen: {sourceClass?.name ?? pendingSourceId}. Selecciona la clase destino.</p>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    );
  }

  const targetClass = classes.find((c) => c.id === pendingTargetId);

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        type: "AddRelationship",
        relationship: {
          id: crypto.randomUUID(),
          kind: "association",
          source: { class_id: pendingSourceId, multiplicity: sourceMultiplicity },
          target: { class_id: pendingTargetId, multiplicity: targetMultiplicity },
        },
      });
      onCancel();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <p>
        {sourceClass?.name ?? pendingSourceId} → {targetClass?.name ?? pendingTargetId}
      </p>

      <div className="flex flex-col gap-1">
        <label htmlFor="relationship-source-multiplicity">Multiplicidad origen</label>
        <select
          id="relationship-source-multiplicity"
          value={sourceMultiplicity}
          onChange={(event) => setSourceMultiplicity(event.target.value as MultiplicityString)}
        >
          {MULTIPLICITY_OPTIONS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="relationship-target-multiplicity">Multiplicidad destino</label>
        <select
          id="relationship-target-multiplicity"
          value={targetMultiplicity}
          onChange={(event) => setTargetMultiplicity(event.target.value as MultiplicityString)}
        >
          {MULTIPLICITY_OPTIONS.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <div className="flex gap-2">
        <Button type="button" disabled={submitting} onClick={handleSubmit}>
          Confirmar relación
        </Button>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}
