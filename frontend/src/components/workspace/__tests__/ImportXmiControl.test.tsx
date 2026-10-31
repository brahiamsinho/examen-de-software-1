import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ImportXmiControl } from "@/components/workspace/ImportXmiControl";
import { ApiError } from "@/lib/api";

const file = new File(["<XMI/>"], "modelo.xml", { type: "application/xml" });

describe("ImportXmiControl", () => {
  it("passes the chosen file to onImport", async () => {
    const onImport = vi.fn().mockResolvedValue(undefined);
    render(<ImportXmiControl onImport={onImport} />);

    fireEvent.change(screen.getByLabelText("Archivo XML"), { target: { files: [file] } });

    expect(onImport).toHaveBeenCalledWith(file);
    await vi.waitFor(() => {
      expect(screen.getByRole("button", { name: "Importar XML" })).toBeEnabled();
    });
  });

  it("shows the server detail when the import is rejected", async () => {
    const onImport = vi.fn().mockRejectedValue(
      new ApiError({ status: 422, code: "invalid_xmi", detail: "El archivo no es un XML válido." }),
    );
    render(<ImportXmiControl onImport={onImport} />);

    fireEvent.change(screen.getByLabelText("Archivo XML"), { target: { files: [file] } });

    expect(await screen.findByRole("alert")).toHaveTextContent("El archivo no es un XML válido.");
  });

  it("is disabled when the disabled prop is set", () => {
    render(<ImportXmiControl onImport={vi.fn()} disabled />);

    expect(screen.getByRole("button", { name: "Importar XML" })).toBeDisabled();
  });
});
