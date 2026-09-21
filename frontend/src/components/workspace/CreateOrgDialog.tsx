"use client";

import { CreateOrgForm } from "@/components/workspace/CreateOrgForm";
import { Dialog } from "@/components/ui/dialog";
import type { Organization } from "@/lib/organizations";

type CreateOrgDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (input: { name: string; slug: string }) => Promise<Organization>;
};

/**
 * Organization administration lives behind the sidebar's org switcher (and
 * the zero-organization empty state), never inline on the dashboard. Closes
 * only after `onCreate` resolves so a rejected slug keeps its error visible.
 */
export function CreateOrgDialog({ open, onOpenChange, onCreate }: CreateOrgDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Crear organización"
      description="Una organización agrupa a tu equipo y sus diagramas."
    >
      <CreateOrgForm
        onCreate={async (input) => {
          const org = await onCreate(input);
          onOpenChange(false);
          return org;
        }}
      />
    </Dialog>
  );
}
