"use client";

import { AlertCircle, ImageUp, Loader2 } from "lucide-react";
import { useRef, useState, type ChangeEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import type { VoiceCommandResult } from "@/lib/voice_command";

type ImageImportButtonProps = {
  /** Container-supplied: uploads the image and returns the applied-commands
   * report, mirroring `VoiceCommandButton`'s `onSubmit`-returns-result
   * convention. */
  onSubmit: (file: File) => Promise<VoiceCommandResult>;
  disabled?: boolean;
};

type Status = "idle" | "uploading" | "done" | "error";

const ACCEPTED_TYPES = "image/png,image/jpeg,image/webp,image/gif";

/**
 * Image-driven diagram import: opens a native file picker for a UML diagram
 * image (screenshot, photo of a whiteboard sketch, or an export from
 * another tool), sends it to the backend's OpenAI-vision-backed
 * `/image-command` endpoint via `onSubmit`, and renders the same kind of
 * per-command ok/failed report `VoiceCommandButton` shows. Mirrors
 * `ImportXmiControl`'s hidden-input trigger pattern (a visually hidden
 * `<input type="file">`, opened programmatically via a ref).
 */
export function ImageImportButton({ onSubmit, disabled = false }: ImageImportButtonProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<VoiceCommandResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = ""; // allow picking the same file again after a failure
    if (!file || status === "uploading") return;
    setResult(null);
    setError(null);
    setStatus("uploading");
    try {
      const applied = await onSubmit(file);
      setResult(applied);
      setStatus("done");
    } catch (err) {
      setResult(null);
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
      setStatus("error");
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        aria-label="Imagen del diagrama UML"
        className="sr-only"
        tabIndex={-1}
        onChange={handleChange}
      />
      <Button
        type="button"
        variant="outline"
        size="lg"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || status === "uploading"}
        aria-live="polite"
      >
        {status === "uploading" ? <Loader2 className="animate-spin" /> : <ImageUp />}
        {status === "uploading" ? "Analizando imagen..." : "Importar imagen"}
      </Button>

      {result !== null ? (
        <ul className="flex flex-col gap-1 text-xs">
          {result.applied.length === 0 ? (
            <li className="text-muted-foreground">No se aplicó ningún cambio.</li>
          ) : (
            result.applied.map((item, index) => (
              <li key={index} className={item.ok ? "text-foreground" : "text-destructive"}>
                {item.ok ? "✓" : "✗"} {item.message}
              </li>
            ))
          )}
        </ul>
      ) : null}

      {error !== null ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
