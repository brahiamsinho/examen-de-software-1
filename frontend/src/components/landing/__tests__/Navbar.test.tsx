import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Navbar } from "@/components/landing/Navbar";

describe("Navbar", () => {
  it("renders the brand and the primary CTA", () => {
    render(<Navbar />);

    expect(screen.getByText("Modelia")).toBeInTheDocument();
    const cta = screen.getByRole("link", { name: "Empezar gratis" });
    expect(cta).toHaveAttribute("href", "#precios");
  });

  it("renders the section nav links", () => {
    render(<Navbar />);

    expect(screen.getByRole("link", { name: "Producto" })).toHaveAttribute("href", "#producto");
    expect(screen.getByRole("link", { name: "Organizaciones" })).toHaveAttribute(
      "href",
      "#organizaciones"
    );
    expect(screen.getByRole("link", { name: "Precios" })).toHaveAttribute("href", "#precios");
  });
});
