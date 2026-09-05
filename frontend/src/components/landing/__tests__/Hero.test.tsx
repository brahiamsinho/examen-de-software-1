import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Hero } from "@/components/landing/Hero";

describe("Hero", () => {
  it("renders the headline as the page h1", () => {
    render(<Hero />);

    expect(
      screen.getByRole("heading", {
        level: 1,
        name: /un modelo uml, una sola verdad/i,
      })
    ).toBeInTheDocument();
  });

  it("renders the primary and secondary CTAs", () => {
    render(<Hero />);

    expect(screen.getByRole("link", { name: "Empezar gratis" })).toHaveAttribute(
      "href",
      "#precios"
    );
    expect(screen.getByRole("link", { name: "Ver cómo funciona" })).toHaveAttribute(
      "href",
      "#producto"
    );
  });
});
