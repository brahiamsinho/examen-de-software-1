import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { createStore, Provider } from "jotai";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MembersPage from "@/app/(app)/settings/members/page";
import { ApiError } from "@/lib/api";
import * as orgsLib from "@/lib/organizations";
import { activeOrgSlugAtom, organizationsAtom } from "@/state/organizations";
import { sessionAtom } from "@/state/session";

/**
 * Container page (design.md DD4/DD5/DD6): reads `organizationsAtom` /
 * `activeOrgSlugAtom` / `sessionAtom` directly (no `useOrganizations()` /
 * `useSession()` mount — those already run once in `AppTopbar`/
 * `SessionGuard`). `canManage` derives from `Organization.my_role`. Each
 * test seeds an explicit jotai `store` instead of relying on a fetch effect.
 */
vi.mock("@/lib/organizations", async () => {
  const actual = await vi.importActual<typeof import("@/lib/organizations")>("@/lib/organizations");
  return {
    ...actual,
    listMembers: vi.fn(),
    addMember: vi.fn(),
    changeMemberRole: vi.fn(),
    removeMember: vi.fn(),
  };
});

const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: mockReplace }) }));

const org = { id: "org-1", name: "Acme", slug: "acme", plan: "free" };
const ownerMember = {
  user_id: "owner-1",
  email: "owner@example.com",
  full_name: "Owner One",
  role: "OWNER" as const,
  created_at: "2026-01-01T00:00:00Z",
};
const editorMember = {
  user_id: "editor-1",
  email: "editor@example.com",
  full_name: "Editor One",
  role: "EDITOR" as const,
  created_at: "2026-01-02T00:00:00Z",
};

function renderPage({
  myRole,
  currentUser,
}: {
  myRole: "OWNER" | "EDITOR" | "VIEWER";
  currentUser: { id: string; email: string; full_name: string };
}) {
  const store = createStore();
  store.set(organizationsAtom, [{ ...org, my_role: myRole }]);
  store.set(activeOrgSlugAtom, org.slug);
  store.set(sessionAtom, { status: "authenticated", user: currentUser });

  return render(
    <Provider store={store}>
      <MembersPage />
    </Provider>,
  );
}

describe("MembersPage", () => {
  beforeEach(() => {
    vi.mocked(orgsLib.listMembers).mockReset();
    vi.mocked(orgsLib.addMember).mockReset();
    vi.mocked(orgsLib.changeMemberRole).mockReset();
    vi.mocked(orgsLib.removeMember).mockReset();
    mockReplace.mockReset();
  });

  it("an OWNER sees the add-member form and mutation controls", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([ownerMember, editorMember]);

    renderPage({
      myRole: "OWNER",
      currentUser: { id: ownerMember.user_id, email: ownerMember.email, full_name: ownerMember.full_name },
    });

    expect(await screen.findByRole("list", { name: "Miembros" })).toBeInTheDocument();
    expect(screen.getByLabelText("Correo electrónico")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeInTheDocument();
  });

  it("a non-OWNER sees the roster and an explanatory line, with no mutation controls but self-leave present", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([ownerMember, editorMember]);

    renderPage({
      myRole: "EDITOR",
      currentUser: { id: editorMember.user_id, email: editorMember.email, full_name: editorMember.full_name },
    });

    await screen.findByRole("list", { name: "Miembros" });
    expect(screen.queryByLabelText("Correo electrónico")).not.toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Eliminar" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salir de la organización" })).toBeInTheDocument();
    expect(screen.getByText(/Solo un propietario puede administrar/)).toBeInTheDocument();
  });

  it("a 409 role change on the sole owner renders inline on that row only, list unchanged", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([ownerMember]);
    vi.mocked(orgsLib.changeMemberRole).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "last_owner", detail: "No puedes quitar al único propietario." }),
    );

    renderPage({
      myRole: "OWNER",
      currentUser: { id: ownerMember.user_id, email: ownerMember.email, full_name: ownerMember.full_name },
    });

    const list = await screen.findByRole("list", { name: "Miembros" });
    await within(list).findByText(ownerMember.email);
    const select = within(list).getByRole("combobox");
    fireEvent.change(select, { target: { value: "EDITOR" } });

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No puedes quitar al único propietario.",
    );
    expect(within(list).getByRole("combobox")).toHaveValue("OWNER");
    expect(within(list).getAllByRole("listitem")).toHaveLength(1);
  });

  it("a 409 on self-leave for the sole owner renders inline on that row, member remains listed", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([ownerMember]);
    vi.mocked(orgsLib.removeMember).mockRejectedValueOnce(
      new ApiError({ status: 409, code: "last_owner", detail: "No puedes eliminar al único propietario." }),
    );

    renderPage({
      myRole: "OWNER",
      currentUser: { id: ownerMember.user_id, email: ownerMember.email, full_name: ownerMember.full_name },
    });

    fireEvent.click(await screen.findByRole("button", { name: "Salir de la organización" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No puedes eliminar al único propietario.",
    );
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("a successful add updates the list without a manual refetch", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([ownerMember]);
    const newMember = {
      user_id: "viewer-1",
      email: "viewer@example.com",
      full_name: "Viewer One",
      role: "VIEWER" as const,
      created_at: "2026-01-03T00:00:00Z",
    };
    vi.mocked(orgsLib.addMember).mockResolvedValueOnce(newMember);

    renderPage({
      myRole: "OWNER",
      currentUser: { id: ownerMember.user_id, email: ownerMember.email, full_name: ownerMember.full_name },
    });
    await screen.findByRole("list", { name: "Miembros" });

    fireEvent.change(screen.getByLabelText("Correo electrónico"), {
      target: { value: newMember.email },
    });
    fireEvent.click(screen.getByRole("button", { name: "Agregar miembro" }));

    expect(await screen.findByText(newMember.email)).toBeInTheDocument();
    expect(orgsLib.listMembers).toHaveBeenCalledOnce();
  });

  it("a successful role change updates the row without a manual refetch", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([ownerMember, editorMember]);
    const updated = { ...editorMember, role: "VIEWER" as const };
    vi.mocked(orgsLib.changeMemberRole).mockResolvedValueOnce(updated);

    renderPage({
      myRole: "OWNER",
      currentUser: { id: ownerMember.user_id, email: ownerMember.email, full_name: ownerMember.full_name },
    });
    const list = await screen.findByRole("list", { name: "Miembros" });
    await within(list).findByText(editorMember.email);
    const selects = within(list).getAllByRole("combobox");
    const editorSelect = selects[1]!;

    fireEvent.change(editorSelect, { target: { value: "VIEWER" } });

    await waitFor(() => expect(editorSelect).toHaveValue("VIEWER"));
    expect(orgsLib.listMembers).toHaveBeenCalledOnce();
  });

  it("a non-OWNER successfully leaves the organization: repoints state and redirects", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([ownerMember, editorMember]);
    vi.mocked(orgsLib.removeMember).mockResolvedValueOnce(undefined);

    const store = createStore();
    store.set(organizationsAtom, [{ ...org, my_role: "EDITOR" }]);
    store.set(activeOrgSlugAtom, org.slug);
    store.set(sessionAtom, {
      status: "authenticated",
      user: { id: editorMember.user_id, email: editorMember.email, full_name: editorMember.full_name },
    });

    render(
      <Provider store={store}>
        <MembersPage />
      </Provider>,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Salir de la organización" }));

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/dashboard"));
    expect(store.get(organizationsAtom)).toEqual([]);
    expect(store.get(activeOrgSlugAtom)).toBeNull();
  });

  it("a successful remove updates the list without a manual refetch", async () => {
    vi.mocked(orgsLib.listMembers).mockResolvedValueOnce([ownerMember, editorMember]);
    vi.mocked(orgsLib.removeMember).mockResolvedValueOnce(undefined);

    renderPage({
      myRole: "OWNER",
      currentUser: { id: ownerMember.user_id, email: ownerMember.email, full_name: ownerMember.full_name },
    });
    await screen.findByText(editorMember.email);

    fireEvent.click(screen.getByRole("button", { name: "Eliminar" }));

    await waitFor(() => expect(screen.queryByText(editorMember.email)).not.toBeInTheDocument());
    expect(orgsLib.listMembers).toHaveBeenCalledOnce();
  });
});
