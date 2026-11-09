import { ApiError, apiFetch } from "@/lib/api";

export type RemoteDestination = {
  id: string;
  name: string;
  destination_type: "vm_containers";
  environment: "development" | "testing" | "production";
  managed_config_id: string;
  connectivity_config_ref: string;
  capabilities: string[];
  enabled: boolean;
};

export type RemotePreview = {
  checks: { name: string; passed: boolean; message: string }[];
  warnings: string[];
  can_request: boolean;
  artifact_sha256: string;
  document_revision: number;
};

export type RemoteRequest = {
  id: string;
  destination_id: string;
  destination_name: string;
  environment: string;
  action: string;
  status: string;
  document_revision: number;
  artifact_sha256: string;
  error_code: string;
  error_message: string;
  correlation_id: string;
  created_at: string;
  updated_at: string;
};

export type RemoteEvent = { id: number; action: string; previous_status: string; new_status: string; result: string; error_code: string; message: string; correlation_id: string; created_at: string };

function base(org: string, doc: string) {
  return `/api/orgs/${encodeURIComponent(org)}/documents/${encodeURIComponent(doc)}`;
}

export const getRemoteDestinations = (org: string, doc: string) => apiFetch<RemoteDestination[]>(`${base(org, doc)}/remote-destinations`);
export const previewRemoteDeployment = (org: string, doc: string, destination_id: string) => apiFetch<RemotePreview>(`${base(org, doc)}/remote-deployments/preview`, { method: "POST", body: JSON.stringify({ destination_id }) });
export const requestRemoteDeployment = (org: string, doc: string, destination_id: string) => apiFetch<RemoteRequest>(`${base(org, doc)}/remote-deployments`, { method: "POST", body: JSON.stringify({ destination_id }) });
export const getRemoteConfirmation = (org: string, doc: string, id: string) => apiFetch<{ confirmation_token: string; expires_at: string }>(`${base(org, doc)}/remote-deployments/${encodeURIComponent(id)}/confirmation`, { method: "POST" });
export const confirmRemoteDeployment = (org: string, doc: string, id: string, confirmation_token: string) => apiFetch<RemoteRequest>(`${base(org, doc)}/remote-deployments/${encodeURIComponent(id)}/confirm`, { method: "POST", body: JSON.stringify({ confirmation_token }) });
export const getRemoteEvents = (org: string, doc: string, id: string) => apiFetch<RemoteEvent[]>(`${base(org, doc)}/remote-deployments/${encodeURIComponent(id)}/events`);

export function remoteDeploymentError(error: unknown) {
  if (error instanceof ApiError) return error.detail;
  return "No se pudo completar la operación remota.";
}
