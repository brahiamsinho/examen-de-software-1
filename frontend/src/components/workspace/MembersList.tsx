import { MemberRow } from "@/components/workspace/MemberRow";
import type { Member, Role } from "@/lib/organizations";

type MembersListProps = {
  members: Member[];
  currentUserId: string;
  canManage: boolean;
  rowError: { userId: string; message: string } | null;
  onChangeRole: (userId: string, role: Exclude<Role, "OWNER">) => void;
  onRemove: (userId: string) => void;
  onLeave: (userId: string) => void;
};

/**
 * Presentational (design.md File Changes: "`<ul aria-label="Miembros">`,
 * props-in/callback-out"). Spec `web-member-management` § Members List
 * Visibility: composes `MemberRow` per member, deriving `isSelf` from
 * `currentUserId` so every row's self marker and self-leave control stay
 * correct without the row itself knowing about the viewer.
 */
export function MembersList({
  members,
  currentUserId,
  canManage,
  rowError,
  onChangeRole,
  onRemove,
  onLeave,
}: MembersListProps) {
  return (
    <ul aria-label="Miembros" className="flex flex-col gap-2">
      {members.map((member) => (
        <MemberRow
          key={member.user_id}
          member={member}
          isSelf={member.user_id === currentUserId}
          canManage={canManage}
          rowError={rowError}
          onChangeRole={onChangeRole}
          onRemove={onRemove}
          onLeave={onLeave}
        />
      ))}
    </ul>
  );
}
