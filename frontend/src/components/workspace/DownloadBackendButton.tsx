"use client";

import { AlertCircle, Download } from "lucide-react";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";

type DownloadBackendButtonProps = {
  onDownload: () => Promise<void>;
  disabled?: boolean;
};

/**
 * Presentational: owns only the pending/error UI state of one download.
 * The container supplies `onDownload` (which talks to the API), so this
 * component never imports the transport. A 422 shows the server's own
 * `detail` (e.g. "the document has no classes"), anything else a generic message.
 */
export function DownloadBackendButton({ onDownload, disabled = false }: DownloadBackendButtonProps) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    if (pending) return;
    setError(null);
    setPending(true);
    try {
      await onDownload();
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
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="self-start"
        onClick={handleClick}
        disabled={pending || disabled}
      >
        <Download />
        {pending ? "Generando..." : "Descargar backend"}
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
