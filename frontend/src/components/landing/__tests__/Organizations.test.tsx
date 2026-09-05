import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Organizations } from "@/components/landing/Organizations";

describe("Organizations", () => {
  it("renders the multi-tenant pitch and the role example card", () => {
    render(<Organizations />);

    expect(
      screen.getByRole("heading", {
        name: "Pensado para organizaciones, no solo para proyectos sueltos",
      })
    ).toBeInTheDocument();

    expect(screen.getByText(/Roles por miembro: owner, editor y lector/)).toBeInTheDocument();
    expect(screen.getByText("Owner")).toBeInTheDocument();
    expect(screen.getByText("Editor")).toBeInTheDocument();
    expect(screen.getByText("Lector")).toBeInTheDocument();
  });
});
