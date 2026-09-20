"use client";

import { useAtomValue } from "jotai";
import { AlertTriangle } from "lucide-react";
import { use, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AddAttributeForm } from "@/components/workspace/AddAttributeForm";
import { AddClassForm } from "@/components/workspace/AddClassForm";
import { AddOperationForm } from "@/components/workspace/AddOperationForm";
import { AddRelationshipControl } from "@/components/workspace/AddRelationshipControl";
import { DiagramCanvas } from "@/components/workspace/DiagramCanvas";
import { RemoveAttributeControl } from "@/components/workspace/RemoveAttributeControl";
import { RemoveClassControl } from "@/components/workspace/RemoveClassControl";
import { RemoveOperationControl } from "@/components/workspace/RemoveOperationControl";
import { RemoveRelationshipControl } from "@/components/workspace/RemoveRelationshipControl";
import { GenerationProfilePanel } from "@/components/workspace/GenerationProfilePanel";
import { ValidationPanel } from "@/components/workspace/ValidationPanel";
import { useDocument } from "@/state/document";
import { activeOrgSlugAtom } from "@/state/organizations";

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
  const [pendingSourceId, setPendingSourceId] = useState<string | null>(null);
  const [pendingTargetId, setPendingTargetId] = useState<string | null>(null);

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
      <div className="flex items-baseline justify-between gap-4 border-b border-border px-6 py-4">
        <h1 className="font-heading text-xl font-semibold text-foreground">
          {document.metadata.name}
        </h1>
        <div className="flex gap-4 text-sm text-muted-foreground">
          <p>Clases: {document.model.classes.length}</p>
          <p>Relaciones: {document.model.relationships.length}</p>
        </div>
      </div>

      <div className="flex flex-col gap-6 p-6 lg:flex-row lg:items-start">
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <div className="h-[calc(100vh-12rem)] min-h-[36rem] w-full overflow-hidden rounded-lg border border-border bg-muted/30">
            <DiagramCanvas
              model={document.model}
              revision={document.revision}
              layout={document.layout}
              locks={locks}
              positionListenerRef={positionListenerRef}
              claimRejectedListenerRef={claimRejectedListenerRef}
              onNodeTap={handleNodeTap}
              highlightedClassId={effectiveSourceId}
              onClaim={sendClaim}
              onLivePosition={sendPosition}
              onRelease={sendRelease}
            />
          </div>

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

        <aside className="flex w-full flex-col gap-6 lg:w-96 lg:shrink-0">
          <ValidationPanel lastValidation={lastValidation} />

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

          <div className="flex flex-col gap-3">
            <h2 className="font-heading text-sm font-semibold text-foreground">Agregar</h2>

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

          <div className="flex flex-col gap-3">
            <h2 className="font-heading text-sm font-semibold text-foreground">Eliminar</h2>

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
        </aside>
      </div>
    </div>
  );
}
