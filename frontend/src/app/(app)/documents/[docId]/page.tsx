"use client";

import { useAtomValue } from "jotai";
import { AlertTriangle, FileUp, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsPanel, TabsTab } from "@/components/ui/tabs";
import { AddAttributeForm } from "@/components/workspace/AddAttributeForm";
import { AddClassForm } from "@/components/workspace/AddClassForm";
import { AddOperationForm } from "@/components/workspace/AddOperationForm";
import { AddRelationshipControl } from "@/components/workspace/AddRelationshipControl";
import { DiagramCanvas } from "@/components/workspace/DiagramCanvas";
import { DeploymentActions, DeploymentNotices, DeploymentUrl } from "@/components/workspace/DeploymentControls";
import { EditRelationshipDialog } from "@/components/workspace/EditRelationshipDialog";
import { DeleteDiagramDialog } from "@/components/workspace/DeleteDiagramDialog";
import { DownloadBackendButton } from "@/components/workspace/DownloadBackendButton";
import { ImportXmiControl } from "@/components/workspace/ImportXmiControl";
import { RemoveAttributeControl } from "@/components/workspace/RemoveAttributeControl";
import { RemoveClassControl } from "@/components/workspace/RemoveClassControl";
import { RemoveOperationControl } from "@/components/workspace/RemoveOperationControl";
import { RemoveRelationshipControl } from "@/components/workspace/RemoveRelationshipControl";
import { GenerationProfilePanel } from "@/components/workspace/GenerationProfilePanel";
import { ValidationPanel } from "@/components/workspace/ValidationPanel";
import { ImportWarningsAlert } from "@/components/workspace/ImportWarningsAlert";
import { downloadGeneratedBackend } from "@/lib/generation_export";
import { getJoinTables, type JoinTableHint } from "@/lib/join_tables";
import { exportXmi, importXmiIntoDocument, takeImportWarnings } from "@/lib/xmi_interop";
import { useBackendDeployment } from "@/state/backend_deployment";
import { useDocument } from "@/state/document";
import { useDocumentActions } from "@/state/documents";
import { activeOrgSlugAtom, organizationsAtom } from "@/state/organizations";

/**
 * Container (design.md DD11): stays `"use client"` and unwraps the Next 16
 * `params: Promise<{docId: string}>` with React's `use()` — verified
 * against `node_modules/next/dist/docs/.../page.md`. Reads
 * `activeOrgSlugAtom` via `useAtomValue`, wires `useDocument`,
 * `DiagramCanvas`, the 3 add-forms, `ValidationPanel`, and the click-click
 * state machine (DD8/DD9): `pendingSourceId`/`pendingTargetId` live here,
 * not in `DiagramCanvas`, so `AddRelationshipControl` can render the
 * "source selected, pick a target" affordance from the same state the
 * canvas highlights.
 */
export default function DocumentPage({ params }: { params: Promise<{ docId: string }> }) {
  const { docId } = use(params);
  const orgSlug = useAtomValue(activeOrgSlugAtom);
  const {
    document,
    applyDocument,
    error,
    lastValidation,
    isSubmitting,
    submitCommand,
    locks = {},
    positionListenerRef,
    claimRejectedListenerRef,
    sendClaim,
    sendPosition,
    sendRelease,
  } = useDocument(orgSlug, docId);
  const deployment = useBackendDeployment(orgSlug, docId);
  const router = useRouter();
  const { deleteDiagram } = useDocumentActions(orgSlug);
  // The role only gates what is SHOWN: the backend re-checks it (403) on every write.
  const organizations = useAtomValue(organizationsAtom);
  const myRole = organizations.find((org) => org.slug === orgSlug)?.my_role ?? null;
  const canEdit = myRole === "OWNER" || myRole === "EDITOR";
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [editingRelationshipId, setEditingRelationshipId] = useState<string | null>(null);
  const [pendingSourceId, setPendingSourceId] = useState<string | null>(null);
  const [pendingTargetId, setPendingTargetId] = useState<string | null>(null);
  // Read after mount (sessionStorage does not exist during SSR); consumed once.
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  useEffect(() => {
    setImportWarnings(takeImportWarnings(docId));
  }, [docId]);

  // A both-ends-many association's implied join table (design.md DD177) —
  // fetched separately from the document/websocket state and re-fetched on
  // every revision change, so it never falls behind an edit. A failure here
  // (network hiccup, an in-progress edit the backend can't map yet) just
  // means no hint is drawn; it must never break the diagram itself.
  const [joinTableHints, setJoinTableHints] = useState<JoinTableHint[]>([]);
  useEffect(() => {
    if (orgSlug === null || document === null) return;
    let cancelled = false;
    getJoinTables(orgSlug, docId)
      .then((hints) => {
        if (!cancelled) setJoinTableHints(hints);
      })
      .catch(() => {
        if (!cancelled) setJoinTableHints([]);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgSlug, docId, document?.revision]);

  if (orgSlug === null) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <h1 className="font-heading text-xl font-semibold text-foreground">Diagrama</h1>
        <p className="text-sm text-muted-foreground">No hay una organización activa.</p>
      </div>
    );
  }

  if (error !== null) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <h1 className="font-heading text-xl font-semibold text-foreground">Diagrama</h1>
        <p className="text-sm text-muted-foreground">
          {error.notFound ? "Documento no encontrado." : "Ocurrió un error al cargar el documento."}
        </p>
      </div>
    );
  }

  if (document === null) {
    return null;
  }

  // Same emptiness rule the backend enforces on `POST .../import-xmi` (409 otherwise).
  const isBlank = document.model.classes.length === 0 && document.model.relationships.length === 0;

  async function handleImportIntoDocument(file: File) {
    const result = await importXmiIntoDocument(orgSlug!, docId, file);
    const { warnings, ...imported } = result;
    applyDocument(imported);
    setImportWarnings(warnings);
  }

  async function handleDelete() {
    await deleteDiagram(docId);
    router.replace("/dashboard");
  }

  const classIds = new Set(document.model.classes.map((c) => c.id));
  const danglingRelationshipCount = document.model.relationships.filter(
    (r) => !classIds.has(r.source.class_id) || !classIds.has(r.target.class_id),
  ).length;

  // "{owner} está moviendo {class}" affordance (design.md DD12) — one line
  // per lock held by ANOTHER connection; a lock this client itself holds
  // (`mine: true`) needs no affordance, since that user already sees the
  // node moving under their own cursor.
  const classNameById = new Map(document.model.classes.map((c) => [c.id, c.name]));
  const foreignLocks = Object.entries(locks).filter(([, lock]) => !lock.mine);

  // Derived, not stored (same DD2 philosophy as the Remove* controls): if
  // the class pinned by the click-click flow was removed via
  // RemoveClassControl, it collapses to null in this same render pass
  // instead of the flow rendering a dead id after refetch (post-verify
  // WARNING 2 on uml-canvas-remove-ui).
  const effectiveSourceId = pendingSourceId !== null && classIds.has(pendingSourceId) ? pendingSourceId : null;
  const effectiveTargetId = pendingTargetId !== null && classIds.has(pendingTargetId) ? pendingTargetId : null;

  function handleNodeTap(classId: string) {
    if (effectiveSourceId === null) {
      setPendingSourceId(classId);
    } else if (classId === effectiveSourceId) {
      // Cancel gesture: must also clear pendingTargetId, otherwise a later
      // fresh source tap immediately pairs with this stale target without a
      // second explicit tap (post-verify CRITICAL 1 on uml-canvas-ui).
      setPendingSourceId(null);
      setPendingTargetId(null);
    } else {
      setPendingTargetId(classId);
    }
  }

  function handleCancelRelationship() {
    setPendingSourceId(null);
    setPendingTargetId(null);
  }

  function handleSelfRelationship() {
    // Explicit affordance for a recursive/reflexive relationship (a class
    // related to itself): tapping the same node twice is handleNodeTap's
    // cancel gesture, so this bypasses the canvas entirely and sets the
    // target directly from the already-pending source.
    if (effectiveSourceId !== null) {
      setPendingTargetId(effectiveSourceId);
    }
  }

  return (
    <div className="flex flex-col">
      <header className="flex flex-col gap-3 border-b border-border px-4 py-4 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
          <div className="flex min-w-0 flex-col gap-1">
            <h1 className="font-heading truncate text-xl font-semibold text-foreground">
              {document.metadata.name}
            </h1>
            <div className="flex gap-4 text-sm text-muted-foreground">
              <p>Clases: {document.model.classes.length}</p>
              <p>Relaciones: {document.model.relationships.length}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <DeploymentActions
              deployment={deployment.deployment}
              busy={deployment.busy || deployment.loading}
              actionError={deployment.actionError}
              onStart={deployment.start}
              onStop={deployment.stop}
            />
            <span className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden />
            <DownloadBackendButton
              size="lg"
              className="relative"
              errorClassName="absolute top-full right-0 z-20 mt-2 w-72 shadow-md"
              label="Descargar backend (.zip)"
              onDownload={() => downloadGeneratedBackend(orgSlug, docId)}
            />
            <DownloadBackendButton
              size="lg"
              className="relative"
              errorClassName="absolute top-full right-0 z-20 mt-2 w-72 shadow-md"
              onDownload={() => exportXmi(orgSlug, docId)}
              label="Exportar XML"
              pendingLabel="Exportando..."
            />
            {canEdit ? (
              <Button type="button" variant="outline" size="lg" onClick={() => setDeleteOpen(true)}>
                <Trash2 />
                Eliminar diagrama
              </Button>
            ) : null}
          </div>
        </div>
        <DeploymentUrl deployment={deployment.deployment} />
        <DeploymentNotices deployment={deployment.deployment} actionError={deployment.actionError} />
      </header>

      <div className="flex flex-col gap-6 p-6 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <div className="relative h-[calc(100vh-12rem)] min-h-[36rem] w-full overflow-hidden rounded-lg border border-border bg-muted/30">
            <DiagramCanvas
              model={document.model}
              revision={document.revision}
              layout={document.layout}
              locks={locks}
              positionListenerRef={positionListenerRef}
              claimRejectedListenerRef={claimRejectedListenerRef}
              onNodeTap={handleNodeTap}
              onEdgeEdit={canEdit ? setEditingRelationshipId : undefined}
              joinTableHints={joinTableHints}
              highlightedClassId={effectiveSourceId}
              onClaim={sendClaim}
              onLivePosition={sendPosition}
              onRelease={sendRelease}
            />
            {isBlank && canEdit ? (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center p-6">
                <div className="pointer-events-auto flex max-w-sm flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-card/95 px-6 py-6 text-center shadow-xs">
                  <span className="flex size-10 items-center justify-center rounded-full bg-accent text-accent-foreground">
                    <FileUp className="size-5" aria-hidden="true" />
                  </span>
                  <h2 className="font-heading text-base font-semibold">Este diagrama está vacío</h2>
                  <p className="text-sm text-muted-foreground">
                    Agrega clases desde el panel derecho o carga un modelo desde un archivo XML.
                  </p>
                  <ImportXmiControl onImport={handleImportIntoDocument} disabled={isSubmitting} />
                </div>
              </div>
            ) : null}
          </div>

          {canEdit && document.model.relationships.length > 0 ? (
            <p className="text-xs text-muted-foreground">Doble clic en una relación para editarla</p>
          ) : null}

          {foreignLocks.length > 0 ? (
            <div className="flex flex-col gap-1 text-sm text-muted-foreground">
              {foreignLocks.map(([classId, lock]) => (
                <p key={classId}>
                  {lock.ownerLabel} está moviendo {classNameById.get(classId) ?? classId}
                </p>
              ))}
            </div>
          ) : null}

          {danglingRelationshipCount > 0 ? (
            <Alert variant="caution">
              <AlertTriangle />
              <AlertDescription>
                {danglingRelationshipCount} relación(es) no se muestran por referirse a una clase
                inexistente.
              </AlertDescription>
            </Alert>
          ) : null}
        </div>

        <aside className="flex w-full flex-col gap-4 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:w-96 lg:shrink-0 lg:overflow-y-auto lg:pr-1">
          <ImportWarningsAlert warnings={importWarnings} onDismiss={() => setImportWarnings([])} />

          <ValidationPanel lastValidation={lastValidation} />

          <Tabs defaultValue="agregar">
            <TabsList>
              <TabsTab value="agregar">Agregar</TabsTab>
              <TabsTab value="eliminar">Eliminar</TabsTab>
              <TabsTab value="generacion">Generación</TabsTab>
            </TabsList>

            <TabsPanel value="agregar">
              <div className="flex flex-col gap-3">
                <h2 className="sr-only">Agregar</h2>

                <Card>
                  <CardHeader>
                    <CardTitle>Clase</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <AddClassForm onSubmit={submitCommand} disabled={isSubmitting} />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Atributo</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <AddAttributeForm
                      classes={document.model.classes}
                      onSubmit={submitCommand}
                      disabled={isSubmitting}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Operación</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <AddOperationForm
                      classes={document.model.classes}
                      onSubmit={submitCommand}
                      disabled={isSubmitting}
                    />
                  </CardContent>
                </Card>

                <AddRelationshipControl
                  pendingSourceId={effectiveSourceId}
                  pendingTargetId={effectiveTargetId}
                  classes={document.model.classes}
                  onSubmit={submitCommand}
                  onCancel={handleCancelRelationship}
                  onSelectSelf={handleSelfRelationship}
                  disabled={isSubmitting}
                />
              </div>
            </TabsPanel>

            <TabsPanel value="eliminar">
              <div className="flex flex-col gap-3">
                <h2 className="sr-only">Eliminar</h2>

                <Card>
                  <CardHeader>
                    <CardTitle>Clase</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <RemoveClassControl
                      classes={document.model.classes}
                      relationships={document.model.relationships}
                      onSubmit={submitCommand}
                      disabled={isSubmitting}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Atributo</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <RemoveAttributeControl
                      classes={document.model.classes}
                      onSubmit={submitCommand}
                      disabled={isSubmitting}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Operación</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <RemoveOperationControl
                      classes={document.model.classes}
                      onSubmit={submitCommand}
                      disabled={isSubmitting}
                    />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Relación</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <RemoveRelationshipControl
                      classes={document.model.classes}
                      relationships={document.model.relationships}
                      onSubmit={submitCommand}
                      disabled={isSubmitting}
                    />
                  </CardContent>
                </Card>
              </div>

            </TabsPanel>

            <TabsPanel value="generacion">
              <Card>
                <CardHeader>
                  <CardTitle>Perfil de generación</CardTitle>
                </CardHeader>
                <CardContent>
                  <GenerationProfilePanel
                    classes={document.model.classes}
                    generationMetadata={document.model.generation_metadata}
                    onSubmit={submitCommand}
                    disabled={isSubmitting}
                  />
                </CardContent>
              </Card>
            </TabsPanel>
          </Tabs>
        </aside>
      </div>

      <EditRelationshipDialog
        relationship={
          editingRelationshipId === null
            ? null
            : (document.model.relationships.find((r) => r.id === editingRelationshipId) ?? null)
        }
        classes={document.model.classes}
        onSubmit={submitCommand}
        onClose={() => setEditingRelationshipId(null)}
      />
      <DeleteDiagramDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        diagramName={document.metadata.name}
        onConfirm={handleDelete}
      />
    </div>
  );
}
