import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MembersList } from "@/components/workspace/MembersList";
import type { Member } from "@/lib/organizations";

/**
 * Spec `web-member-management` § Members List Visibility: email, role label,
 * and a self marker on the row matching the current user. Presentational
 * (design.md File Changes): composes `MemberRow` per member, props-in only.
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
const viewer: Member = {
  user_id: "3",
  email: "viewer@example.com",
  full_name: "Viewer One",
  role: "VIEWER",
  created_at: "2026-01-03T00:00:00Z",
};

describe("MembersList", () => {
  it("lists every member with email and role label under an accessible 'Miembros' list", () => {
    render(
      <MembersList
        members={[owner, editor, viewer]}
        currentUserId={editor.user_id}
        canManage={false}
        rowError={null}
        onChangeRole={() => {}}
        onRemove={() => {}}
        onLeave={() => {}}
      />,
    );

    expect(screen.getByRole("list", { name: "Miembros" })).toBeInTheDocument();
    expect(screen.getByText(owner.email)).toBeInTheDocument();
    expect(screen.getByText("Propietario")).toBeInTheDocument();
    expect(screen.getByText(editor.email)).toBeInTheDocument();
    expect(screen.getByText("Editor")).toBeInTheDocument();
    expect(screen.getByText(viewer.email)).toBeInTheDocument();
    expect(screen.getByText("Lector")).toBeInTheDocument();
  });

  it("marks only the row matching the current user with a self marker", () => {
    render(
      <MembersList
        members={[owner, editor, viewer]}
        currentUserId={editor.user_id}
        canManage={false}
        rowError={null}
        onChangeRole={() => {}}
        onRemove={() => {}}
        onLeave={() => {}}
      />,
    );

    const editorRow = screen.getByText(editor.email).closest("li");
    const ownerRow = screen.getByText(owner.email).closest("li");
    const viewerRow = screen.getByText(viewer.email).closest("li");

    expect(editorRow).toHaveTextContent("(Tú)");
    expect(ownerRow).not.toHaveTextContent("(Tú)");
    expect(viewerRow).not.toHaveTextContent("(Tú)");
  });
});
