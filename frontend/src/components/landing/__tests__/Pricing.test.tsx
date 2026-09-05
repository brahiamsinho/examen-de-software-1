import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { Pricing } from "@/components/landing/Pricing";

describe("Pricing", () => {
  it("renders the three plan tiers", () => {
    render(<Pricing />);

    expect(screen.getByText("Starter")).toBeInTheDocument();
    expect(screen.getByText("Team")).toBeInTheDocument();
    expect(screen.getByText("Enterprise")).toBeInTheDocument();
  });

  it("never invents a real Team price — keeps the bracketed placeholder", () => {
    render(<Pricing />);

    expect(screen.getByText("[PRECIO]")).toBeInTheDocument();
    expect(screen.getByText("$0")).toBeInTheDocument();
    expect(screen.getByText("Hablemos")).toBeInTheDocument();
  });
});
