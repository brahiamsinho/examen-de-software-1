import { FileText, Plus } from "lucide-react";
import Link from "next/link";

import { documentTitle } from "@/components/workspace/documentDisplay";
import type { DocumentSummary } from "@/lib/uml_documents";
import { cn } from "@/lib/utils";

type SidebarDiagramsProps = {
  documents: DocumentSummary[];
  loading: boolean;
  activeDocId: string | null;
  /** Omit to hide the "+" — VIEWERs cannot create diagrams. */
  onNew?: () => void;
};

/**
 * Presentational: the sidebar's "Diagramas" section. Only the current
 * organization's diagrams appear here — organization administration lives in
 * the switcher above and never in this list. The header title links to the
 * dashboard's grid overview; the list itself scrolls inside its own region so
 * a long list never pushes "Miembros"/logout off screen.
 */
export function SidebarDiagrams({ documents, loading, activeDocId, onNew }: SidebarDiagramsProps) {
  return (
    <section aria-label="Diagramas" className="flex min-h-0 flex-1 flex-col gap-1">
      <div className="flex items-center justify-between px-2.5">
        <Link
          href="/dashboard"
          className="rounded-sm text-xs font-semibold tracking-wide text-muted-foreground uppercase outline-none hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
        >
          Diagramas
        </Link>
        {onNew ? (
          <button
            type="button"
            aria-label="Nuevo diagrama"
            onClick={onNew}
            className="inline-flex size-6 items-center justify-center rounded-md text-muted-foreground transition-colors outline-none hover:bg-background hover:text-foreground focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <Plus className="size-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <p className="px-2.5 py-1.5 text-sm text-muted-foreground">Cargando…</p>
        ) : documents.length === 0 ? (
          <p className="px-2.5 py-1.5 text-sm text-muted-foreground">Todavía no hay diagramas</p>
        ) : (
          <ul className="flex flex-col gap-0.5">
            {documents.map((doc) => {
              const active = doc.id === activeDocId;
              return (
                <li key={doc.id}>
                  <Link
                    href={`/documents/${doc.id}`}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2.5 py-1.5 text-sm transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                      active
                        ? "bg-accent font-medium text-accent-foreground"
                        : "text-foreground hover:bg-background",
                    )}
                  >
                    <FileText className="size-4 shrink-0 opacity-60" aria-hidden="true" />
                    <span className={cn("truncate", !doc.name.trim() && "italic opacity-70")}>
                      {documentTitle(doc)}
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
