import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DocumentGrid } from "@/components/workspace/DocumentGrid";

const docA = { id: "doc-1", name: "Ventas", revision: 4, updated_at: "2026-09-12T10:05:00Z" };
const docB = { id: "doc-2", name: "  ", revision: 1, updated_at: "2026-09-11T10:00:00Z" };

describe("DocumentGrid", () => {
  it("renders one card per document, each a link to /documents/{id}", () => {
    render(<DocumentGrid documents={[docA, docB]} />);

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(2);
    expect(links[0]).toHaveAttribute("href", "/documents/doc-1");
    expect(links[1]).toHaveAttribute("href", "/documents/doc-2");
  });

  it("shows name, revision and the updated timestamp on each card", () => {
    const { container } = render(<DocumentGrid documents={[docA]} />);

    expect(screen.getByText("Ventas")).toBeInTheDocument();
    expect(screen.getByText("Revisión 4")).toBeInTheDocument();
    expect(screen.getByText(/Actualizado/)).toBeInTheDocument();
    expect(container.querySelector("time")).toHaveAttribute("datetime", "2026-09-12T10:05:00Z");
  });

  it('falls back to "Sin título" for a blank name', () => {
    render(<DocumentGrid documents={[docB]} />);

    expect(screen.getByText("Sin título")).toBeInTheDocument();
    expect(screen.getByText("Revisión 1")).toBeInTheDocument();
  });

  it("omits the updated line when the timestamp is invalid", () => {
    render(<DocumentGrid documents={[{ ...docA, updated_at: "not-a-date" }]} />);

    expect(screen.queryByText(/Actualizado/)).not.toBeInTheDocument();
  });

  it("renders a friendly empty state with the provided actions, not an empty list", () => {
    render(<DocumentGrid documents={[]} emptyActions={<button type="button">Nuevo diagrama</button>} />);

    expect(screen.getByRole("heading", { name: "Todavía no hay diagramas" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Nuevo diagrama" })).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("the read-only empty state offers no actions", () => {
    render(<DocumentGrid documents={[]} />);

    expect(screen.getByRole("heading", { name: "Todavía no hay diagramas" })).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});

describe("DocumentGrid delete action", () => {
  it("shows a delete button per card only when onDelete is provided", () => {
    const { rerender } = render(<DocumentGrid documents={[docA]} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();

    const onDelete = vi.fn();
    rerender(<DocumentGrid documents={[docA]} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole("button", { name: "Eliminar diagrama Ventas" }));

    expect(onDelete).toHaveBeenCalledWith(docA);
  });
});
