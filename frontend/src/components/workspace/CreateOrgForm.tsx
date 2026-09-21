"use client";

import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api";
import type { Organization } from "@/lib/organizations";

function slugify(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-+|-+$)/g, "");
}

type CreateOrgFormProps = {
  onCreate: (input: { name: string; slug: string }) => Promise<Organization>;
};

/**
 * Presentational: receives `onCreate` from its container (the real
 * `useOrganizations().createOrganization`, DD7's optimistic append — no
 * manual refetch happens here or anywhere downstream). `slug` is required
 * by the backend (Phase 2 deviation note) and is auto-derived from `name`
 * until the user edits it manually.
 */
export function CreateOrgForm({ onCreate }: CreateOrgFormProps) {
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleNameChange(value: string) {
    setName(value);
    if (!slugTouched) {
      setSlug(slugify(value));
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onCreate({ name, slug });
      setName("");
      setSlug("");
      setSlugTouched(false);
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
        <Label htmlFor="create-org-name">Nombre de la organización</Label>
        <Input
          id="create-org-name"
          type="text"
          value={name}
          onChange={(event) => handleNameChange(event.target.value)}
          required
          autoFocus
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="create-org-slug">Identificador (slug)</Label>
        <Input
          id="create-org-slug"
          type="text"
          value={slug}
          onChange={(event) => {
            setSlugTouched(true);
            setSlug(event.target.value);
          }}
          required
        />
        <p className="text-xs text-muted-foreground">
          Se usa en las direcciones internas. Se completa solo a partir del nombre.
        </p>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}

      <Button type="submit" disabled={submitting}>
        Crear organización
      </Button>
    </form>
  );
}
