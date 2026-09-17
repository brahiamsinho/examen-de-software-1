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
  type Visibility,
} from "@/lib/uml_documents";

type AddOperationFormProps = {
  classes: UmlClass[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  disabled?: boolean;
};

const VISIBILITIES: readonly Visibility[] = ["public", "private", "protected", "package"];

/**
 * Presentational (design.md DD8), mirror of `AddAttributeForm`. The
 * return-type select's first option is an explicit "Sin tipo de retorno"
 * (submits `return_type: null`), followed by the eight `PRIMITIVE_TYPES` —
 * no `enumeration_ref` option this cycle. No parameter input — v1 always
 * submits `parameters: ()`. Operation `id` is generated client-side with
 * `crypto.randomUUID()`.
 *
 * `resolvedClassId` re-derives fresh every render (same production-bug fix
 * as `AddAttributeForm`): a form mounted with zero classes must not freeze
 * `class_id` at `""` forever once a class is later added.
 */
export function AddOperationForm({ classes, onSubmit, disabled = false }: AddOperationFormProps) {
  const [classId, setClassId] = useState(classes[0]?.id ?? "");
  const resolvedClassId = classes.some((c) => c.id === classId) ? classId : (classes[0]?.id ?? "");
  const [name, setName] = useState("");
  const [returnType, setReturnType] = useState<PrimitiveType | "">("");
  const [visibility, setVisibility] = useState<Visibility>("public");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        type: "AddOperation",
        class_id: resolvedClassId,
        operation: {
          id: crypto.randomUUID(),
          name,
          return_type: returnType === "" ? null : returnType,
          visibility,
        }, // no `parameters` field on the wire — v1 always sends none (server-side ())
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
        <Label htmlFor="add-operation-class">Clase</Label>
        <Select
          id="add-operation-class"
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
        <Label htmlFor="add-operation-name">Nombre de la operación</Label>
        <Input
          id="add-operation-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="add-operation-return-type">Tipo de retorno</Label>
        <Select
          id="add-operation-return-type"
          value={returnType}
          onChange={(event) => setReturnType(event.target.value as PrimitiveType | "")}
          className="font-mono"
        >
          <option value="">Sin tipo de retorno</option>
          {PRIMITIVE_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </Select>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="add-operation-visibility">Visibilidad</Label>
        <Select
          id="add-operation-visibility"
          value={visibility}
          onChange={(event) => setVisibility(event.target.value as Visibility)}
        >
          {VISIBILITIES.map((v) => (
            <option key={v} value={v}>
              {v}
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
        Agregar operación
      </Button>
    </form>
  );
}
