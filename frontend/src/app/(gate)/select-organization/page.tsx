"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { OrgPicker } from "@/components/workspace/OrgPicker";
import { useOrganizations, useSetActiveOrg } from "@/state/organizations";

/**
 * Container for the post-login organization picker (design.md DD4,
 * web-organization-workspace § Post-Login Organization Picker). Calling
 * `useOrganizations()` is legitimate here — this route is authenticated
 * (guarded by `(gate)/layout.tsx`) and needs the org list anyway.
 *
 * Redirects to `/dashboard` when the loaded list has fewer than 2
 * organizations, so a bookmarked or back-button visit can never become a
 * permanent dead end.
 */
export default function SelectOrganizationPage() {
  const router = useRouter();
  const { organizations } = useOrganizations();
  const setActiveOrg = useSetActiveOrg();

  useEffect(() => {
    if (organizations.length > 0 && organizations.length < 2) {
      router.replace("/dashboard");
    }
  }, [organizations, router]);

  function handleSelect(slug: string) {
    setActiveOrg(slug);
    router.replace("/dashboard");
  }

  if (organizations.length < 2) {
    return null;
  }

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-lg font-semibold">Selecciona una organización</h1>
      <OrgPicker organizations={organizations} onSelect={handleSelect} />
    </div>
  );
}
