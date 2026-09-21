"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import type { UmlDocument } from "@/lib/uml_documents";

type CreateDocumentFormProps = {
  onCreate: (input: { name: string }) => Promise<UmlDocument>;
};

/**
 * Mirrors `CreateOrgForm` (DD14): props-in/callback-out, no `useRouter`
 * here — the container's handler does `createDocument` then
 * `router.push(...)`, keeping this form render-testable without a router
 * mock.
 */
export function CreateDocumentForm({ onCreate }: CreateDocumentFormProps) {
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onCreate({ name });
      setName("");
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
      <div className="flex flex-col gap-1.5">
        <Label htmlFor="create-document-name">Nombre del diagrama</Label>
        <Input
          id="create-document-name"
          type="text"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
          autoFocus
        />
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Button type="submit" disabled={submitting}>
        Crear diagrama
      </Button>
    </form>
  );
}
