import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { AddRelationshipControl } from "@/components/workspace/AddRelationshipControl";

const classes = [
  { id: "c1", name: "Cliente", visibility: "public" as const, attributes: [], operations: [] },
  { id: "c2", name: "Pedido", visibility: "public" as const, attributes: [], operations: [] },
];

/**
 * Click-click relationship state lives in the container (DD8); this control
 * is presentational. It builds the `association` `AddRelationship` command
 * with `crypto.randomUUID()` (DD10) and, on a successful `onSubmit`, calls
 * `onCancel` to clear both pending ids — the same reset the container's
 * "tap again = cancel" path already performs.
 */
describe("AddRelationshipControl", () => {
  it("renders nothing when pendingSourceId is null", () => {
    render(
      <AddRelationshipControl
        pendingSourceId={null}
        pendingTargetId={null}
        classes={classes}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.queryByText(/Cliente/)).not.toBeInTheDocument();
  });

  it("renders the pending-source prompt when only pendingSourceId is set", () => {
    render(
      <AddRelationshipControl
        pendingSourceId="c1"
        pendingTargetId={null}
        classes={classes}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByText(/Cliente/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Multiplicidad origen")).not.toBeInTheDocument();
  });

  it("renders both multiplicity selects when both ids are set", () => {
    render(
      <AddRelationshipControl
        pendingSourceId="c1"
        pendingTargetId="c2"
        classes={classes}
        onSubmit={vi.fn()}
        onCancel={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Multiplicidad origen")).toBeInTheDocument();
    expect(screen.getByLabelText("Multiplicidad destino")).toBeInTheDocument();
  });

  it("onSubmit builds an association AddRelationship command with a generated id and clears both ids on success", async () => {
    const onSubmit = vi.fn().mockResolvedValue({ revision: 2, validation: { is_valid: true, violations: [] } });
    const onCancel = vi.fn();
    render(
      <AddRelationshipControl
        pendingSourceId="c1"
        pendingTargetId="c2"
        classes={classes}
        onSubmit={onSubmit}
        onCancel={onCancel}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Confirmar relación" }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "AddRelationship",
        relationship: expect.objectContaining({
          kind: "association",
          source: expect.objectContaining({ class_id: "c1" }),
          target: expect.objectContaining({ class_id: "c2" }),
        }),
      }),
    );
    const [[command]] = onSubmit.mock.calls;
    expect(typeof command.relationship.id).toBe("string");
    expect(command.relationship.id.length).toBeGreaterThan(0);

    await vi.waitFor(() => {
      expect(onCancel).toHaveBeenCalledOnce();
    });
  });
});
