"use client";

import { AlertCircle } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import type { CommandResult, RelationshipKind, UmlClass, UmlCommandIn } from "@/lib/uml_documents";

const MULTIPLICITY_OPTIONS = ["1", "0..1", "0..*", "1..*"] as const;
type MultiplicityString = (typeof MULTIPLICITY_OPTIONS)[number];

const RELATIONSHIP_KIND_OPTIONS: readonly { value: RelationshipKind; label: string }[] = [
  { value: "association", label: "Asociación" },
  { value: "aggregation", label: "Agregación" },
  { value: "composition", label: "Composición" },
  { value: "generalization", label: "Generalización" },
];

type AddRelationshipControlProps = {
  pendingSourceId: string | null;
  pendingTargetId: string | null;
  classes: UmlClass[];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  onCancel: () => void;
  onSelectSelf: () => void;
  disabled?: boolean;
};

/**
 * Presentational: the click-click state (`pendingSourceId`/`pendingTargetId`)
 * lives in the container (DD8); this control only renders the affordance
 * for whatever state it is given and builds an `AddRelationship` command
 * for the locally-selected `RelationshipKind` (default `association`) with
 * `crypto.randomUUID()` (DD10) on submit. Generalization hides both
 * multiplicity selects and always submits `"1"`/`"1"` regardless of any
 * prior selection (DD5); switching away from generalization restores it,
 * since kind is never reset. A successful submission calls `onCancel` to
 * clear both pending ids — the same reset the container's "tap again =
 * cancel" path performs.
 *
 * `onSelectSelf` covers recursive/reflexive relationships (a class related
 * to itself — e.g. a tree node's `parent`): tapping the same class twice on
 * the canvas is the container's cancel gesture, so self-relationships need
 * an explicit affordance here instead of overloading that tap.
 */
export function AddRelationshipControl({
  pendingSourceId,
  pendingTargetId,
  classes,
  onSubmit,
  onCancel,
  onSelectSelf,
  disabled = false,
}: AddRelationshipControlProps) {
  const [kind, setKind] = useState<RelationshipKind>("association");
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
      <div className="flex flex-col gap-3">
        <p className="text-sm text-muted-foreground">
          Origen: <span className="font-mono text-foreground">{sourceClass?.name ?? pendingSourceId}</span>.
          Selecciona la clase destino en el diagrama.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onSelectSelf}>
            Relación consigo misma
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={onCancel}>
            Cancelar
          </Button>
        </div>
      </div>
    );
  }

  const targetClass = classes.find((c) => c.id === pendingTargetId);
  // `const` bindings narrow inside a nested closure; the `string | null`
  // params above do not (TS cannot assume a param wasn't reassigned by the
  // time a closure defined later in this render runs).
  const sourceId: string = pendingSourceId;
  const targetId: string = pendingTargetId;

  async function handleSubmit() {
    setError(null);
    setSubmitting(true);
    try {
      // DD5: the payload is derived from what is visible, not the hidden
      // multiplicity state — generalization has no multiplicity in UML 2.5,
      // so it always sends the literal "1"/"1" regardless of any prior
      // selection. Kind is never reset on switch, so switching back to a
      // multiplicity-bearing kind restores the earlier choice.
      const isGeneralization = kind === "generalization";
      await onSubmit({
        type: "AddRelationship",
        relationship: {
          id: crypto.randomUUID(),
          kind,
          source: { class_id: sourceId, multiplicity: isGeneralization ? "1" : sourceMultiplicity },
          target: { class_id: targetId, multiplicity: isGeneralization ? "1" : targetMultiplicity },
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
    <div className="flex flex-col gap-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
      <p className="font-mono text-sm font-medium text-foreground">
        {sourceClass?.name ?? pendingSourceId} → {targetClass?.name ?? pendingTargetId}
      </p>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="relationship-kind">Tipo de relación</Label>
        <Select
          id="relationship-kind"
          value={kind}
          onChange={(event) => setKind(event.target.value as RelationshipKind)}
        >
          {RELATIONSHIP_KIND_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>

      {kind === "generalization" ? null : (
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="relationship-source-multiplicity">Multiplicidad origen</Label>
            <Select
              id="relationship-source-multiplicity"
              value={sourceMultiplicity}
              onChange={(event) => setSourceMultiplicity(event.target.value as MultiplicityString)}
              className="font-mono"
            >
              {MULTIPLICITY_OPTIONS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </Select>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="relationship-target-multiplicity">Multiplicidad destino</Label>
            <Select
              id="relationship-target-multiplicity"
              value={targetMultiplicity}
              onChange={(event) => setTargetMultiplicity(event.target.value as MultiplicityString)}
              className="font-mono"
            >
              {MULTIPLICITY_OPTIONS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </Select>
          </div>
        </div>
      )}

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <div className="flex gap-2">
        <Button type="button" size="sm" disabled={submitting || disabled} onClick={handleSubmit}>
          Confirmar relación
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onCancel}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}
