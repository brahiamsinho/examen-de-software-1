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

export type Member = {
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  created_at: string;
};

/**
 * Thin `apiFetch` wrappers (design.md DD1): no `try/catch` here so `ApiError`
 * (including the 409 `LastOwnerError`) reaches the caller verbatim, exactly
 * like `createOrganization`. `removeMember` resolves to `undefined` because
 * `apiFetch` returns `undefined` for a 204 response.
 */
export async function listMembers(orgSlug: string): Promise<Member[]> {
  return apiFetch<Member[]>(`/api/orgs/${encodeURIComponent(orgSlug)}/members`);
}

export async function addMember(
  orgSlug: string,
  input: { email: string; role: "EDITOR" | "VIEWER" },
): Promise<Member> {
  return apiFetch<Member>(`/api/orgs/${encodeURIComponent(orgSlug)}/members`, {
    method: "POST",
    json: input,
  });
}

export async function changeMemberRole(
  orgSlug: string,
  userId: string,
  role: Exclude<Role, "OWNER">,
): Promise<Member> {
  return apiFetch<Member>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/members/${encodeURIComponent(userId)}`,
    { method: "PATCH", json: { role } },
  );
}

export async function removeMember(orgSlug: string, userId: string): Promise<void> {
  return apiFetch<void>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/members/${encodeURIComponent(userId)}`,
    { method: "DELETE" },
  );
}
