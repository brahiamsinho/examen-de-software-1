import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MemberRow } from "@/components/workspace/MemberRow";
import type { Member, Role } from "@/lib/organizations";

/**
 * Spec `web-member-management` §§ Add/Change Role/Remove/Last-Owner Error —
 * covers every control this row can show, per design.md DD7 (OWNER option is
 * always disabled/unofferable) and DD5 (single-slot row error).
 */
const owner: Member = {
  user_id: "1",
  email: "owner@example.com",
  full_name: "Owner One",
  role: "OWNER",
  created_at: "2026-01-01T00:00:00Z",
};
const editor: Member = {
  user_id: "2",
  email: "editor@example.com",
  full_name: "Editor One",
  role: "EDITOR",
  created_at: "2026-01-02T00:00:00Z",
};

type MemberRowProps = {
  member: Member;
  isSelf: boolean;
  canManage: boolean;
  rowError: { userId: string; message: string } | null;
  onChangeRole: (userId: string, role: Exclude<Role, "OWNER">) => void;
  onRemove: (userId: string) => void;
  onLeave: (userId: string) => void;
};

function renderRow(overrides: Partial<MemberRowProps> = {}) {
  const onChangeRole = vi.fn();
  const onRemove = vi.fn();
  const onLeave = vi.fn();
  const props: MemberRowProps = {
    member: editor,
    isSelf: false,
    canManage: true,
    rowError: null,
    onChangeRole,
    onRemove,
    onLeave,
    ...overrides,
  };

  const utils = render(
    <ul>
      <MemberRow {...props} />
    </ul>,
  );
  return { ...utils, onChangeRole, onRemove, onLeave };
}

describe("MemberRow", () => {
  it("an OWNER row shows the current value disabled and never offers OWNER as a target", () => {
    const { onChangeRole } = renderRow({ member: owner, canManage: true, isSelf: true });

    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select).toHaveValue("OWNER");
    const ownerOption = screen.getByRole("option", { name: "Propietario" }) as HTMLOptionElement;
    expect(ownerOption.disabled).toBe(true);

    fireEvent.change(select, { target: { value: "EDITOR" } });
    expect(onChangeRole).toHaveBeenCalledWith(owner.user_id, "EDITOR");
  });

  it("an EDITOR/VIEWER row's select offers only EDITOR and VIEWER", () => {
    renderRow({ member: editor, canManage: true });

    const select = screen.getByRole("combobox");
    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Editor", "Lector"]);
    expect(select).toHaveValue("EDITOR");
  });

  it("changing the role calls onChangeRole with the row's userId and the new role", () => {
    const { onChangeRole } = renderRow({ member: editor, canManage: true });

    fireEvent.change(screen.getByRole("combobox"), { target: { value: "VIEWER" } });

    expect(onChangeRole).toHaveBeenCalledWith(editor.user_id, "VIEWER");
  });

  it("hides the role select for a non-owner viewer, showing the role as plain text instead", () => {
    renderRow({ member: editor, canManage: false });

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.getByText("Editor")).toBeInTheDocument();
  });

  it("shows a remove-other control only for an OWNER viewer on someone else's row", () => {
    renderRow({ member: editor, canManage: true, isSelf: false });

    expect(screen.getByRole("button", { name: "Eliminar" })).toBeInTheDocument();
  });

  it("hides the remove-other control for a non-owner viewer", () => {
    renderRow({ member: editor, canManage: false, isSelf: false });

    expect(screen.queryByRole("button", { name: "Eliminar" })).not.toBeInTheDocument();
  });

  it("hides the remove-other control on the viewer's own row even when they can manage", () => {
    renderRow({ member: editor, canManage: true, isSelf: true });

    expect(screen.queryByRole("button", { name: "Eliminar" })).not.toBeInTheDocument();
  });

  it("always renders the self-leave control on the viewer's own row, regardless of role", () => {
    renderRow({ member: editor, canManage: false, isSelf: true });

    expect(screen.getByRole("button", { name: "Salir de la organización" })).toBeInTheDocument();
  });

  it("clicking leave calls onLeave with the row's userId", () => {
    const { onLeave } = renderRow({ member: editor, canManage: false, isSelf: true });

    fireEvent.click(screen.getByRole("button", { name: "Salir de la organización" }));

    expect(onLeave).toHaveBeenCalledWith(editor.user_id);
  });

  it("clicking remove calls onRemove with the row's userId", () => {
    const { onRemove } = renderRow({ member: editor, canManage: true, isSelf: false });

    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    expect(onRemove).toHaveBeenCalledWith(editor.user_id);
  });

  it("renders the row error only when it matches this row's userId", () => {
    renderRow({
      member: editor,
      rowError: { userId: editor.user_id, message: "No se puede quitar al único propietario." },
    });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "No se puede quitar al único propietario.",
    );
  });

  it("does not render a row error that belongs to a different row", () => {
    renderRow({ member: editor, rowError: { userId: "999", message: "Otro error" } });

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
