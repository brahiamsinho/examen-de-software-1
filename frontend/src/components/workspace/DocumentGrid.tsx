import { FileText, Trash2 } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { documentTitle, formatUpdatedAt } from "@/components/workspace/documentDisplay";
import type { DocumentSummary } from "@/lib/uml_documents";
import { cn } from "@/lib/utils";

type DocumentGridProps = {
  documents: DocumentSummary[];
  /** Actions shown inside the empty state (the header hides them then). */
  emptyActions?: ReactNode;
  /** Omit to hide the per-card delete button (VIEWERs cannot delete). */
  onDelete?: (doc: DocumentSummary) => void;
};

/**
 * Presentational: responsive grid of diagram cards. Each card is one real
 * `next/link` anchor (the whole card is the click target, and Enter/Space
 * work natively), because a card is a destination, not an in-place action.
 * An empty list renders a friendly first-run state instead of nothing —
 * `emptyActions` lets the container place its create/import controls there
 * so they exist exactly once on the page.
 */
export function DocumentGrid({ documents, emptyActions, onDelete }: DocumentGridProps) {
  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-border px-6 py-14 text-center">
        <span className="flex size-11 items-center justify-center rounded-full bg-accent text-accent-foreground">
          <FileText className="size-5" aria-hidden="true" />
        </span>
        <div className="flex flex-col gap-1">
          <h2 className="font-heading text-lg font-semibold">Todavía no hay diagramas</h2>
          <p className="max-w-sm text-sm text-muted-foreground">
            {emptyActions
              ? "Crea el primero desde cero o importa un modelo desde un archivo XML."
              : "Cuando alguien del equipo cree un diagrama, lo verás aquí."}
          </p>
        </div>
        {emptyActions ? (
          <div className="flex flex-wrap items-start justify-center gap-2">{emptyActions}</div>
        ) : null}
      </div>
    );
  }

  return (
    <ul
      aria-label="Diagramas"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4"
    >
      {documents.map((doc) => {
        const updated = formatUpdatedAt(doc.updated_at);
        const untitled = !doc.name.trim();
        return (
          <li key={doc.id} className="group/card relative">
            <Link
              href={`/documents/${doc.id}`}
              className="group flex h-full flex-col gap-3 rounded-xl border border-border bg-card p-4 text-card-foreground shadow-xs transition-all outline-none hover:-translate-y-0.5 hover:border-ring hover:shadow-md focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
            >
              <span className="flex size-9 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                <FileText className="size-4" aria-hidden="true" />
              </span>
              <span
                className={cn(
                  "line-clamp-2 text-base leading-snug font-semibold",
                  untitled && "font-medium text-muted-foreground italic",
                )}
              >
                {documentTitle(doc)}
              </span>
              <span className="mt-auto flex flex-col gap-0.5 text-xs text-muted-foreground">
                <span>Revisión {doc.revision}</span>
                {updated ? (
                  <span>
                    Actualizado <time dateTime={doc.updated_at}>{updated}</time>
                  </span>
                ) : null}
              </span>
            </Link>
            {onDelete ? (
              <button
                type="button"
                aria-label={`Eliminar diagrama ${documentTitle(doc)}`}
                title="Eliminar diagrama"
                onClick={() => onDelete(doc)}
                className="absolute top-3 right-3 inline-flex size-8 items-center justify-center rounded-md text-muted-foreground transition-all outline-none hover:bg-destructive/10 hover:text-destructive focus-visible:opacity-100 focus-visible:ring-3 focus-visible:ring-ring/50 sm:opacity-0 sm:group-hover/card:opacity-100"
              >
                <Trash2 className="size-4" aria-hidden="true" />
              </button>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
