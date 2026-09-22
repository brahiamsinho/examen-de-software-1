"use client";

import { AlertCircle, Loader2, Mic, MicOff } from "lucide-react";
import { useRef, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import type { VoiceCommandResult } from "@/lib/voice_command";

/**
 * Minimal shape of the Web Speech API's `SpeechRecognition` this component
 * actually uses. The DOM lib ships no types for it (Firefox/Safari don't
 * implement it at all), so it is hand-declared here rather than reaching
 * for `any`.
 */
type SpeechRecognitionResultLike = { transcript: string };
type SpeechRecognitionResultListLike = { [index: number]: { [index: number]: SpeechRecognitionResultLike } };
type SpeechRecognitionEventLike = { results: SpeechRecognitionResultListLike };
type SpeechRecognitionErrorEventLike = { error: string };

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

/**
 * Rioplatense Spanish ("es-AR"): this project's own example voice
 * utterances use voseo ("creá una clase Persona con un atributo edad"),
 * so the recognizer is pinned to the dialect that transcribes that
 * conjugation correctly rather than the more generic "es-ES".
 */
const LOCALE = "es-AR";

function getSpeechRecognitionConstructor(): SpeechRecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

type VoiceCommandButtonProps = {
  /** Container-supplied: POSTs the transcript and returns the applied-commands
   * report, mirroring `AddClassForm`'s `onSubmit`-returns-result convention. */
  onSubmit: (transcript: string) => Promise<VoiceCommandResult>;
  disabled?: boolean;
};

type Status = "idle" | "listening" | "processing" | "done" | "error";

/**
 * Voice-driven diagram editing: captures one utterance with the browser's
 * native `SpeechRecognition`, sends the transcript to the backend's
 * Gemini-backed `/voice-command` endpoint via `onSubmit`, and renders what
 * was heard plus a per-command ok/failed report. Idle / listening /
 * processing / result are all distinct, visible states — never a bare
 * console.log. Renders a disabled, tooltipped button (not nothing, not a
 * crash) when the browser has no `SpeechRecognition` at all (Firefox,
 * Safari).
 */
export function VoiceCommandButton({ onSubmit, disabled = false }: VoiceCommandButtonProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [heard, setHeard] = useState<string | null>(null);
  const [result, setResult] = useState<VoiceCommandResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  const SpeechRecognitionCtor = getSpeechRecognitionConstructor();

  async function applyTranscript(transcript: string) {
    setHeard(transcript);
    setStatus("processing");
    setError(null);
    try {
      const applied = await onSubmit(transcript);
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

  function handleClick() {
    if (SpeechRecognitionCtor === null || status === "listening" || status === "processing") {
      return;
    }
    setResult(null);
    setError(null);
    setHeard(null);

    const recognition = new SpeechRecognitionCtor();
    recognition.lang = LOCALE;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const transcript = event.results[0]?.[0]?.transcript ?? "";
      void applyTranscript(transcript);
    };
    recognition.onerror = () => {
      setStatus("error");
      setError("No se pudo escuchar el micrófono. Intenta de nuevo.");
    };
    recognition.onend = () => {
      // Only idle-out a still-`listening` state (no result/error fired) —
      // `applyTranscript` already moved status to "processing"/"done"/"error".
      setStatus((current) => (current === "listening" ? "idle" : current));
    };

    recognitionRef.current = recognition;
    setStatus("listening");
    recognition.start();
  }

  if (SpeechRecognitionCtor === null) {
    return (
      <Button
        type="button"
        variant="outline"
        size="lg"
        disabled
        title="Tu navegador no soporta reconocimiento de voz. Probá con Chrome o Edge."
      >
        <MicOff />
        Comando de voz
      </Button>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <Button
        type="button"
        variant="outline"
        size="lg"
        onClick={handleClick}
        disabled={disabled || status === "listening" || status === "processing"}
        aria-live="polite"
      >
        {status === "processing" ? <Loader2 className="animate-spin" /> : <Mic />}
        {status === "listening"
          ? "Escuchando..."
          : status === "processing"
            ? "Procesando..."
            : "Comando de voz"}
      </Button>

      {heard !== null && status !== "listening" ? (
        <p className="text-xs text-muted-foreground">Se escuchó: &ldquo;{heard}&rdquo;</p>
      ) : null}

      {result !== null ? (
        <ul className="flex flex-col gap-1 text-xs">
          {result.applied.length === 0 ? (
            <li className="text-muted-foreground">No se aplicó ningún cambio.</li>
          ) : (
            result.applied.map((item, index) => (
              <li
                key={index}
                className={item.ok ? "text-foreground" : "text-destructive"}
              >
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
