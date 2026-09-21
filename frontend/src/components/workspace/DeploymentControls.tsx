"use client";

import { AlertCircle, FileText, Loader2, Play, RotateCw, Square } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import { isInProgress, type Deployment, type DeploymentStatus } from "@/lib/backend_deployments";
import { cn } from "@/lib/utils";

type DeploymentState = {
  deployment: Deployment | null;
  busy: boolean;
  actionError: string | null;
  onStart: () => void;
  onStop: () => void;
};

const STEP_LABELS: Partial<Record<DeploymentStatus, string>> = {
  queued: "En cola…",
  building: "Construyendo…",
  starting: "Iniciando…",
};

/**
 * Status-aware action group of the editor header. Idle/stopped -> "Generar
 * backend"; queued/building/starting -> disabled with the current step and a
 * spinner; running -> badge + links + Detener/Regenerar; failed -> "Reintentar".
 * The reason and log of a failure live in `DeploymentNotices`, below the header.
 */
export function DeploymentActions({ deployment, busy, onStart, onStop }: DeploymentState) {
  const status = deployment?.status ?? null;

  if (status !== null && isInProgress(status)) {
    return (
      <Button type="button" size="lg" disabled aria-live="polite">
        <Loader2 className="animate-spin" />
        {STEP_LABELS[status]}
      </Button>
    );
  }

  if (status === "running") {
    const linkClass = buttonVariants({ variant: "outline", size: "lg" });
    return (
      <>
        <span className="inline-flex h-9 items-center gap-2 rounded-lg border border-border bg-background px-3 text-sm font-medium text-foreground">
          <span className="size-2 rounded-full bg-success" aria-hidden />
          En ejecución
        </span>
        {/* The generated API has no page at its root (404); the OpenAPI document is the useful, always-200 entry point. */}
        {deployment?.openapi_url ? (
          <a className={linkClass} href={deployment.openapi_url} target="_blank" rel="noreferrer">
            <FileText />
            Documentación API
          </a>
        ) : null}
        <Button type="button" size="lg" variant="outline" onClick={onStop} disabled={busy}>
          <Square />
          Detener
        </Button>
        <Button type="button" size="lg" variant="outline" onClick={onStart} disabled={busy}>
          <RotateCw />
          Regenerar
        </Button>
      </>
    );
  }

  const retry = status === "failed";
  return (
    <Button type="button" size="lg" onClick={onStart} disabled={busy}>
      {busy ? <Loader2 className="animate-spin" /> : retry ? <RotateCw /> : <Play />}
      {retry ? "Reintentar" : "Generar backend"}
    </Button>
  );
}

/**
 * Feedback under the header: a friendly message when starting/stopping failed
 * (quota, nothing to generate, runner down), the reason a deployment failed,
 * and a collapsible build log while building or after a failure.
 */
export function DeploymentNotices({ deployment, actionError, className }: Pick<DeploymentState, "deployment" | "actionError"> & { className?: string }) {
  const failed = deployment?.status === "failed";
  const showLog =
    deployment !== null && deployment.log_tail.trim() !== "" && (failed || isInProgress(deployment.status));

  if (!actionError && !failed && !showLog) return null;

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {actionError ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      ) : null}
      {failed ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>
            <p className="font-medium">No se pudo iniciar el backend.</p>
            {deployment.error ? <p className="opacity-80">{deployment.error}</p> : null}
          </AlertDescription>
        </Alert>
      ) : null}
      {showLog ? (
        <details className="group rounded-lg border border-border bg-background text-sm">
          <summary className="cursor-pointer rounded-lg px-3 py-2 font-medium text-foreground outline-none select-none focus-visible:ring-3 focus-visible:ring-ring/50">
            Registro de construcción
          </summary>
          <pre className="max-h-56 overflow-auto border-t border-border bg-muted/40 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap text-foreground/80">
            {deployment.log_tail}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
