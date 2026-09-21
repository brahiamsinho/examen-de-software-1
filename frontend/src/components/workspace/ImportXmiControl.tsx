"use client";

import { AlertCircle, Upload } from "lucide-react";
import { useRef, useState, type ChangeEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

type ImportXmiControlProps = {
  onImport: (file: File) => Promise<void>;
  disabled?: boolean;
};

/**
 * Presentational: a button that opens a hidden file input and owns only the
 * pending/error state of one import. The container supplies `onImport`
 * (upload + navigation), so no transport or router is imported here. A 422
 * shows the server's own `detail` (e.g. "no es un XML válido").
 */
export function ImportXmiControl({ onImport, disabled = false }: ImportXmiControlProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow picking the same file again after a failure
    if (!file || pending) return;
    setError(null);
    setPending(true);
    try {
      await onImport(file);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        type="file"
        accept=".xml,.xmi,application/xml,text/xml"
        aria-label="Archivo XML"
        className="sr-only"
        tabIndex={-1}
        onChange={handleChange}
      />
      <Button
        type="button"
        variant="outline"
        className="self-start"
        onClick={() => inputRef.current?.click()}
        disabled={pending || disabled}
      >
        <Upload />
        {pending ? "Importando..." : "Importar XML"}
      </Button>

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
