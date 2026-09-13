import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RemoveClassControl } from "@/components/workspace/RemoveClassControl";

const classes = [
  { id: "c1", name: "Cliente", visibility: "public" as const, attributes: [], operations: [] },
  { id: "c2", name: "Pedido", visibility: "public" as const, attributes: [], operations: [] },
];

const relationships = [
  {
    id: "r1",
    kind: "association" as const,
    source: { class_id: "c1", multiplicity: { lower: 1, upper: 1 }, role: null },
    target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
    name: null,
  },
  {
    id: "r2",
    kind: "association" as const,
    source: { class_id: "c2", multiplicity: { lower: 1, upper: 1 }, role: null },
    target: { class_id: "c1", multiplicity: { lower: 0, upper: null }, role: null },
    name: null,
  },
  {
    id: "r3",
    kind: "association" as const,
    source: { class_id: "c2", multiplicity: { lower: 1, upper: 1 }, role: null },
    target: { class_id: "c2", multiplicity: { lower: 0, upper: null }, role: null },
    name: null,
  },
];

/**
 * Presentational (design.md DD2/DD3/DD4/DD5). The cascade count is derived
 * at render from `relationships` (source-or-target filter, mirroring
 * `remove_class`'s own backend filter and `page.tsx`'s
 * `danglingRelationshipCount`). Submission is gated behind a confirmation
 * branch (DD4); `RemoveClass` is never submitted before `Confirmar` is
 * clicked.
 */
describe("RemoveClassControl", () => {
  it("selecting a class with 2 of 3 relationships shows a confirmation step stating exactly 2, and does not submit", () => {
    render(
      <RemoveClassControl classes={classes} relationships={relationships} onSubmit={vi.fn()} />,
    );

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    expect(screen.getByText(/Se eliminarán también 2 relación\(es\)/)).toBeInTheDocument();
  });

  it("does not submit RemoveClass while the confirmation step is showing and not yet confirmed", () => {
    const onSubmit = vi.fn();
    render(
      <RemoveClassControl classes={classes} relationships={relationships} onSubmit={onSubmit} />,
    );

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("Confirmar submits RemoveClass exactly once for the selected class and refetch is left to the caller", async () => {
    const onSubmit = vi
      .fn()
      .mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    render(
      <RemoveClassControl classes={classes} relationships={relationships} onSubmit={onSubmit} />,
    );

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirmar eliminación" }));

    await vi.waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
    expect(onSubmit).toHaveBeenCalledWith({ type: "RemoveClass", class_id: "c1" });
  });

  it("a class with zero relationships still requires confirmation before RemoveClass is submitted", () => {
    const onSubmit = vi.fn();
    const classWithNoRelationships = [
      { id: "c9", name: "Aislada", visibility: "public" as const, attributes: [], operations: [] },
    ];
    render(
      <RemoveClassControl
        classes={classWithNoRelationships}
        relationships={relationships}
        onSubmit={onSubmit}
      />,
    );

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c9" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    expect(screen.getByRole("button", { name: "Confirmar eliminación" })).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
    // DD5: the cascade line is omitted entirely at count 0, not shown as
    // "0 relación(es)" (spec.md's corrected scenario text).
    expect(screen.queryByText(/relación\(es\) que la referencian/)).not.toBeInTheDocument();
  });

  it("Cancelar returns to the select with zero onSubmit calls", () => {
    const onSubmit = vi.fn();
    render(
      <RemoveClassControl classes={classes} relationships={relationships} onSubmit={onSubmit} />,
    );

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancelar" }));

    expect(screen.getByLabelText("Clase")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirmar eliminación" })).not.toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("a stale selected id disappearing after rerender collapses the select to unset and disables Eliminar", () => {
    const { rerender } = render(
      <RemoveClassControl classes={classes} relationships={relationships} onSubmit={vi.fn()} />,
    );

    fireEvent.change(screen.getByLabelText("Clase"), { target: { value: "c1" } });
    expect(screen.getByLabelText("Clase")).toHaveValue("c1");

    rerender(
      <RemoveClassControl
        classes={[classes[1]!]}
        relationships={relationships}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Clase")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDisabled();
  });
});
