"use client";

import { useState } from "react";

import { Plus } from "lucide-react";

import { VerifyEmailBanner } from "@/components/auth/VerifyEmailBanner";
import { Button } from "@/components/ui/button";
import { CreateOrgDialog } from "@/components/workspace/CreateOrgDialog";
import { DocumentGrid } from "@/components/workspace/DocumentGrid";
import { ImportXmiControl } from "@/components/workspace/ImportXmiControl";
import { NewDocumentDialog } from "@/components/workspace/NewDocumentDialog";
import { OrgEmptyState } from "@/components/workspace/OrgEmptyState";
import { ROLE_LABELS } from "@/components/workspace/roleLabels";
import { useDocumentActions, useDocuments } from "@/state/documents";
import { useOrganizations } from "@/state/organizations";

/**
 * Container for the diagrams overview. The page shows diagrams and their
 * actions only: organization administration (switching, creating) lives in
 * the sidebar's `OrgSwitcher`. The one exception is the zero-organization
 * empty state, where creating an organization *is* the only useful action —
 * it opens the same dialog instead of an inline form.
 *
 * Owns its own `useOrganizations()`/`useDocuments()` instances (a sibling of
 * `AppSidebar` under `(app)/layout.tsx`; the duplicate GETs are idempotent and
 * converge on the shared org atom / document invalidation counter).
 *
 * `create_document_view` requires OWNER/EDITOR (require_role); a VIEWER would
 * always get a 403, so both actions are hidden for them (same role-gating
 * precedent as `settings/members/page.tsx`'s `canManage`).
 */
export default function DashboardPage() {
  const { organizations, activeSlug, createOrganization } = useOrganizations();
  const activeOrg = organizations.find((org) => org.slug === activeSlug) ?? null;
  const canCreateDocument = activeOrg?.my_role === "OWNER" || activeOrg?.my_role === "EDITOR";
  const { documents, loading } = useDocuments(activeOrg?.slug ?? null);
  const { createDiagram, importDiagram } = useDocumentActions(activeOrg?.slug ?? null);
  const [newDiagramOpen, setNewDiagramOpen] = useState(false);
  const [createOrgOpen, setCreateOrgOpen] = useState(false);

  if (organizations.length === 0) {
    return (
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 p-4 sm:p-8">
        <VerifyEmailBanner />
        <OrgEmptyState>
          <Button type="button" onClick={() => setCreateOrgOpen(true)}>
            <Plus />
            Crear organización
          </Button>
        </OrgEmptyState>
        <CreateOrgDialog
          open={createOrgOpen}
          onOpenChange={setCreateOrgOpen}
          onCreate={createOrganization}
        />
      </div>
    );
  }

  const actions = canCreateDocument ? (
    <>
      <ImportXmiControl onImport={importDiagram} />
      <Button type="button" onClick={() => setNewDiagramOpen(true)}>
        <Plus />
        Nuevo diagrama
      </Button>
    </>
  ) : null;
  // Actions render in exactly one place, and only once the list has loaded, so
  // they never jump between the header and the empty state.
  const showHeaderActions = !loading && documents.length > 0;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-4 sm:p-8">
      <VerifyEmailBanner />
      {activeOrg ? (
        <>
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex min-w-0 flex-col gap-1.5">
              <h1 className="font-heading text-2xl font-semibold tracking-tight break-words">
                {activeOrg.name}
              </h1>
              <p className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <span className="rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-accent-foreground">
                  Plan {activeOrg.plan.toUpperCase()}
                </span>
                <span>{ROLE_LABELS[activeOrg.my_role ?? ""] ?? activeOrg.my_role}</span>
              </p>
            </div>
            {showHeaderActions && actions ? (
              <div className="flex flex-wrap items-start gap-2">{actions}</div>
            ) : null}
          </header>

          {loading ? (
            <div role="status" aria-label="Cargando diagramas" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2].map((key) => (
                <div key={key} className="h-32 animate-pulse rounded-xl border border-border bg-muted" />
              ))}
            </div>
          ) : (
            <DocumentGrid documents={documents} emptyActions={actions} />
          )}

          <NewDocumentDialog
            open={newDiagramOpen}
            onOpenChange={setNewDiagramOpen}
            onCreate={createDiagram}
          />
        </>
      ) : null}
    </div>
  );
}
