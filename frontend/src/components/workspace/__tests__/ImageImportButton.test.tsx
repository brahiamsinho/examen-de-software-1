import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ImageImportButton } from "@/components/workspace/ImageImportButton";
import { ApiError } from "@/lib/api";
import type { VoiceCommandResult } from "@/lib/voice_command";

const file = new File(["fake-image-bytes"], "diagrama.png", { type: "image/png" });

const SUCCESS_RESULT: VoiceCommandResult = {
  revision: 2,
  applied: [{ ok: true, message: "Created class 'Persona'" }],
};

describe("ImageImportButton", () => {
  it("passes the chosen file to onSubmit and reports what was applied", async () => {
    const onSubmit = vi.fn().mockResolvedValue(SUCCESS_RESULT);
    render(<ImageImportButton onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Imagen del diagrama UML"), { target: { files: [file] } });

    expect(onSubmit).toHaveBeenCalledWith(file);
    await waitFor(() => {
      expect(screen.getByText("✓ Created class 'Persona'")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Importar imagen" })).toBeEnabled();
  });

  it("renders a per-command failure alongside a successful one in the same result", async () => {
    const onSubmit = vi.fn().mockResolvedValue({
      revision: 2,
      applied: [
        { ok: true, message: "Created class 'Persona'" },
        { ok: false, message: "Unknown class 'Ghost'" },
      ],
    } satisfies VoiceCommandResult);
    render(<ImageImportButton onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Imagen del diagrama UML"), { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("✓ Created class 'Persona'")).toBeInTheDocument();
    });
    expect(screen.getByText("✗ Unknown class 'Ghost'")).toBeInTheDocument();
  });

  it("shows the server's error detail when the backend call fails", async () => {
    const onSubmit = vi
      .fn()
      .mockRejectedValue(new ApiError({ status: 400, code: "invalid_image", detail: "Unsupported image type." }));
    render(<ImageImportButton onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText("Imagen del diagrama UML"), { target: { files: [file] } });

    expect(await screen.findByRole("alert")).toHaveTextContent("Unsupported image type.");
  });

  it("is disabled when the disabled prop is set", () => {
    render(<ImageImportButton onSubmit={vi.fn()} disabled />);

    expect(screen.getByRole("button", { name: "Importar imagen" })).toBeDisabled();
  });
});
