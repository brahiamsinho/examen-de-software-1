"use client";

import { AlertCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import type { CommandResult, UmlClass, UmlCommandIn } from "@/lib/uml_documents";

type RemoveOperationControlProps = {
  classes: UmlClass[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  disabled?: boolean;
};

/**
 * Presentational (design.md DD8), mirror of `RemoveAttributeControl`.
 * Operation options are scoped to the selected class — operation ids are
 * only unique within a class, so `RemoveOperation` needs both `class_id`
 * and `operation_id`. Both selected ids are derived fresh every render, so
 * a stale id left behind by a refetch collapses to `null` in the same
 * render pass. Submission is immediate; there is no confirmation branch
 * (spec: Remove Operation Command).
 */
export function RemoveOperationControl({
  classes,
  onSubmit,
  disabled = false,
}: RemoveOperationControlProps) {
  const [classId, setClassId] = useState("");
  const selectedClass = classes.find((c) => c.id === classId) ?? null;
  const operations = selectedClass?.operations ?? [];
  const [operationId, setOperationId] = useState("");
  const selectedOperation = operations.find((o) => o.id === operationId) ?? null;
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedClass === null || selectedOperation === null) return;
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        type: "RemoveOperation",
        class_id: selectedClass.id,
        operation_id: selectedOperation.id,
      });
      setOperationId("");
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
        <Label htmlFor="remove-operation-class">Clase</Label>
        <Select
          id="remove-operation-class"
          value={selectedClass?.id ?? ""}
          onChange={(event) => {
            setClassId(event.target.value);
            setOperationId("");
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
        <Label htmlFor="remove-operation-operation">Operación</Label>
        <Select
          id="remove-operation-operation"
          value={selectedOperation?.id ?? ""}
          onChange={(event) => setOperationId(event.target.value)}
        >
          <option value="">Selecciona una operación</option>
          {operations.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
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
        disabled={submitting || selectedClass === null || selectedOperation === null || disabled}
      >
        Eliminar operación
      </Button>
    </form>
  );
}
