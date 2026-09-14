import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ValidationPanel } from "@/components/workspace/ValidationPanel";

/**
 * Renders non-blockingly from `lastValidation` (DD13): `null` until the
 * first command, then every diagnostic regardless of `is_valid`. Exposes no
 * prop that could disable another form — this panel is purely display.
 */
describe("ValidationPanel", () => {
  it("renders nothing when lastValidation is null", () => {
    const { container } = render(<ValidationPanel lastValidation={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders every Diagnostic field for both severities and never disables anything", () => {
    render(
      <ValidationPanel
        lastValidation={{
          is_valid: false,
          violations: [
            { severity: "error", code: "duplicate_name", message: "Nombre duplicado", path: "model.classes[0].name" },
            { severity: "warning", code: "unused_class", message: "Clase sin relaciones", path: "model.classes[1]" },
          ],
        }}
      />,
    );

    expect(screen.getByText("error")).toBeInTheDocument();
    expect(screen.getByText("duplicate_name")).toBeInTheDocument();
    expect(screen.getByText("Nombre duplicado")).toBeInTheDocument();
    expect(screen.getByText("model.classes[0].name")).toBeInTheDocument();

    expect(screen.getByText("warning")).toBeInTheDocument();
    expect(screen.getByText("unused_class")).toBeInTheDocument();
    expect(screen.getByText("Clase sin relaciones")).toBeInTheDocument();
    expect(screen.getByText("model.classes[1]")).toBeInTheDocument();

    expect(document.querySelector("[disabled]")).toBeNull();
  });
});
