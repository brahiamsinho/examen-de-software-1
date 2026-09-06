import { apiFetch } from "@/lib/api";

/**
 * Domain client for `apps/organizations` (design.md's `lib/organizations.ts`
 * — one module per backend Django app). No cookie/CSRF knowledge here;
 * everything goes through `apiFetch`.
 */

export type Role = "OWNER" | "EDITOR" | "VIEWER";

export type Organization = {
  id: string;
  name: string;
  slug: string;
  plan: string;
  my_role: Role | null;
};

export async function listOrganizations(): Promise<Organization[]> {
  return apiFetch<Organization[]>("/api/orgs");
}

export async function createOrganization(input: {
  name: string;
  slug: string;
}): Promise<Organization> {
  return apiFetch<Organization>("/api/orgs", { method: "POST", json: input });
}
