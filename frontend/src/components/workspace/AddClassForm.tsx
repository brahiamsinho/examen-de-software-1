"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import type { CommandResult, UmlCommandIn } from "@/lib/uml_documents";

type AddClassFormProps = {
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
};

/**
 * Presentational, a `CreateOrgForm` clone (design.md File Changes): receives
 * `onSubmit` — the container's `submitCommand` — instead of calling
 * `state/document.ts` itself. `class_id` is generated client-side with
 * `crypto.randomUUID()` (DD10): the frozen command bus has no
 * id-allocation path.
 */
export function AddClassForm({ onSubmit }: AddClassFormProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({ type: "AddClass", class_id: crypto.randomUUID(), name });
      setName("");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="add-class-name">Nombre de la clase</label>
        <input
          id="add-class-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Button type="submit" disabled={submitting}>
        Agregar clase
      </Button>
    </form>
  );
}
