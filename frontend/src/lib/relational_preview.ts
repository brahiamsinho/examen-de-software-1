import { apiFetch } from "@/lib/api";
import { saveBlobAsFile } from "@/lib/save_blob";

export type RelationalPreviewColumn = {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
};

export type RelationalPreviewForeignKey = {
  name: string;
  columns: string[];
  referenced_table: string;
  referenced_columns: string[];
  on_delete: string;
  on_update: string;
  relationship_id: string | null;
};

export type RelationalPreviewTable = {
  name: string;
  columns: RelationalPreviewColumn[];
  foreign_keys: RelationalPreviewForeignKey[];
};

export type RelationalPreview = {
  tables: RelationalPreviewTable[];
  sql: string;
};

export function getRelationalPreview(orgSlug: string, docId: string): Promise<RelationalPreview> {
  return apiFetch<RelationalPreview>(
    `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/relational-preview`,
  );
}

export function downloadRelationalSql(sql: string, documentName: string): void {
  const filename = `${documentName.trim().replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "").toLowerCase() || "modelia"}-schema.sql`;
  saveBlobAsFile(new Blob([sql], { type: "application/sql;charset=utf-8" }), filename);
}
