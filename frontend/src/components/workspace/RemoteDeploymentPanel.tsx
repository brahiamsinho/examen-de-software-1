"use client";

import { AlertTriangle, CheckCircle2, Loader2, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { confirmRemoteDeployment, getRemoteConfirmation, getRemoteDestinations, getRemoteEvents, previewRemoteDeployment, remoteDeploymentError, requestRemoteDeployment, type RemoteDestination, type RemoteEvent, type RemotePreview, type RemoteRequest } from "@/lib/remote_deployments";

export function RemoteDeploymentPanel({ orgSlug, docId, canDeploy }: { orgSlug: string; docId: string; canDeploy: boolean }) {
  const [destinations, setDestinations] = useState<RemoteDestination[]>([]);
  const [destinationId, setDestinationId] = useState("");
  const [preview, setPreview] = useState<RemotePreview | null>(null);
  const [request, setRequest] = useState<RemoteRequest | null>(null);
  const [events, setEvents] = useState<RemoteEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { getRemoteDestinations(orgSlug, docId).then(setDestinations).catch(() => setError("No se pudieron cargar los destinos remotos.")); }, [orgSlug, docId]);
  const selected = destinations.find((item) => item.id === destinationId);
  async function validate() { if (!destinationId) return; setBusy(true); setError(null); try { setPreview(await previewRemoteDeployment(orgSlug, docId, destinationId)); } catch (err) { setError(remoteDeploymentError(err)); } finally { setBusy(false); } }
  async function requestAuthorization() { if (!destinationId) return; setBusy(true); setError(null); try { const next = await requestRemoteDeployment(orgSlug, docId, destinationId); setRequest(next); setEvents(await getRemoteEvents(orgSlug, docId, next.id)); } catch (err) { setError(remoteDeploymentError(err)); } finally { setBusy(false); } }
  async function confirm() { if (!request) return; setBusy(true); setError(null); try { const proof = await getRemoteConfirmation(orgSlug, docId, request.id); setRequest(await confirmRemoteDeployment(orgSlug, docId, request.id, proof.confirmation_token)); setEvents(await getRemoteEvents(orgSlug, docId, request.id)); } catch (err) { setError(remoteDeploymentError(err)); } finally { setBusy(false); } }

  return <div className="flex flex-col gap-3">
    <div><h2 className="font-heading text-base font-semibold">Despliegue remoto en VM</h2><p className="text-sm text-muted-foreground">Validación local y autorización gobernada. No sustituye el despliegue local.</p></div>
    {destinations.length === 0 ? <Alert variant="caution"><AlertTriangle /><AlertDescription>No existe un destino remoto autorizado. Puedes configurar y validar el proceso, pero no ejecutar el despliegue remoto.</AlertDescription></Alert> : <>
      <label className="flex flex-col gap-1 text-sm font-medium">Destino autorizado
        <Select value={destinationId} onChange={(event) => { setDestinationId(event.target.value); setPreview(null); }}><option value="">Selecciona un destino</option>{destinations.map((item) => <option key={item.id} value={item.id} disabled={!item.enabled}>{item.name} ({item.environment})</option>)}</Select>
      </label>
      {selected ? <p className="text-xs text-muted-foreground">Configuración: {selected.managed_config_id}. Capacidades: {selected.capabilities.join(", ") || "sin declarar"}.</p> : null}
      <Button type="button" variant="outline" onClick={() => void validate()} disabled={!destinationId || busy}>{busy ? <Loader2 className="animate-spin" /> : <CheckCircle2 />}Validar despliegue</Button>
    </>}
    {preview ? <div className="rounded-lg border p-3 text-sm"><p className="font-medium">Vista previa local</p>{preview.checks.map((check) => <p key={check.name} className={check.passed ? "text-success" : "text-destructive"}>{check.passed ? "Aprobada" : "Bloqueada"}: {check.message}</p>)}{preview.warnings.map((warning) => <p key={warning} className="mt-1 text-muted-foreground">Advertencia: {warning}</p>)}</div> : null}
    {preview?.can_request && canDeploy && !request ? <Button type="button" onClick={() => void requestAuthorization()} disabled={busy}><ShieldCheck />Solicitar autorización remota</Button> : null}
    {request?.status === "AWAITING_CONFIRMATION" && canDeploy ? <Alert><ShieldCheck /><AlertDescription><p>Confirmar despliegue: {request.destination_name}, entorno {request.environment}, revisión {request.document_revision}.</p><Button className="mt-2" type="button" onClick={() => void confirm()} disabled={busy}>Confirmar autorización</Button></AlertDescription></Alert> : null}
    {request ? <div className="rounded-lg border p-3 text-sm"><p className="font-medium">Estado: {request.status}</p>{request.status === "AUTHORIZED" ? <p className="text-muted-foreground">Autorizado, pero no ejecutado: no hay un ejecutor remoto aprobado.</p> : null}{events.map((event) => <p key={event.id} className="mt-1 text-muted-foreground">{event.new_status}: {event.message}</p>)}</div> : null}
    {!canDeploy ? <p className="text-sm text-muted-foreground">Solo un OWNER puede solicitar o confirmar operaciones remotas.</p> : null}
    {error ? <Alert variant="destructive"><AlertTriangle /><AlertDescription>{error}</AlertDescription></Alert> : null}
  </div>;
}
