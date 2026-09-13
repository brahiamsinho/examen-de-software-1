import { AlertCircle } from "lucide-react";

import { ROLE_LABELS } from "@/components/workspace/roleLabels";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import type { Member, Role } from "@/lib/organizations";

type MemberRowProps = {
  member: Member;
  isSelf: boolean;
  canManage: boolean;
  rowError: { userId: string; message: string } | null;
  onChangeRole: (userId: string, role: Exclude<Role, "OWNER">) => void;
  onRemove: (userId: string) => void;
  onLeave: (userId: string) => void;
};

/**
 * Presentational (design.md File Changes: "Role control, remove/leave,
 * inline row error"). The OWNER option is always disabled/unofferable
 * (DD7), but an OWNER's own row keeps its select enabled so the sole-owner
 * demote-self scenario (spec "Last-Owner Error Surfacing") can still be
 * attempted and rejected by the backend's 409. Remove-other is hidden for a
 * non-OWNER viewer and on the viewer's own row (DD6); self-leave always
 * renders on the viewer's own row regardless of role. `rowError` is a
 * single slot (DD5): rendered only when its `userId` matches this row.
 */
export function MemberRow({
  member,
  isSelf,
  canManage,
  rowError,
  onChangeRole,
  onRemove,
  onLeave,
}: MemberRowProps) {
  const error = rowError?.userId === member.user_id ? rowError.message : null;

  return (
    <li className="flex items-center justify-between gap-4 border-b border-border py-3 last:border-b-0">
      <div className="flex min-w-0 flex-col gap-1.5">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <span className="truncate">{member.email}</span>
          {isSelf ? <span className="text-xs text-muted-foreground">(Tú)</span> : null}
        </div>

        {canManage ? (
          <Select
            className="h-8 w-40"
            value={member.role}
            onChange={(event) =>
              onChangeRole(member.user_id, event.target.value as Exclude<Role, "OWNER">)
            }
          >
            {member.role === "OWNER" ? (
              <option value="OWNER" disabled>
                {ROLE_LABELS.OWNER}
              </option>
            ) : null}
            <option value="EDITOR">{ROLE_LABELS.EDITOR}</option>
            <option value="VIEWER">{ROLE_LABELS.VIEWER}</option>
          </Select>
        ) : (
          <span className="text-xs text-muted-foreground">{ROLE_LABELS[member.role]}</span>
        )}

        {error ? (
          <Alert variant="destructive" className="mt-1">
            <AlertCircle />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
      </div>

      <div className="flex shrink-0 items-center gap-2">
        {canManage && !isSelf ? (
          <Button
            type="button"
            variant="caution"
            size="sm"
            onClick={() => onRemove(member.user_id)}
          >
            Eliminar
          </Button>
        ) : null}
        {isSelf ? (
          <Button type="button" variant="caution" size="sm" onClick={() => onLeave(member.user_id)}>
            Salir de la organización
          </Button>
        ) : null}
      </div>
    </li>
  );
}
