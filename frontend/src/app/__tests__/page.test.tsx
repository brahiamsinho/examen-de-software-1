import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import Home from "@/app/page";

describe("Home page", () => {
  it("composes every landing section", () => {
    render(<Home />);

    expect(
      screen.getByRole("heading", { level: 1, name: /un modelo uml, una sola verdad/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Todo lo que necesita tu equipo, en un solo lugar")).toBeInTheDocument();
    expect(
      screen.getByText("Pensado para organizaciones, no solo para proyectos sueltos")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Team").length).toBeGreaterThan(0);
    expect(screen.getByText("© 2026 Modelia")).toBeInTheDocument();
  });
});
