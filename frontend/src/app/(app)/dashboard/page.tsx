"use client";

import { CreateOrgForm } from "@/components/workspace/CreateOrgForm";
import { OrgEmptyState } from "@/components/workspace/OrgEmptyState";
import { useOrganizations } from "@/state/organizations";

/**
 * Container: owns its own `useOrganizations()` call — it is a sibling of
 * `AppTopbar` under `(app)/layout.tsx`, so it cannot receive org state as a
 * prop from it (see AppTopbar's docblock and Deviations for the resulting
 * duplicate-`listOrganizations()`-fetch tradeoff, accepted as low-risk: an
 * idempotent GET, converging on the same shared `organizationsAtom`).
 *
 * Empty state renders `OrgEmptyState` + `CreateOrgForm` side by side (spec
 * `web-organization-workspace` § Zero-Organization Empty State — reachable,
 * non-blocking, no onboarding redirect).
 */
export default function DashboardPage() {
  const { organizations, activeSlug, createOrganization } = useOrganizations();
  const activeOrg = organizations.find((org) => org.slug === activeSlug) ?? null;

  if (organizations.length === 0) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <OrgEmptyState />
        <CreateOrgForm onCreate={createOrganization} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {activeOrg ? (
        <div className="rounded-lg border border-border p-6">
          <h1 className="text-xl font-semibold">{activeOrg.name}</h1>
          <p className="text-sm text-muted-foreground">Plan: {activeOrg.plan}</p>
        </div>
      ) : null}
      <CreateOrgForm onCreate={createOrganization} />
    </div>
  );
}
