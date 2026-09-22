import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { VoiceCommandButton } from "@/components/workspace/VoiceCommandButton";
import { ApiError } from "@/lib/api";
import type { VoiceCommandResult } from "@/lib/voice_command";

/**
 * jsdom implements no Web Speech API at all, so every test controls it via
 * this hand-written fake installed on `window` — the same
 * install-a-fake-constructor-on-the-global convention
 * `lib/uml_documents.test.ts` uses for `WebSocket`.
 */
class FakeSpeechRecognition {
  static instances: FakeSpeechRecognition[] = [];
  lang = "";
  interimResults = false;
  maxAlternatives = 1;
  onresult: ((event: { results: { [i: number]: { [j: number]: { transcript: string } } } }) => void) | null =
    null;
  onerror: ((event: { error: string }) => void) | null = null;
  onend: (() => void) | null = null;
  start = vi.fn();
  stop = vi.fn(() => {
    this.onend?.();
  });

  constructor() {
    FakeSpeechRecognition.instances.push(this);
  }
}

function installFakeSpeechRecognition() {
  FakeSpeechRecognition.instances = [];
  Object.defineProperty(window, "SpeechRecognition", {
    value: FakeSpeechRecognition,
    configurable: true,
    writable: true,
  });
  return FakeSpeechRecognition;
}

function removeSpeechRecognition() {
  Reflect.deleteProperty(window, "SpeechRecognition");
  Reflect.deleteProperty(window, "webkitSpeechRecognition");
}

function emitResult(recognition: FakeSpeechRecognition, transcript: string) {
  recognition.onresult?.({ results: { 0: { 0: { transcript } } } });
}

const SUCCESS_RESULT: VoiceCommandResult = {
  revision: 2,
  applied: [{ ok: true, message: "Created class 'Persona'" }],
};

describe("VoiceCommandButton", () => {
  afterEach(() => {
    removeSpeechRecognition();
    vi.restoreAllMocks();
  });

  it("renders a disabled, tooltipped button when the browser has no SpeechRecognition", () => {
    removeSpeechRecognition();
    const onSubmit = vi.fn();

    render(<VoiceCommandButton onSubmit={onSubmit} />);

    const button = screen.getByRole("button", { name: "Comando de voz" });
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute("title", expect.stringContaining("no soporta"));
  });

  it("idle -> listening -> processing -> result: reports what was heard and what was applied", async () => {
    installFakeSpeechRecognition();
    const onSubmit = vi.fn().mockResolvedValue(SUCCESS_RESULT);

    render(<VoiceCommandButton onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Comando de voz" }));

    expect(screen.getByRole("button", { name: "Escuchando..." })).toBeInTheDocument();
    const [recognition] = FakeSpeechRecognition.instances;
    expect(recognition!.lang).toBe("es-AR");
    expect(recognition!.start).toHaveBeenCalledTimes(1);

    emitResult(recognition!, "creá una clase Persona");

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("creá una clase Persona");
    });
    expect(screen.getByText(/Se escuchó/)).toHaveTextContent("creá una clase Persona");

    await waitFor(() => {
      expect(screen.getByText("✓ Created class 'Persona'")).toBeInTheDocument();
    });
    // Back to idle, ready for another utterance.
    expect(screen.getByRole("button", { name: "Comando de voz" })).not.toBeDisabled();
  });

  it("renders a per-command failure alongside a successful one in the same result", async () => {
    installFakeSpeechRecognition();
    const onSubmit = vi.fn().mockResolvedValue({
      revision: 2,
      applied: [
        { ok: true, message: "Created class 'Persona'" },
        { ok: false, message: "Unknown class 'Ghost'" },
      ],
    } satisfies VoiceCommandResult);

    render(<VoiceCommandButton onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Comando de voz" }));
    emitResult(FakeSpeechRecognition.instances[0]!, "algo con dos comandos");

    await waitFor(() => {
      expect(screen.getByText("✓ Created class 'Persona'")).toBeInTheDocument();
    });
    expect(screen.getByText("✗ Unknown class 'Ghost'")).toBeInTheDocument();
  });

  it("shows the server's error detail when the backend call fails", async () => {
    installFakeSpeechRecognition();
    const onSubmit = vi
      .fn()
      .mockRejectedValue(new ApiError({ status: 503, code: "gemini_api_key_missing", detail: "GEMINI_API_KEY is not configured." }));

    render(<VoiceCommandButton onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Comando de voz" }));
    emitResult(FakeSpeechRecognition.instances[0]!, "creá una clase Persona");

    await waitFor(() => {
      expect(screen.getByText("GEMINI_API_KEY is not configured.")).toBeInTheDocument();
    });
  });

  it("a recognition error shows a generic listening-failure message", async () => {
    installFakeSpeechRecognition();
    const onSubmit = vi.fn();

    render(<VoiceCommandButton onSubmit={onSubmit} />);
    fireEvent.click(screen.getByRole("button", { name: "Comando de voz" }));
    FakeSpeechRecognition.instances[0]!.onerror?.({ error: "not-allowed" });

    await waitFor(() => {
      expect(screen.getByText(/No se pudo escuchar el micrófono/)).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
