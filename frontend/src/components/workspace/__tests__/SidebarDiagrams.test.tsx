import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SidebarDiagrams } from "@/components/workspace/SidebarDiagrams";

const docA = { id: "doc-1", name: "Ventas", revision: 4, updated_at: "2026-09-12T10:05:00Z" };
const docB = { id: "doc-2", name: "", revision: 1, updated_at: "2026-09-11T10:00:00Z" };

describe("SidebarDiagrams", () => {
  it("lists only diagrams as links to their document page", () => {
    render(<SidebarDiagrams documents={[docA, docB]} loading={false} activeDocId={null} />);

    expect(screen.getByRole("link", { name: "Ventas" })).toHaveAttribute("href", "/documents/doc-1");
    expect(screen.getByRole("link", { name: "Sin título" })).toHaveAttribute(
      "href",
      "/documents/doc-2",
    );
  });

  it("marks the active diagram with aria-current", () => {
    render(<SidebarDiagrams documents={[docA, docB]} loading={false} activeDocId="doc-1" />);

    expect(screen.getByRole("link", { name: "Ventas" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Sin título" })).not.toHaveAttribute("aria-current");
  });

  it("shows a subtle empty state when there are no diagrams", () => {
    render(<SidebarDiagrams documents={[]} loading={false} activeDocId={null} />);

    expect(screen.getByText("Todavía no hay diagramas")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("shows a loading hint instead of the empty state while fetching", () => {
    render(<SidebarDiagrams documents={[]} loading activeDocId={null} />);

    expect(screen.getByText("Cargando…")).toBeInTheDocument();
    expect(screen.queryByText("Todavía no hay diagramas")).not.toBeInTheDocument();
  });

  it('renders the "+" only when onNew is provided and calls it on click', () => {
    const onNew = vi.fn();
    const { rerender } = render(
      <SidebarDiagrams documents={[]} loading={false} activeDocId={null} onNew={onNew} />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Nuevo diagrama" }));
    expect(onNew).toHaveBeenCalledOnce();

    rerender(<SidebarDiagrams documents={[]} loading={false} activeDocId={null} />);
    expect(screen.queryByRole("button", { name: "Nuevo diagrama" })).not.toBeInTheDocument();
  });
});
