"""Register and remove the calling user's phone for push notifications."""
from django.http import HttpRequest
from ninja import Router, Status
from ninja.security import django_auth

from apps.notifications import service
from apps.notifications.schemas import DeviceIn, DeviceRemoveIn

router = Router()


@router.post("", response={204: None}, auth=django_auth)
def register_device(request: HttpRequest, payload: DeviceIn):
    service.register_device(user=request.user, token=payload.token.strip(), platform=payload.platform)
    return Status(204, None)


@router.delete("", response={204: None}, auth=django_auth)
def unregister_device(request: HttpRequest, payload: DeviceRemoveIn):
    service.unregister_device(user=request.user, token=payload.token.strip())
    return Status(204, None)
