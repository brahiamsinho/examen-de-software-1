"use client";

import { AlertCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import type { CommandResult, UmlClass, UmlCommandIn } from "@/lib/uml_documents";

type RemoveAttributeControlProps = {
  classes: UmlClass[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  disabled?: boolean;
};

/**
 * Presentational (design.md DD2/DD3). Attribute options are scoped to the
 * selected class — attribute ids are only unique within a class (DD1), so
 * `RemoveAttribute` needs both `class_id` and `attribute_id`. Both selected
 * ids are derived fresh every render, so a stale id left behind by a
 * refetch collapses to `null` in the same render pass. Submission is
 * immediate; there is no confirmation branch (spec: Remove Attribute
 * Command).
 */
export function RemoveAttributeControl({
  classes,
  onSubmit,
  disabled = false,
}: RemoveAttributeControlProps) {
  const [classId, setClassId] = useState("");
  const selectedClass = classes.find((c) => c.id === classId) ?? null;
  const attributes = selectedClass?.attributes ?? [];
  const [attributeId, setAttributeId] = useState("");
  const selectedAttribute = attributes.find((a) => a.id === attributeId) ?? null;
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedClass === null || selectedAttribute === null) return;
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        type: "RemoveAttribute",
        class_id: selectedClass.id,
        attribute_id: selectedAttribute.id,
      });
      setAttributeId("");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="remove-attribute-class">Clase</Label>
        <Select
          id="remove-attribute-class"
          value={selectedClass?.id ?? ""}
          onChange={(event) => {
            setClassId(event.target.value);
            setAttributeId("");
          }}
        >
          <option value="">Selecciona una clase</option>
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="remove-attribute-attribute">Atributo</Label>
        <Select
          id="remove-attribute-attribute"
          value={selectedAttribute?.id ?? ""}
          onChange={(event) => setAttributeId(event.target.value)}
        >
          <option value="">Selecciona un atributo</option>
          {attributes.map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
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
        type="submit"
        variant="caution"
        size="sm"
        className="self-start"
        disabled={submitting || selectedClass === null || selectedAttribute === null || disabled}
      >
        Eliminar atributo
      </Button>
    </form>
  );
}
