"use client";

import { AlertCircle } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
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
    <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="add-member-email">Correo electrónico</Label>
        <Input
          id="add-member-email"
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          required
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="add-member-role">Rol</Label>
        <Select
          id="add-member-role"
          value={role}
          onChange={(event) => setRole(event.target.value as "EDITOR" | "VIEWER")}
        >
          <option value="EDITOR">Editor</option>
          <option value="VIEWER">Lector</option>
        </Select>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}

      <Button type="submit" size="sm" className="self-start" disabled={submitting}>
        Agregar miembro
      </Button>
    </form>
  );
}
