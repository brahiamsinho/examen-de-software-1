import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ImageImportButton } from "@/components/workspace/ImageImportButton";
import { ApiError } from "@/lib/api";
import type { ImageImportPreview } from "@/lib/image_command";
import type { VoiceCommandResult } from "@/lib/voice_command";

const file = new File(["fake-image-bytes"], "diagrama.png", { type: "image/png" });

const SUCCESS_RESULT: VoiceCommandResult = {
  revision: 2,
  applied: [{ ok: true, message: "Created class 'Persona'" }],
};

describe("ImageImportButton", () => {
  it("passes the chosen file to preview and only applies after confirmation", async () => {
    const onPreview = vi.fn().mockResolvedValue({ plan_id: "plan-1", base_revision: 1, changes: SUCCESS_RESULT.applied } satisfies ImageImportPreview);
    const onConfirm = vi.fn().mockResolvedValue(SUCCESS_RESULT);
    render(<ImageImportButton onPreview={onPreview} onConfirm={onConfirm} />);

    fireEvent.change(screen.getByLabelText("Imagen del diagrama UML"), { target: { files: [file] } });

    expect(onPreview).toHaveBeenCalledWith(file);
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toHaveTextContent("Created class 'Persona'");
    });
    expect(onConfirm).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Aplicar cambios" }));
    await waitFor(() => expect(onConfirm).toHaveBeenCalledWith("plan-1"));
    expect(await screen.findByText("✓ Created class 'Persona'")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Importar imagen" })).toBeEnabled();
  });

  it("renders a per-command failure alongside a successful one in the same result", async () => {
    const onPreview = vi.fn().mockResolvedValue({ plan_id: "plan-1", base_revision: 1, changes: [
        { ok: true, message: "Created class 'Persona'" },
        { ok: false, message: "Unknown class 'Ghost'" },
      ] } satisfies ImageImportPreview);
    render(<ImageImportButton onPreview={onPreview} onConfirm={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Imagen del diagrama UML"), { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toHaveTextContent("Created class 'Persona'");
    });
    expect(screen.getByRole("dialog")).toHaveTextContent("Unknown class 'Ghost'");
  });

  it("shows the server's error detail when the backend call fails", async () => {
    const onPreview = vi
      .fn()
      .mockRejectedValue(new ApiError({ status: 400, code: "invalid_image", detail: "Unsupported image type." }));
    render(<ImageImportButton onPreview={onPreview} onConfirm={vi.fn()} />);

    fireEvent.change(screen.getByLabelText("Imagen del diagrama UML"), { target: { files: [file] } });

    expect(await screen.findByRole("alert")).toHaveTextContent("Unsupported image type.");
  });

  it("is disabled when the disabled prop is set", () => {
    render(<ImageImportButton onPreview={vi.fn()} onConfirm={vi.fn()} disabled />);

    expect(screen.getByRole("button", { name: "Importar imagen" })).toBeDisabled();
  });
});
