import { type FormEvent, useMemo, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { ApiError } from "@/lib/api";
import type { CommandResult, UmlClass, UmlCommandIn, UmlModel } from "@/lib/uml_documents";

type TriState = "unset" | "true" | "false";
type TargetKind = "class" | "attribute";
type Target = { kind: TargetKind; elementId: string; label: string };
type TriStateValues = Record<string, TriState>;

type GenerationProfilePanelProps = {
  classes: UmlClass[];
  generationMetadata: UmlModel["generation_metadata"];
  onSubmit: (command: UmlCommandIn) => Promise<CommandResult>;
  disabled?: boolean;
};

const CRUD_OPERATIONS = ["create", "read", "update", "delete"] as const;
const CLASS_FIELDS = ["auditable", "readOnly", "crud"] as const;
const ATTRIBUTE_FIELDS = ["searchable", "sortable", "readOnly"] as const;
const FIELD_LABELS: Record<(typeof CLASS_FIELDS | typeof ATTRIBUTE_FIELDS)[number], string> = {
  auditable: "Auditable",
  readOnly: "Solo lectura",
  crud: "CRUD",
  searchable: "Buscable",
  sortable: "Ordenable",
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function deriveTargets(classes: UmlClass[]): Target[] {
  return classes.flatMap((umlClass) => [
    { kind: "class", elementId: umlClass.id, label: `Clase: ${umlClass.name}` } satisfies Target,
    ...umlClass.attributes.map(
      (attribute): Target => ({
        kind: "attribute",
        elementId: attribute.id,
        label: `Atributo: ${umlClass.name}.${attribute.name}`,
      }),
    ),
  ]);
}

function booleanTriState(value: unknown): TriState {
  if (value === true) return "true";
  if (value === false) return "false";
  return "unset";
}

function crudTriState(value: unknown): TriState {
  if (!Array.isArray(value)) return "unset";
  if (value.length === 0) return "false";
  return CRUD_OPERATIONS.every((operation) => value.includes(operation)) ? "true" : "unset";
}

function emptyValues(kind: TargetKind): TriStateValues {
  const fields = kind === "class" ? CLASS_FIELDS : ATTRIBUTE_FIELDS;
  return Object.fromEntries(fields.map((field) => [field, "unset"])) as TriStateValues;
}

function readProfileValues(
  generationMetadata: UmlModel["generation_metadata"],
  target: Target,
): TriStateValues {
  const entry = generationMetadata[target.elementId];
  if (!isRecord(entry) || !isRecord(entry.profile)) {
    return emptyValues(target.kind);
  }

  if (target.kind === "class") {
    return {
      auditable: booleanTriState(entry.profile.auditable),
      readOnly: booleanTriState(entry.profile.readOnly),
      crud: crudTriState(entry.profile.crud),
    };
  }

  return {
    searchable: booleanTriState(entry.profile.searchable),
    sortable: booleanTriState(entry.profile.sortable),
    readOnly: booleanTriState(entry.profile.readOnly),
  };
}

function buildProfile(target: Target, values: TriStateValues): Record<string, unknown> | null {
  const profile: Record<string, unknown> = {};
  const addBoolean = (field: string) => {
    if (values[field] === "true") profile[field] = true;
    if (values[field] === "false") profile[field] = false;
  };

  if (target.kind === "class") {
    addBoolean("auditable");
    addBoolean("readOnly");
    if (values.crud === "true") profile.crud = [...CRUD_OPERATIONS];
    if (values.crud === "false") profile.crud = [];
  } else {
    addBoolean("searchable");
    addBoolean("sortable");
    addBoolean("readOnly");
  }

  return Object.keys(profile).length > 0 ? profile : null;
}

function valuesFromSubmitted(target: Target, profile: Record<string, unknown> | null): TriStateValues {
  if (profile === null) return emptyValues(target.kind);
  return readProfileValues({ [target.elementId]: { profile } }, target);
}

function TriStateSelect({
  id,
  label,
  value,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  value: TriState;
  disabled?: boolean;
  onChange: (value: TriState) => void;
}) {
  return (
    <div className="flex flex-col gap-1">
      <Label htmlFor={id}>{label}</Label>
      <Select
        id={id}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value as TriState)}
      >
        <option value="unset">Sin declarar</option>
        <option value="true">Sí</option>
        <option value="false">No</option>
      </Select>
    </div>
  );
}

export function GenerationProfilePanel({
  classes,
  generationMetadata,
  onSubmit,
  disabled = false,
}: GenerationProfilePanelProps) {
  const targets = useMemo(() => deriveTargets(classes), [classes]);
  const [selectedElementId, setSelectedElementId] = useState("");
  const selectedTarget = targets.find((target) => target.elementId === selectedElementId) ?? null;
  const [editedValues, setEditedValues] = useState<{ elementId: string; values: TriStateValues } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const baseValues = useMemo(
    () => (selectedTarget === null ? {} : readProfileValues(generationMetadata, selectedTarget)),
    [generationMetadata, selectedTarget],
  );
  const values =
    editedValues !== null && editedValues.elementId === selectedTarget?.elementId
      ? editedValues.values
      : baseValues;

  const fields = selectedTarget?.kind === "class" ? CLASS_FIELDS : ATTRIBUTE_FIELDS;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (selectedTarget === null) return;

    const profile = buildProfile(selectedTarget, values);
    try {
      await onSubmit({ type: "SetGenerationProfile", element_id: selectedTarget.elementId, profile });
      setError(null);
      setEditedValues({ elementId: selectedTarget.elementId, values: valuesFromSubmitted(selectedTarget, profile) });
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
    }
  }

  const formDisabled = disabled || selectedTarget === null;

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
      <div className="flex flex-col gap-1">
        <Label htmlFor="generation-profile-target">Elemento</Label>
        <Select
          id="generation-profile-target"
          value={selectedTarget?.elementId ?? ""}
          disabled={disabled || targets.length === 0}
          onChange={(event) => {
            setSelectedElementId(event.target.value);
            setEditedValues(null);
            setError(null);
          }}
        >
          <option value="">Selecciona un elemento</option>
          {targets.map((target) => (
            <option key={target.elementId} value={target.elementId}>
              {target.label}
            </option>
          ))}
        </Select>
      </div>

      {targets.length === 0 ? (
        <p className="text-sm text-muted-foreground">No hay clases ni atributos disponibles para perfilar.</p>
      ) : null}

      {selectedTarget === null && targets.length > 0 ? (
        <p className="text-sm text-muted-foreground">Selecciona una clase o atributo para editar su perfil.</p>
      ) : null}

      {selectedTarget !== null ? (
        <div className="flex flex-col gap-3">
          {fields.map((field) => (
            <TriStateSelect
              key={field}
              id={`generation-profile-${field}`}
              label={FIELD_LABELS[field]}
              value={values[field] ?? "unset"}
              disabled={disabled}
              onChange={(value) =>
                setEditedValues({
                  elementId: selectedTarget.elementId,
                  values: { ...values, [field]: value },
                })
              }
            />
          ))}
        </div>
      ) : null}

      {error !== null ? (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Button type="submit" disabled={formDisabled}>
        Guardar perfil
      </Button>
    </form>
  );
}
