import { beforeEach, describe, expect, it, vi } from "vitest";

import * as api from "@/lib/api";
import { createOrganization, listOrganizations } from "@/lib/organizations";

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
});
