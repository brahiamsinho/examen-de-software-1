import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OrgPicker } from "@/components/workspace/OrgPicker";

/**
 * Presentational one-time picker (design.md DD4). No `activeSlug`: nothing
 * is active yet at this point in the flow, so a "current" affordance would
 * be a lie (unlike `OrgSwitcher`, which mid-session switches an existing
 * active org).
 */
const orgA = { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const };
const orgB = { id: "2", name: "Beta", slug: "beta", plan: "free", my_role: "EDITOR" as const };

describe("OrgPicker", () => {
  it("lists every organization with its role label", () => {
    render(<OrgPicker organizations={[orgA, orgB]} onSelect={vi.fn()} />);

    expect(screen.getByRole("button", { name: /Acme/ })).toBeInTheDocument();
    expect(screen.getByText("Propietario")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Beta/ })).toBeInTheDocument();
    expect(screen.getByText("Editor")).toBeInTheDocument();
  });

  it("calls onSelect with the chosen organization's slug", () => {
    const onSelect = vi.fn();
    render(<OrgPicker organizations={[orgA, orgB]} onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: /Beta/ }));

    expect(onSelect).toHaveBeenCalledWith("beta");
  });
});
