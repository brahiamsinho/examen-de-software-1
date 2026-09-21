import { act, fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OrgSwitcher } from "@/components/workspace/OrgSwitcher";

/**
 * Presentational: `OrgSwitcher` receives `organizations`/`activeSlug`/
 * `onSelect`/`onCreate` as props (persistence and the stale-slug fallback
 * belong to `useOrganizations()`, covered in `state/__tests__`). The trigger
 * shows the current org; the menu switches or opens the create dialog.
 */
const orgA = { id: "1", name: "Acme", slug: "acme", plan: "free", my_role: "OWNER" as const };
const orgB = { id: "2", name: "Beta", slug: "beta", plan: "free", my_role: "EDITOR" as const };

function open() {
  const trigger = screen.getByRole("button", { name: /Acme|Sin organización/ });
  act(() => {
    fireEvent.pointerDown(trigger, { button: 0 });
    fireEvent.mouseDown(trigger, { button: 0 });
    fireEvent.click(trigger, { button: 0 });
  });
}

describe("OrgSwitcher", () => {
  it("shows the current organization's name and role on the trigger", () => {
    render(
      <OrgSwitcher organizations={[orgA, orgB]} activeSlug="acme" onSelect={vi.fn()} onCreate={vi.fn()} />,
    );

    const trigger = screen.getByRole("button", { name: /Acme/ });
    expect(trigger).toHaveTextContent("Propietario");
    expect(trigger).toHaveAttribute("aria-haspopup", "menu");
  });

  it("lists every organization in the menu and switches on selection", async () => {
    const onSelect = vi.fn();
    render(
      <OrgSwitcher organizations={[orgA, orgB]} activeSlug="acme" onSelect={onSelect} onCreate={vi.fn()} />,
    );
    open();

    expect(await screen.findByRole("menuitemradio", { name: /Acme/ })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    const beta = screen.getByRole("menuitemradio", { name: /Beta/ });
    expect(beta).toHaveAttribute("aria-checked", "false");
    expect(beta).toHaveTextContent("Editor");

    fireEvent.click(beta);
    expect(onSelect).toHaveBeenCalledWith("beta");
  });

  it('"Crear organización" opens a dialog with the creation form and submits through onCreate', async () => {
    const created = { id: "3", name: "Gamma", slug: "gamma", plan: "free", my_role: "OWNER" as const };
    const onCreate = vi.fn().mockResolvedValue(created);
    render(
      <OrgSwitcher organizations={[orgA]} activeSlug="acme" onSelect={vi.fn()} onCreate={onCreate} />,
    );
    open();

    fireEvent.click(await screen.findByRole("menuitem", { name: "Crear organización" }));

    expect(await screen.findByRole("dialog", { name: "Crear organización" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Nombre de la organización"), {
      target: { value: "Gamma" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Crear organización" }));

    await vi.waitFor(() => expect(onCreate).toHaveBeenCalledWith({ name: "Gamma", slug: "gamma" }));
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("with no organizations it still renders, offering only creation", async () => {
    render(<OrgSwitcher organizations={[]} activeSlug={null} onSelect={vi.fn()} onCreate={vi.fn()} />);

    expect(screen.getByRole("button", { name: /Sin organización/ })).toBeInTheDocument();
    open();

    expect(await screen.findByRole("menuitem", { name: "Crear organización" })).toBeInTheDocument();
    expect(screen.queryByRole("menuitemradio")).not.toBeInTheDocument();
  });
});
