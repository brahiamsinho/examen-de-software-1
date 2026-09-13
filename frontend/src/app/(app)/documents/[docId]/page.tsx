"use client";

import { useAtomValue } from "jotai";
import { use, useState } from "react";

import { AddAttributeForm } from "@/components/workspace/AddAttributeForm";
import { AddClassForm } from "@/components/workspace/AddClassForm";
import { AddRelationshipControl } from "@/components/workspace/AddRelationshipControl";
import { DiagramCanvas } from "@/components/workspace/DiagramCanvas";
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
  const { document, error, lastValidation, submitCommand } = useDocument(orgSlug, docId);
  const [pendingSourceId, setPendingSourceId] = useState<string | null>(null);
  const [pendingTargetId, setPendingTargetId] = useState<string | null>(null);

  function handleNodeTap(classId: string) {
    if (pendingSourceId === null) {
      setPendingSourceId(classId);
    } else if (classId === pendingSourceId) {
      // Cancel gesture: must also clear pendingTargetId, otherwise a later
      // fresh source tap immediately pairs with this stale target without a
      // second explicit tap (post-verify CRITICAL 1).
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

  if (orgSlug === null) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <h1 className="text-xl font-semibold">Diagrama</h1>
        <p className="text-sm text-muted-foreground">No hay una organización activa.</p>
      </div>
    );
  }

  if (error !== null) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <h1 className="text-xl font-semibold">Diagrama</h1>
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

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">{document.metadata.name}</h1>
      <div className="flex gap-4 text-sm text-muted-foreground">
        <p>Clases: {document.model.classes.length}</p>
        <p>Relaciones: {document.model.relationships.length}</p>
      </div>

      <div className="h-96 w-full border border-border">
        <DiagramCanvas
          model={document.model}
          revision={document.revision}
          onNodeTap={handleNodeTap}
          highlightedClassId={pendingSourceId}
        />
      </div>

      {danglingRelationshipCount > 0 ? (
        <p className="text-sm text-muted-foreground">
          {danglingRelationshipCount} relación(es) no se muestran por referirse a una clase
          inexistente.
        </p>
      ) : null}

      <ValidationPanel lastValidation={lastValidation} />

      <AddClassForm onSubmit={submitCommand} />
      <AddAttributeForm classes={document.model.classes} onSubmit={submitCommand} />
      <AddRelationshipControl
        pendingSourceId={pendingSourceId}
        pendingTargetId={pendingTargetId}
        classes={document.model.classes}
        onSubmit={submitCommand}
        onCancel={handleCancelRelationship}
      />
    </div>
  );
}
