"use client";

import { useAtomValue } from "jotai";
import { useState } from "react";

import { AddMemberForm } from "@/components/workspace/AddMemberForm";
import { MembersList } from "@/components/workspace/MembersList";
import { ApiError } from "@/lib/api";
import type { Role } from "@/lib/organizations";
import { useMembers } from "@/state/members";
import { activeOrgSlugAtom, organizationsAtom, useLeaveOrganization } from "@/state/organizations";
import { sessionAtom } from "@/state/session";

type RowError = { userId: string; message: string };

function toRowMessage(err: unknown): string {
  return err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.";
}

/**
 * Container (design.md DD4/DD5/DD6): reads `organizationsAtom` /
 * `activeOrgSlugAtom` / `sessionAtom` directly via `useAtomValue` instead of
 * `useOrganizations()`/`useSession()` — those hooks already fetch once each
 * in `AppTopbar`/`SessionGuard`, and a third mount here would add a third
 * `listOrganizations()` GET. `canManage` derives from the already-loaded
 * `Organization.my_role` (`OrgSwitcher`'s established source, DD6) — hiding
 * controls is presentation only, the backend's `require_role` stays the
 * enforcement point. `rowError` is a single slot (DD5): one mutation per
 * click, so concurrent per-row errors are unreachable; each attempt clears
 * it first. Self-leave routes through `useLeaveOrganization` (its own 409
 * — e.g. removing the sole owner — surfaces inline here exactly like
 * `changeMemberRole`/`removeMember`).
 */
export default function MembersPage() {
  const organizations = useAtomValue(organizationsAtom);
  const activeSlug = useAtomValue(activeOrgSlugAtom);
  const session = useAtomValue(sessionAtom);
  const activeOrg = organizations.find((org) => org.slug === activeSlug) ?? null;
  const canManage = activeOrg?.my_role === "OWNER";
  const currentUserId = session.status === "authenticated" ? session.user.id : "";

  const { members, addMember, changeMemberRole, removeMember } = useMembers(activeSlug);
  const leaveOrganization = useLeaveOrganization();
  const [rowError, setRowError] = useState<RowError | null>(null);

  async function handleChangeRole(userId: string, role: Exclude<Role, "OWNER">) {
    setRowError(null);
    try {
      await changeMemberRole(userId, role);
    } catch (err) {
      setRowError({ userId, message: toRowMessage(err) });
    }
  }

  async function handleRemove(userId: string) {
    setRowError(null);
    try {
      await removeMember(userId);
    } catch (err) {
      setRowError({ userId, message: toRowMessage(err) });
    }
  }

  async function handleLeave(userId: string) {
    if (activeSlug === null) return;
    setRowError(null);
    try {
      await leaveOrganization(activeSlug, userId);
    } catch (err) {
      setRowError({ userId, message: toRowMessage(err) });
    }
  }

  if (activeSlug === null) {
    return (
      <div className="flex flex-col gap-6 p-6">
        <h1 className="text-xl font-semibold">Miembros</h1>
        <p className="text-sm text-muted-foreground">No hay una organización activa.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <h1 className="text-xl font-semibold">Miembros</h1>

      {!canManage ? (
        <p className="text-sm text-muted-foreground">
          Solo un propietario puede administrar los miembros.
        </p>
      ) : null}

      <MembersList
        members={members}
        currentUserId={currentUserId}
        canManage={canManage}
        rowError={rowError}
        onChangeRole={handleChangeRole}
        onRemove={handleRemove}
        onLeave={handleLeave}
      />

      {canManage ? <AddMemberForm onAdd={addMember} /> : null}
    </div>
  );
}
