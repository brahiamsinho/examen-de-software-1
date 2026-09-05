import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { FinalCta } from "@/components/landing/FinalCta";

describe("FinalCta", () => {
  it("renders the closing message and CTA", () => {
    render(<FinalCta />);

    expect(screen.getByText("Tu equipo ya tiene el modelo en la cabeza.")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Empezar gratis — sin tarjeta" })
    ).toBeInTheDocument();
  });
});
