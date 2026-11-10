"""Remote deployment governance with no network or runner side effects.

This module deliberately knows no VM address, credential, Docker client, or SSH
client. A future approved executor may consume AUTHORIZED requests; until then
authorization is recorded truthfully and the request is not marked as running.
"""
import hashlib
import secrets
from datetime import timedelta

from django_mongodb_backend import transaction

from config.transactions import run_atomic
from django.http import Http404
from django.utils import timezone

from apps.backend_deployments.models import (
    RemoteDeploymentDestination,
    RemoteDeploymentEvent,
    RemoteDeploymentRequest,
    RemoteDeploymentStatus,
)
from apps.generation_export.service import build_project_archive

CONFIRMATION_TTL = timedelta(minutes=10)
_TRANSITIONS = {
    RemoteDeploymentStatus.DRAFT: {RemoteDeploymentStatus.VALIDATED, RemoteDeploymentStatus.FAILED},
    RemoteDeploymentStatus.VALIDATED: {RemoteDeploymentStatus.AWAITING_CONFIRMATION, RemoteDeploymentStatus.CANCELLED},
    RemoteDeploymentStatus.AWAITING_CONFIRMATION: {RemoteDeploymentStatus.AUTHORIZED, RemoteDeploymentStatus.CANCELLED, RemoteDeploymentStatus.FAILED},
    RemoteDeploymentStatus.AUTHORIZED: {RemoteDeploymentStatus.QUEUED, RemoteDeploymentStatus.CANCELLED},
    RemoteDeploymentStatus.QUEUED: {RemoteDeploymentStatus.DEPLOYING, RemoteDeploymentStatus.FAILED, RemoteDeploymentStatus.CANCELLED},
    RemoteDeploymentStatus.DEPLOYING: {RemoteDeploymentStatus.RUNNING, RemoteDeploymentStatus.FAILED, RemoteDeploymentStatus.CANCELLED},
}


class RemoteDeploymentError(Exception):
    code = "remote_deployment_error"


class RemoteDeploymentBlocked(RemoteDeploymentError):
    code = "remote_deployment_blocked"


class ConfirmationInvalid(RemoteDeploymentError):
    code = "confirmation_invalid"


class ConfirmationExpired(RemoteDeploymentError):
    code = "confirmation_expired"


class ConfirmationReused(RemoteDeploymentError):
    code = "confirmation_reused"


def _safe_message(message: str) -> str:
    # Never persist common secret-shaped values supplied by an executor or client.
    lowered = message.lower()
    if any(marker in lowered for marker in ("authorization", "token", "password", "private key", "ssh-")):
        return "Se ocultó un detalle sensible del error."
    return message[:500]


def _event(request, actor, *, action, previous, new, result, code="", message=""):
    return RemoteDeploymentEvent.objects.unscoped().create(
        organization=request.organization, request=request, actor=actor, action=action,
        previous_status=previous, new_status=new, result=result, error_code=code,
        message=_safe_message(message), correlation_id=request.correlation_id,
    )


def destinations(organization):
    return RemoteDeploymentDestination.objects.for_organization(organization).order_by("environment", "name")


def get_destination(organization, destination_id):
    try:
        return RemoteDeploymentDestination.objects.for_organization(organization).get(id=destination_id)
    except RemoteDeploymentDestination.DoesNotExist as exc:
        raise Http404("Remote destination not found") from exc


def preview(*, organization, document, destination_id):
    """Pure preflight: builds only an in-memory archive and never creates rows."""
    destination = get_destination(organization, destination_id)
    checks, warnings = [], []
    checks.append({"name": "destination_exists", "passed": True, "message": "Destino autorizado encontrado."})
    checks.append({"name": "destination_enabled", "passed": destination.enabled, "message": "Destino habilitado." if destination.enabled else "El destino está deshabilitado."})
    configured = bool(destination.managed_config_id and destination.connectivity_config_ref)
    checks.append({"name": "managed_configuration", "passed": configured, "message": "Configuración administrada disponible." if configured else "Falta configuración administrada."})
    try:
        artifact = build_project_archive(document)
        digest = hashlib.sha256(artifact).hexdigest()
        checks.append({"name": "artifact_generation", "passed": True, "message": "El artefacto backend puede generarse."})
    except Exception as exc:
        digest = ""
        checks.append({"name": "artifact_generation", "passed": False, "message": str(exc)[:300]})
    warnings.append("La validación es local: no abrió conexiones SSH, Docker remoto ni transfirió archivos.")
    warnings.append("No existe un ejecutor remoto autorizado en esta instalación; una autorización no inicia una VM.")
    return {
        "destination": destination,
        "checks": checks,
        "warnings": warnings,
        "can_request": all(check["passed"] for check in checks),
        "artifact_sha256": digest,
        "document_revision": document.revision,
    }


def request_deployment(*, organization, document, user, destination_id):
    preview_result = preview(organization=organization, document=document, destination_id=destination_id)
    if not preview_result["can_request"]:
        raise RemoteDeploymentBlocked("La validación previa bloquea la solicitud de despliegue remoto.")
    destination = preview_result["destination"]
    with transaction.atomic():
        # A document/destination pair may have only one active authorization flow.
        duplicate = RemoteDeploymentRequest.objects.for_organization(organization).filter(
            document_id=document.id, destination=destination,
            status__in=[RemoteDeploymentStatus.AWAITING_CONFIRMATION, RemoteDeploymentStatus.AUTHORIZED],
        ).exists()
        if duplicate:
            raise RemoteDeploymentBlocked("Ya existe una solicitud remota pendiente para este destino.")
        request = RemoteDeploymentRequest.objects.unscoped().create(
            organization=organization, document_id=document.id, destination=destination, created_by=user,
            document_revision=preview_result["document_revision"], artifact_sha256=preview_result["artifact_sha256"],
            validation={"checks": preview_result["checks"], "warnings": preview_result["warnings"]},
            status=RemoteDeploymentStatus.AWAITING_CONFIRMATION,
        )
        _event(request, user, action="request", previous=RemoteDeploymentStatus.VALIDATED,
               new=request.status, result="accepted", message="Solicitud creada; requiere confirmación explícita.")
    return request


def issue_confirmation(*, request, user):
    """Creates a one-use proof token; only its digest is stored."""
    if request.status != RemoteDeploymentStatus.AWAITING_CONFIRMATION:
        raise ConfirmationReused("La solicitud ya no admite una confirmación.")
    token = secrets.token_urlsafe(32)
    request.confirmation_digest = hashlib.sha256(token.encode()).hexdigest()
    request.confirmation_expires_at = timezone.now() + CONFIRMATION_TTL
    request.save(update_fields=["confirmation_digest", "confirmation_expires_at", "updated_at"])
    return token


def confirm(*, organization, document, request_id, user, token):
    rejected = None
    request = None

    def _confirm() -> None:
        # The request row is rewritten on every path that matters, so two
        # confirmations at once conflict and the loser runs again, finding the
        # confirmation already used (`run_atomic` retries it).
        nonlocal rejected, request
        rejected = None
        try:
            request = RemoteDeploymentRequest.objects.for_organization(organization).select_related("destination").get(id=request_id, document_id=document.id)
        except RemoteDeploymentRequest.DoesNotExist as exc:
            raise Http404("Remote deployment request not found") from exc
        if request.created_by_id != user.id:
            raise ConfirmationInvalid("La confirmación pertenece a otro usuario.")
        if request.confirmation_used_at is not None:
            raise ConfirmationReused("La confirmación ya fue utilizada.")
        if request.confirmation_expires_at is None or request.confirmation_expires_at <= timezone.now():
            previous = request.status
            request.status = RemoteDeploymentStatus.FAILED
            request.error_code = "confirmation_expired"
            request.error_message = "La confirmación venció; crea una nueva solicitud."
            request.save(update_fields=["status", "error_code", "error_message", "updated_at"])
            _event(
                request, user, action="confirm", previous=previous, new=request.status,
                result="rejected", code=request.error_code, message=request.error_message,
            )
            rejected = ConfirmationExpired(request.error_message)
        elif not secrets.compare_digest(request.confirmation_digest, hashlib.sha256(token.encode()).hexdigest()):
            raise ConfirmationInvalid("La confirmación no coincide con la solicitud.")
        else:
            current = preview(organization=organization, document=document, destination_id=request.destination_id)
            if not current["can_request"] or current["artifact_sha256"] != request.artifact_sha256 or current["document_revision"] != request.document_revision:
                request.status = RemoteDeploymentStatus.FAILED
                request.error_code, request.error_message = "stale_request", "El documento, artefacto o destino cambió después de validar."
                request.save(update_fields=["status", "error_code", "error_message", "updated_at"])
                _event(request, user, action="confirm", previous=RemoteDeploymentStatus.AWAITING_CONFIRMATION, new=request.status, result="rejected", code=request.error_code, message=request.error_message)
                rejected = RemoteDeploymentBlocked(request.error_message)
            else:
                request.confirmation_used_at = timezone.now()
                request.status = RemoteDeploymentStatus.AUTHORIZED
                request.save(update_fields=["confirmation_used_at", "status", "updated_at"])
                _event(request, user, action="confirm", previous=RemoteDeploymentStatus.AWAITING_CONFIRMATION, new=request.status, result="authorized", message="Autorización registrada. La ejecución remota permanece deshabilitada.")
    run_atomic(_confirm)
    if rejected is not None:
        raise rejected
    return request


def get_request(organization, document, request_id):
    try:
        return RemoteDeploymentRequest.objects.for_organization(organization).select_related("destination").get(id=request_id, document_id=document.id)
    except RemoteDeploymentRequest.DoesNotExist as exc:
        raise Http404("Remote deployment request not found") from exc
