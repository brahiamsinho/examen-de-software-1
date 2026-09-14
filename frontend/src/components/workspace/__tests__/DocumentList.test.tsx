import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DocumentList } from "@/components/workspace/DocumentList";

const docA = { id: "doc-1", name: "Ventas", revision: 4, updated_at: "2026-09-12T10:05:00Z" };
const docB = { id: "doc-2", name: "Compras", revision: 1, updated_at: "2026-09-11T10:00:00Z" };

describe("DocumentList", () => {
  it("renders one li per document with a link to /documents/{id}", () => {
    render(<DocumentList documents={[docA, docB]} />);

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(2);
    expect(links[0]).toHaveAttribute("href", "/documents/doc-1");
    expect(links[1]).toHaveAttribute("href", "/documents/doc-2");
  });

  it("shows the document name and revision on each row", () => {
    render(<DocumentList documents={[docA]} />);

    expect(screen.getByText("Ventas")).toBeInTheDocument();
    expect(screen.getByText("Revisión 4")).toBeInTheDocument();
  });

  it("renders an empty-state message, not an empty <ul>, when there are zero documents", () => {
    render(<DocumentList documents={[]} />);

    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(
      screen.getByText("Todavía no tienes diagramas. Crea el primero con «Nuevo Diagrama»."),
    ).toBeInTheDocument();
  });
});
