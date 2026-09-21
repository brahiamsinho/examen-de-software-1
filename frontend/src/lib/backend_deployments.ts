import { ApiError, apiFetch } from "@/lib/api";

/**
 * Domain client for `apps/backend_deployments`: run the Spring Boot backend
 * generated from a document on the runner and read/stop it. One deployment
 * per document is "current"; `latest` is the poll target (the server
 * refreshes its state from the runner on every read).
 */

export type DeploymentStatus = "queued" | "building" | "starting" | "running" | "failed" | "stopped";

export type Deployment = {
  id: string;
  document_id: string;
  status: DeploymentStatus;
  error: string;
  log_tail: string;
  public_path: string;
  public_url: string | null;
  openapi_url: string | null;
  docs_url: string | null;
  created_at: string;
  updated_at: string;
};

/** Statuses in which the runner is still working, so the UI keeps polling. */
export const IN_PROGRESS_STATUSES: readonly DeploymentStatus[] = ["queued", "building", "starting"];

export function isInProgress(status: DeploymentStatus): boolean {
  return IN_PROGRESS_STATUSES.includes(status);
}

function base(orgSlug: string, docId: string): string {
  return `/api/orgs/${encodeURIComponent(orgSlug)}/documents/${encodeURIComponent(docId)}/deployments`;
}

export function startDeployment(orgSlug: string, docId: string): Promise<Deployment> {
  return apiFetch<Deployment>(base(orgSlug, docId), { method: "POST" });
}

/** `null` when the document has never been deployed (the API answers 404). */
export async function getLatestDeployment(orgSlug: string, docId: string): Promise<Deployment | null> {
  try {
    return await apiFetch<Deployment>(`${base(orgSlug, docId)}/latest`);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export function stopDeployment(orgSlug: string, docId: string, deploymentId: string): Promise<Deployment> {
  return apiFetch<Deployment>(`${base(orgSlug, docId)}/${encodeURIComponent(deploymentId)}`, {
    method: "DELETE",
  });
}

const FRIENDLY_MESSAGES: Record<string, string> = {
  quota_exceeded:
    "Alcanzaste el límite de backends en ejecución de tu organización. Detén uno e inténtalo de nuevo.",
  nothing_to_generate: "El diagrama aún no tiene clases. Agrega al menos una para generar el backend.",
  generation_failed: "No se pudo generar el backend a partir de este diagrama. Revisa el modelo.",
  runner_unavailable: "El servicio que ejecuta los backends no está disponible ahora. Inténtalo en unos minutos.",
  runner_rejected: "El servicio de ejecución rechazó el backend generado. Revisa el modelo e inténtalo de nuevo.",
};

/** Maps a failed start/stop call to a friendly Spanish message (never a raw code). */
export function deploymentErrorMessage(error: unknown): string {
  if (error instanceof ApiError && FRIENDLY_MESSAGES[error.code]) {
    return FRIENDLY_MESSAGES[error.code]!;
  }
  if (error instanceof ApiError && error.status === 403) {
    return "Tu rol en esta organización no permite ejecutar backends.";
  }
  return "Ocurrió un error inesperado. Intenta de nuevo.";
}
