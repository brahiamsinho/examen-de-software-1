"use client";

import { useState } from "react";

import { useRouter } from "next/navigation";

import { VerifyEmailBanner } from "@/components/auth/VerifyEmailBanner";
import { Button } from "@/components/ui/button";
import { CreateDocumentForm } from "@/components/workspace/CreateDocumentForm";
import { CreateOrgForm } from "@/components/workspace/CreateOrgForm";
import { DocumentList } from "@/components/workspace/DocumentList";
import { OrgEmptyState } from "@/components/workspace/OrgEmptyState";
import { createDocument } from "@/lib/uml_documents";
import { useDocuments } from "@/state/documents";
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
 *
 * `web-uml-canvas`'s "New Diagram" entry point (DD14) only renders when
 * `activeOrg` exists, and its handler — not `CreateDocumentForm` itself —
 * calls `createDocument` then `router.push(/documents/{doc.id})`.
 */
export default function DashboardPage() {
  const { organizations, activeSlug, createOrganization } = useOrganizations();
  const activeOrg = organizations.find((org) => org.slug === activeSlug) ?? null;
  // `create_document_view` requires OWNER/EDITOR (require_role); a VIEWER
  // would always get a 403 on submit, so the entry point is hidden for them
  // — same role-gating precedent as `settings/members/page.tsx`'s `canManage`
  // (post-verify WARNING: was previously shown unconditionally).
  const canCreateDocument = activeOrg?.my_role === "OWNER" || activeOrg?.my_role === "EDITOR";
  const { documents, loading } = useDocuments(activeOrg?.slug ?? null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const router = useRouter();

  async function handleCreateDocument(input: { name: string }) {
    const doc = await createDocument(activeOrg!.slug, input);
    router.push(`/documents/${doc.id}`);
    return doc;
  }

  if (organizations.length === 0) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <VerifyEmailBanner />
        <OrgEmptyState />
        <CreateOrgForm onCreate={createOrganization} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <VerifyEmailBanner />
      {activeOrg ? (
        <div className="rounded-lg border border-border p-6">
          <h1 className="text-xl font-semibold">{activeOrg.name}</h1>
          <p className="text-sm text-muted-foreground">Plan: {activeOrg.plan}</p>
        </div>
      ) : null}
      <CreateOrgForm onCreate={createOrganization} />
      {activeOrg ? (
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Mis Diagramas</h2>
            {canCreateDocument ? (
              <Button type="button" onClick={() => setShowCreateForm((prev) => !prev)}>
                Nuevo Diagrama
              </Button>
            ) : null}
          </div>
          {showCreateForm ? <CreateDocumentForm onCreate={handleCreateDocument} /> : null}
          {loading ? (
            <p className="text-sm text-muted-foreground">Cargando…</p>
          ) : (
            <DocumentList documents={documents} />
          )}
        </section>
      ) : null}
    </div>
  );
}
