import { useCallback, useEffect, useRef, useState } from "react";

import {
  deploymentErrorMessage,
  getLatestDeployment,
  isInProgress,
  startDeployment,
  stopDeployment,
  type Deployment,
} from "@/lib/backend_deployments";

const POLL_INTERVAL_MS = 3000;

/**
 * Local state of one document's running backend. Loads the latest deployment
 * on mount, starts/stops it, and polls `latest` every 3 s while the runner is
 * still working (queued/building/starting); polling stops on running, failed,
 * stopped or unmount. `actionError` is a friendly message for a failed
 * start/stop (quota, nothing to generate, runner down); a failed deployment
 * itself is reported through `deployment.status === "failed"`.
 */
export function useBackendDeployment(orgSlug: string | null, docId: string) {
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [loading, setLoading] = useState(orgSlug !== null);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [trackedKey, setTrackedKey] = useState(`${orgSlug}/${docId}`);
  const requestSeq = useRef(0);

  // Reset synchronously when the target changes (see useMembers for the rationale).
  const key = `${orgSlug}/${docId}`;
  if (key !== trackedKey) {
    setTrackedKey(key);
    setDeployment(null);
    setActionError(null);
    setLoading(orgSlug !== null);
  }

  useEffect(() => {
    if (orgSlug === null) return;
    let cancelled = false;
    getLatestDeployment(orgSlug, docId)
      .then((latest) => {
        if (!cancelled) setDeployment(latest);
      })
      .catch(() => {
        /* status is best-effort on load: the page stays usable without it */
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [orgSlug, docId]);

  const status = deployment?.status ?? null;
  const polling = status !== null && isInProgress(status);

  useEffect(() => {
    if (orgSlug === null || !polling) return;
    let cancelled = false;
    const timer = setInterval(() => {
      const seq = ++requestSeq.current;
      getLatestDeployment(orgSlug, docId)
        .then((latest) => {
          // Ignore a slow poll that was overtaken by a newer request or a start/stop.
          if (!cancelled && seq === requestSeq.current && latest) setDeployment(latest);
        })
        .catch(() => {
          /* transient poll failure: try again on the next tick */
        });
    }, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [orgSlug, docId, polling]);

  const start = useCallback(async () => {
    if (orgSlug === null) return;
    setBusy(true);
    setActionError(null);
    requestSeq.current++;
    try {
      setDeployment(await startDeployment(orgSlug, docId));
    } catch (error) {
      setActionError(deploymentErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, docId]);

  const stop = useCallback(async () => {
    if (orgSlug === null || deployment === null) return;
    setBusy(true);
    setActionError(null);
    requestSeq.current++;
    try {
      setDeployment(await stopDeployment(orgSlug, docId, deployment.id));
    } catch (error) {
      setActionError(deploymentErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }, [orgSlug, docId, deployment]);

  return { deployment, loading, busy, actionError, start, stop };
}
