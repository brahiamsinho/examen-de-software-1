"use client";

import { AlertCircle } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import type { CommandResult, Relationship, UmlClass, UmlCommandIn } from "@/lib/uml_documents";

type RemoveRelationshipControlProps = {
  classes: UmlClass[];
  relationships: Relationship[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  disabled?: boolean;
};

/**
 * Presentational (design.md DD2/DD6). Option labels identify a relationship
 * by its endpoint class names and kind
 * (`"{sourceName} → {targetName} ({kind})"`) rather than multiplicity —
 * multiplicity does not disambiguate two relationships between the same
 * class pair. Dangling relationships (an endpoint that no longer resolves
 * to a class) are listed, not filtered, falling back to the raw `class_id`
 * — `toElements` drops dangling edges from the canvas, so this control is
 * the only way to delete one. Submission is immediate; no confirmation.
 */
export function RemoveRelationshipControl({
  classes,
  relationships,
  onSubmit,
  disabled = false,
}: RemoveRelationshipControlProps) {
  const [relationshipId, setRelationshipId] = useState("");
  const selectedRelationship = relationships.find((r) => r.id === relationshipId) ?? null;
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function className(classId: string): string {
    return classes.find((c) => c.id === classId)?.name ?? classId;
  }

  function label(r: Relationship): string {
    return `${className(r.source.class_id)} → ${className(r.target.class_id)} (${r.kind})`;
  }

  async function handleSubmit() {
    if (selectedRelationship === null) return;
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({ type: "RemoveRelationship", relationship_id: selectedRelationship.id });
      setRelationshipId("");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="remove-relationship-select">Relación</Label>
        <Select
          id="remove-relationship-select"
          value={selectedRelationship?.id ?? ""}
          onChange={(event) => setRelationshipId(event.target.value)}
          className="font-mono"
        >
          <option value="">Selecciona una relación</option>
          {relationships.map((r) => (
            <option key={r.id} value={r.id}>
              {label(r)}
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
        disabled={submitting || selectedRelationship === null || disabled}
        onClick={handleSubmit}
      >
        Eliminar relación
      </Button>
    </div>
  );
}
