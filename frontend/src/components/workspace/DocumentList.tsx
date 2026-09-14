import Link from "next/link";

import type { DocumentSummary } from "@/lib/uml_documents";

type DocumentListProps = { documents: DocumentSummary[] };

/**
 * Presentational (design.md DD6/DD7), no `"use client"` — like `OrgSwitcher`.
 * Each row is a real `next/link` anchor (not an `onClick` handler): a list
 * row is a real destination, unlike `CreateDocumentForm`'s post-mutation
 * redirect to an id that does not exist ahead of time. Zero documents
 * renders the empty-state copy, not `null` — an empty list is a first-run
 * state the user must see. No date column (DD7): no date-formatting helper
 * exists in this codebase.
 */
export function DocumentList({ documents }: DocumentListProps) {
  if (documents.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Todavía no tienes diagramas. Crea el primero con «Nuevo Diagrama».
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-0.5" aria-label="Diagramas">
      {documents.map((doc) => (
        <li key={doc.id}>
          <Link
            href={`/documents/${doc.id}`}
            className="flex flex-col rounded-md px-2.5 py-1.5 text-left text-sm transition-colors hover:bg-background"
          >
            <span className="font-medium text-foreground">{doc.name}</span>
            <span className="text-xs text-muted-foreground">Revisión {doc.revision}</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
