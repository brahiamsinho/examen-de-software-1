import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DownloadBackendButton } from "@/components/workspace/DownloadBackendButton";
import { ApiError } from "@/lib/api";

describe("DownloadBackendButton", () => {
  it("renders the Spanish label and calls onDownload on click", async () => {
    const onDownload = vi.fn().mockResolvedValue(undefined);
    render(<DownloadBackendButton onDownload={onDownload} />);

    fireEvent.click(screen.getByRole("button", { name: "Descargar backend" }));

    expect(onDownload).toHaveBeenCalledTimes(1);
    await vi.waitFor(() => {
      expect(screen.getByRole("button", { name: "Descargar backend" })).toBeEnabled();
    });
  });

  it("shows a loading state and disables the button while the download is pending", async () => {
    let resolveDownload: () => void = () => {};
    const onDownload = vi.fn(
      () => new Promise<void>((resolve) => { resolveDownload = resolve; }),
    );
    render(<DownloadBackendButton onDownload={onDownload} />);

    fireEvent.click(screen.getByRole("button", { name: "Descargar backend" }));

    const busy = await screen.findByRole("button", { name: "Generando..." });
    expect(busy).toBeDisabled();
    fireEvent.click(busy);
    expect(onDownload).toHaveBeenCalledTimes(1);

    resolveDownload();
    await vi.waitFor(() => {
      expect(screen.getByRole("button", { name: "Descargar backend" })).toBeEnabled();
    });
  });

  it("shows the server detail in an alert when the API rejects with a 422", async () => {
    const onDownload = vi.fn().mockRejectedValue(
      new ApiError({
        status: 422,
        code: "nothing_to_generate",
        detail: "El documento no tiene clases para generar.",
      }),
    );
    render(<DownloadBackendButton onDownload={onDownload} />);

    fireEvent.click(screen.getByRole("button", { name: "Descargar backend" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El documento no tiene clases para generar.",
    );
    expect(screen.getByRole("button", { name: "Descargar backend" })).toBeEnabled();
  });

  it("shows a generic message for a non-API error and clears it on the next attempt", async () => {
    const onDownload = vi
      .fn()
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce(undefined);
    render(<DownloadBackendButton onDownload={onDownload} />);

    fireEvent.click(screen.getByRole("button", { name: "Descargar backend" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Ocurrió un error inesperado");

    fireEvent.click(screen.getByRole("button", { name: "Descargar backend" }));
    await vi.waitFor(() => {
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
  });

  it("is disabled when the disabled prop is set", () => {
    render(<DownloadBackendButton onDownload={vi.fn()} disabled />);

    expect(screen.getByRole("button", { name: "Descargar backend" })).toBeDisabled();
  });
});
