import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OrgSwitcher } from "@/components/workspace/OrgSwitcher";

/**
 * Purely presentational (design.md "components/workspace ... presentational,
 * no fetch"): `OrgSwitcher` receives `organizations`/`activeSlug`/`onSelect`
 * as props instead of calling `useOrganizations()` itself. Persistence to
 * localStorage and the stale-slug fallback are owned by `useOrganizations()`
 * and already covered by `state/__tests__/organizations.test.ts` (Phase 3);
 * this component only needs to prove it renders the given state and forwards
 * a selection. The real container wiring (which is what actually persists a
 * selection) is exercised by `AppTopbar.test.tsx`.
 */
const orgA = { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const };
const orgB = { id: "2", name: "Beta", slug: "beta", plan: "free", my_role: "EDITOR" as const };

describe("OrgSwitcher", () => {
  it("lists every organization with its role", () => {
    render(<OrgSwitcher organizations={[orgA, orgB]} activeSlug="acme" onSelect={vi.fn()} />);

    expect(screen.getByRole("button", { name: /Acme/ })).toBeInTheDocument();
    expect(screen.getByText("Propietario")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Beta/ })).toBeInTheDocument();
    expect(screen.getByText("Editor")).toBeInTheDocument();
  });

  it("marks the active organization and calls onSelect with the clicked slug", () => {
    const onSelect = vi.fn();
    render(<OrgSwitcher organizations={[orgA, orgB]} activeSlug="acme" onSelect={onSelect} />);

    expect(screen.getByRole("button", { name: /Acme/ })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: /Beta/ }));
    expect(onSelect).toHaveBeenCalledWith("beta");
  });

  it("renders no active button when activeSlug matches no membership", () => {
    render(<OrgSwitcher organizations={[orgA, orgB]} activeSlug="ghost" onSelect={vi.fn()} />);

    expect(screen.getByRole("button", { name: /Acme/ })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("button", { name: /Beta/ })).toHaveAttribute("aria-pressed", "false");
  });

  it("renders nothing when there are no organizations", () => {
    const { container } = render(
      <OrgSwitcher organizations={[]} activeSlug={null} onSelect={vi.fn()} />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
