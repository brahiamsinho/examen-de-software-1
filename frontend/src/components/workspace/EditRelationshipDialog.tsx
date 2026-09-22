"use client";

import { AlertCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import {
  formatMultiplicity,
  parseMultiplicityInput,
  type CommandResult,
  type Relationship,
  type UmlClass,
  type UmlCommandIn,
} from "@/lib/uml_documents";

const INVALID_MULTIPLICITY = "Multiplicidad inválida. Ejemplos: 1, 0..1, 0..*, 1..*";

type EditRelationshipDialogProps = {
  /** The relationship being edited; `null` keeps the dialog closed. */
  relationship: Relationship | null;
  classes: UmlClass[];
  /** Sends the command; a rejection keeps the dialog open with an error. */
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  onClose: () => void;
};

/**
 * Presentational dialog opened by double-clicking an edge on the canvas.
 * The container owns which relationship is open and supplies `onSubmit`
 * (`submitCommand`); this component only validates the two multiplicity
 * inputs (same notation as `formatMultiplicity`, plus a lone "*") and builds
 * an `UpdateRelationship` command. A generalization has no multiplicities in
 * UML 2.5, so it shows only the name.
 */
export function EditRelationshipDialog({
  relationship,
  classes,
  onSubmit,
  onClose,
}: EditRelationshipDialogProps) {
  return (
    <Dialog
      open={relationship !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title="Editar relación"
    >
      {/* Mounted only while open, so each open starts from the current values. */}
      {relationship ? (
        <EditRelationshipForm
          key={relationship.id}
          relationship={relationship}
          classes={classes}
          onSubmit={onSubmit}
          onClose={onClose}
        />
      ) : null}
    </Dialog>
  );
}

function EditRelationshipForm({
  relationship,
  classes,
  onSubmit,
  onClose,
}: Omit<EditRelationshipDialogProps, "relationship"> & { relationship: Relationship }) {
  const hasMultiplicity = relationship.kind !== "generalization";
  const [name, setName] = useState(relationship.name ?? "");
  const [source, setSource] = useState(formatMultiplicity(relationship.source.multiplicity));
  const [target, setTarget] = useState(formatMultiplicity(relationship.target.multiplicity));
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const className = (id: string) => classes.find((c) => c.id === id)?.name ?? id;
  const sourceName = className(relationship.source.class_id);
  const targetName = className(relationship.target.class_id);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const command: UmlCommandIn = {
      type: "UpdateRelationship",
      relationship_id: relationship.id,
      name: name.trim() === "" ? null : name.trim(),
    };
    if (hasMultiplicity) {
      const parsedSource = parseMultiplicityInput(source);
      const parsedTarget = parseMultiplicityInput(target);
      if (parsedSource === null || parsedTarget === null) {
        setError(INVALID_MULTIPLICITY);
        return;
      }
      command.source_multiplicity = parsedSource;
      command.target_multiplicity = parsedTarget;
    }

    setSubmitting(true);
    try {
      await onSubmit(command);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <p className="font-mono text-sm text-muted-foreground">
        {sourceName} → {targetName}
      </p>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="edit-relationship-name">Nombre</Label>
        <Input
          id="edit-relationship-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Sin nombre"
        />
      </div>

      {hasMultiplicity ? (
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="edit-relationship-source">Multiplicidad en {sourceName}</Label>
            <Input
              id="edit-relationship-source"
              value={source}
              onChange={(event) => setSource(event.target.value)}
              className="font-mono"
              autoComplete="off"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="edit-relationship-target">Multiplicidad en {targetName}</Label>
            <Input
              id="edit-relationship-target"
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              className="font-mono"
              autoComplete="off"
            />
          </div>
        </div>
      ) : null}

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
          Cancelar
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Guardando..." : "Guardar"}
        </Button>
      </div>
    </form>
  );
}
