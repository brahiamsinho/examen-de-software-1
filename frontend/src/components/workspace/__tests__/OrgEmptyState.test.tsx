import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { OrgEmptyState } from "@/components/workspace/OrgEmptyState";

describe("OrgEmptyState", () => {
  it("renders a non-blocking prompt to create the first organization", () => {
    render(<OrgEmptyState />);

    expect(
      screen.getByRole("heading", { name: "Crea tu primera organización" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Aún no perteneces a ninguna organización/)).toBeInTheDocument();
  });
});
