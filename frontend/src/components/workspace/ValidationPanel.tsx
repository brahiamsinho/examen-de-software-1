import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
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

  if (lastValidation.violations.length === 0) {
    return (
      <Alert variant="success">
        <CheckCircle2 />
        <AlertDescription>El modelo es válido.</AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {lastValidation.violations.map((violation, index) => (
        <Alert
          key={`${violation.code}-${index}`}
          variant={violation.severity === "error" ? "destructive" : "caution"}
        >
          {violation.severity === "error" ? <XCircle /> : <AlertTriangle />}
          <AlertDescription>
            <p className="text-xs opacity-70">{violation.severity}</p>
            <p className="font-mono text-xs opacity-80">{violation.code}</p>
            <p>{violation.message}</p>
            <p className="font-mono text-xs opacity-70">{violation.path}</p>
          </AlertDescription>
        </Alert>
      ))}
    </div>
  );
}
