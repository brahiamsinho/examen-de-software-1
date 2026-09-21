"use client";

import { CreateDocumentForm } from "@/components/workspace/CreateDocumentForm";
import { Dialog } from "@/components/ui/dialog";
import type { UmlDocument } from "@/lib/uml_documents";

type NewDocumentDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (input: { name: string }) => Promise<UmlDocument>;
};

/**
 * Shared by the sidebar "+" and the dashboard's "Nuevo diagrama": the form
 * lives in a modal so neither surface carries an inline form. The dialog
 * closes only after `onCreate` resolves, so a failed request keeps the form
 * (and its error message) on screen.
 */
export function NewDocumentDialog({ open, onOpenChange, onCreate }: NewDocumentDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Nuevo diagrama"
      description="Elige un nombre; después podrás agregar clases y relaciones."
    >
      <CreateDocumentForm
        onCreate={async (input) => {
          const doc = await onCreate(input);
          onOpenChange(false);
          return doc;
        }}
      />
    </Dialog>
  );
}
