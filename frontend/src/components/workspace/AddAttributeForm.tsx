"use client";

import { AlertCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
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
  disabled?: boolean;
};

/**
 * Presentational (design.md File Changes). The type select offers only the
 * eight `PRIMITIVE_TYPES` — no `enumeration_ref` option this cycle (spec
 * "Enumeration types are not offered"). Attribute `id` is generated
 * client-side with `crypto.randomUUID()` (DD10).
 *
 * `classId` is derived fresh every render (DD2 philosophy, same as the
 * Remove* controls), not just initialized once: `useState(classes[0]?.id ??
 * "")` alone froze at `""` forever when this form first mounted with zero
 * classes (a brand-new document) and never re-synced once a class was
 * added — every submit then silently sent `class_id: ""` and the attribute
 * was never actually added (bug reported in production).
 */
export function AddAttributeForm({ classes, onSubmit, disabled = false }: AddAttributeFormProps) {
  const [classId, setClassId] = useState(classes[0]?.id ?? "");
  const resolvedClassId = classes.some((c) => c.id === classId) ? classId : (classes[0]?.id ?? "");
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
        class_id: resolvedClassId,
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
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="add-attribute-class">Clase</Label>
        <Select
          id="add-attribute-class"
          value={resolvedClassId}
          onChange={(event) => setClassId(event.target.value)}
        >
          {classes.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="add-attribute-name">Nombre del atributo</Label>
        <Input
          id="add-attribute-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="add-attribute-type">Tipo</Label>
        <Select
          id="add-attribute-type"
          value={type}
          onChange={(event) => setType(event.target.value as PrimitiveType)}
          className="font-mono"
        >
          {PRIMITIVE_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
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

      <Button type="submit" size="sm" className="self-start" disabled={submitting || disabled}>
        Agregar atributo
      </Button>
    </form>
  );
}
