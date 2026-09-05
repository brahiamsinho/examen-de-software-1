import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Footer } from "@/components/landing/Footer";

describe("Footer", () => {
  it("renders the brand and the section links", () => {
    render(<Footer />);

    expect(screen.getByText("© 2026 Modelia")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Producto" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Organizaciones" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Precios" }).length).toBeGreaterThan(0);
  });
});
