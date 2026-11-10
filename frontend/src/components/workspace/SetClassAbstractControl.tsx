"use client";

import { AlertCircle } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import type { CommandResult, UmlClass, UmlCommandIn } from "@/lib/uml_documents";

type SetClassAbstractControlProps = {
  classes: UmlClass[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  disabled?: boolean;
};

/**
 * Presentational. Marks a class abstract (UML 2.5 `isAbstract`) or makes it
 * concrete again. The selected id is looked up fresh on every render, so a
 * class that disappears in a refetch just clears the selection. The button
 * always offers the opposite of the class's current state.
 */
export function SetClassAbstractControl({ classes, onSubmit, disabled = false }: SetClassAbstractControlProps) {
  const [classId, setClassId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const selected = classes.find((item) => item.id === classId) ?? null;
  const isAbstract = selected?.is_abstract === true;

  async function handleClick() {
    if (selected === null) return;
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({ type: "SetClassAbstract", class_id: selected.id, is_abstract: !isAbstract });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="abstract-class-select">Clase</Label>
        <Select
          id="abstract-class-select"
          value={selected?.id ?? ""}
          onChange={(event) => setClassId(event.target.value)}
        >
          <option value="">Selecciona una clase</option>
          {classes.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </Select>
      </div>

      {selected ? (
        <p className="text-sm text-muted-foreground">
          {selected.name} es {isAbstract ? "abstracta" : "concreta"}.
        </p>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Button
        type="button"
        size="sm"
        variant="outline"
        className="self-start"
        disabled={selected === null || submitting || disabled}
        onClick={handleClick}
      >
        {isAbstract ? "Quitar abstracta" : "Marcar como abstracta"}
      </Button>
    </div>
  );
}
