"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import type { Member } from "@/lib/organizations";

type AddMemberFormProps = {
  onAdd: (input: { email: string; role: "EDITOR" | "VIEWER" }) => Promise<Member>;
};

/**
 * Presentational: a `CreateOrgForm` clone (design.md File Changes). Role
 * selector is limited to `EDITOR`/`VIEWER` (spec "Add Member by Email" MUST
 * NOT expose `OWNER`). Receives `onAdd` from its container instead of
 * calling `state/members.ts` itself, matching `CreateOrgForm`'s
 * props-in/callback-out shape exactly, including error handling: a rejected
 * `onAdd` renders `ApiError.detail` in `role="alert"` and leaves the form
 * filled in (no clearing on failure).
 */
export function AddMemberForm({ onAdd }: AddMemberFormProps) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<"EDITOR" | "VIEWER">("EDITOR");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onAdd({ email, role });
      setEmail("");
      setRole("EDITOR");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Ocurrió un error inesperado. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <label htmlFor="add-member-email">Correo electrónico</label>
        <input
          id="add-member-email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="add-member-role">Rol</label>
        <select
          id="add-member-role"
          value={role}
          onChange={(event) => setRole(event.target.value as "EDITOR" | "VIEWER")}
        >
          <option value="EDITOR">Editor</option>
          <option value="VIEWER">Lector</option>
        </select>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Button type="submit" disabled={submitting}>
        Agregar miembro
      </Button>
    </form>
  );
}
