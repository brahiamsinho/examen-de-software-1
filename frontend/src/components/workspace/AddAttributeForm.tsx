"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import {
  PRIMITIVE_TYPES,
  type CommandResult,
  type PrimitiveType,
  type UmlClass,
  type UmlCommandIn,
} from "@/lib/uml_documents";

type AddAttributeFormProps = {
  classes: UmlClass[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
};

/**
 * Presentational (design.md File Changes). The type select offers only the
 * eight `PRIMITIVE_TYPES` — no `enumeration_ref` option this cycle (spec
 * "Enumeration types are not offered"). Attribute `id` is generated
 * client-side with `crypto.randomUUID()` (DD10).
 */
export function AddAttributeForm({ classes, onSubmit }: AddAttributeFormProps) {
  const [classId, setClassId] = useState(classes[0]?.id ?? "");
  const [name, setName] = useState("");
  const [type, setType] = useState<PrimitiveType>(PRIMITIVE_TYPES[0]!);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        type: "AddAttribute",
        class_id: classId,
        attribute: { id: crypto.randomUUID(), name, type },
      });
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
        <label htmlFor="add-attribute-class">Clase</label>
        <select
          id="add-attribute-class"
          value={classId}
          onChange={(event) => setClassId(event.target.value)}
        >
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="add-attribute-name">Nombre del atributo</label>
        <input
          id="add-attribute-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="add-attribute-type">Tipo</label>
        <select
          id="add-attribute-type"
          value={type}
          onChange={(event) => setType(event.target.value as PrimitiveType)}
        >
          {PRIMITIVE_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Button type="submit" disabled={submitting}>
        Agregar atributo
      </Button>
    </form>
  );
}
