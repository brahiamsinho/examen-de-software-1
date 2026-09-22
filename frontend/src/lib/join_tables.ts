import { apiFetch } from "@/lib/api";

/**
 * Domain client for `apps/relational_mapping`'s join-table preview: the
 * intermediate table a both-ends-many association needs once the backend is
 * generated (`Class A <-*..*-> Class B` becomes a `class_a_class_b` table),
 * shown on the canvas as a hint before the user ever generates anything.
 * Reuses the SAME `map_to_relational` the real generator runs, so the name
 * and columns shown here never drift from what actually gets built.
 */
export type JoinTableHint = {
  relationship_id: string;
  table_name: string;
  columns: string[];
};

export function getJoinTables(orgSlug: string, docId: string): Promise<JoinTableHint[]> {
  return apiFetch<JoinTableHint[]>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/join-tables`,
  );
}
