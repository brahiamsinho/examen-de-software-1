import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Features } from "@/components/landing/Features";

describe("Features", () => {
  it("renders the section heading and the four feature cards", () => {
    render(<Features />);

    expect(
      screen.getByRole("heading", { name: "Todo lo que necesita tu equipo, en un solo lugar" })
    ).toBeInTheDocument();

    expect(screen.getByText("Modelo canónico único")).toBeInTheDocument();
    expect(screen.getByText("Cuatro formas de modelar")).toBeInTheDocument();
    expect(screen.getByText("Generación de código")).toBeInTheDocument();
    expect(screen.getByText("Asistente con IA")).toBeInTheDocument();
  });
});
