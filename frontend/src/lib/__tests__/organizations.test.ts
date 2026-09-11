import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import {
  addMember,
  changeMemberRole,
  createOrganization,
  listMembers,
  listOrganizations,
  removeMember,
} from "@/lib/organizations";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    apiFetch: vi.fn(),
  };
});

const organization = {
  id: "22222222-2222-2222-2222-222222222222",
  name: "Acme",
  slug: "acme",
  plan: "STARTER",
  my_role: "OWNER",
};

const member = {
  user_id: "33333333-3333-3333-3333-333333333333",
  email: "collaborator@example.com",
  full_name: "Collaborator One",
  role: "EDITOR",
  created_at: "2026-01-01T00:00:00Z",
};

describe("lib/organizations", () => {
  beforeEach(() => {
    vi.mocked(api.apiFetch).mockReset();
  });

  it("listOrganizations gets /api/orgs and returns the list", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce([organization]);

    const result = await listOrganizations();

    expect(api.apiFetch).toHaveBeenCalledWith("/api/orgs");
    expect(result).toEqual([organization]);
  });

  it("createOrganization posts to /api/orgs and returns the created org with my_role OWNER", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(organization);

    const result = await createOrganization({ name: "Acme", slug: "acme" });

    expect(api.apiFetch).toHaveBeenCalledWith(
      "/api/orgs",
      expect.objectContaining({
        method: "POST",
        json: { name: "Acme", slug: "acme" },
      }),
    );
    expect(result).toEqual(organization);
    expect(result.my_role).toBe("OWNER");
  });

  it("listMembers gets /api/orgs/{slug}/members and returns the list", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce([member]);

    const result = await listMembers("acme");

    expect(api.apiFetch).toHaveBeenCalledWith("/api/orgs/acme/members");
    expect(result).toEqual([member]);
  });

  it("addMember posts email and role to /api/orgs/{slug}/members and returns the created member", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(member);

    const result = await addMember("acme", { email: "collaborator@example.com", role: "EDITOR" });

    expect(api.apiFetch).toHaveBeenCalledWith(
      "/api/orgs/acme/members",
      expect.objectContaining({
        method: "POST",
        json: { email: "collaborator@example.com", role: "EDITOR" },
      }),
    );
    expect(result).toEqual(member);
  });

  it("changeMemberRole patches /api/orgs/{slug}/members/{userId} and returns the updated member", async () => {
    const updated = { ...member, role: "VIEWER" };
    vi.mocked(api.apiFetch).mockResolvedValueOnce(updated);

    const result = await changeMemberRole("acme", member.user_id, "VIEWER");

    expect(api.apiFetch).toHaveBeenCalledWith(
      `/api/orgs/acme/members/${member.user_id}`,
      expect.objectContaining({ method: "PATCH", json: { role: "VIEWER" } }),
    );
    expect(result).toEqual(updated);
  });

  it("removeMember deletes /api/orgs/{slug}/members/{userId} and resolves to undefined on 204", async () => {
    vi.mocked(api.apiFetch).mockResolvedValueOnce(undefined);

    const result = await removeMember("acme", member.user_id);

    expect(api.apiFetch).toHaveBeenCalledWith(
      `/api/orgs/acme/members/${member.user_id}`,
      expect.objectContaining({ method: "DELETE" }),
    );
    expect(result).toBeUndefined();
  });
});
