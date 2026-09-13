import type { CommandResult } from "@/lib/uml_documents";

type ValidationPanelProps = {
  lastValidation: CommandResult["validation"] | null;
};

/**
 * Renders non-blockingly from `lastValidation` (DD13): `null` until the
 * first command — `GET /documents/{id}` returns no `validation` field at
 * all — and after it renders every diagnostic regardless of `is_valid`.
 * Purely display: it exposes no prop that could disable another form.
 */
export function ValidationPanel({ lastValidation }: ValidationPanelProps) {
  if (lastValidation === null) {
    return null;
  }

  return (
    <ul className="flex flex-col gap-2">
      {lastValidation.violations.map((violation, index) => (
        <li key={`${violation.code}-${index}`} className="flex flex-col gap-0.5 text-sm">
          <span>{violation.severity}</span>
          <span>{violation.code}</span>
          <span>{violation.message}</span>
          <span>{violation.path}</span>
        </li>
      ))}
    </ul>
  );
}
