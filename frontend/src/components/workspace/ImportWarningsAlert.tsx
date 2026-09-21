import { AlertTriangle } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

type ImportWarningsAlertProps = {
  warnings: string[];
  onDismiss: () => void;
};

/** Lists what the XMI import skipped or assumed; renders nothing when clean. */
export function ImportWarningsAlert({ warnings, onDismiss }: ImportWarningsAlertProps) {
  if (warnings.length === 0) return null;

  return (
    <Alert variant="caution">
      <AlertTriangle />
      <AlertDescription>
        <p className="font-medium">La importación se completó con {warnings.length} aviso(s):</p>
        <ul className="list-disc pl-5">
          {warnings.map((warning, index) => (
            <li key={index}>{warning}</li>
          ))}
        </ul>
        <Button type="button" size="sm" variant="ghost" className="mt-2" onClick={onDismiss}>
          Cerrar avisos
        </Button>
      </AlertDescription>
    </Alert>
  );
}
