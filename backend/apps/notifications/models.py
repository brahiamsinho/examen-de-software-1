"""Where to push a notification: one Firebase registration token per phone."""
from django.conf import settings
from django.db import models


class DeviceToken(models.Model):
    """A phone's Firebase registration token, owned by whoever logged in on it.

    Deliberately not tied to an organization: a person belongs to several, and
    who may be notified is decided when sending (membership is re-checked then),
    so leaving an organization stops its pushes without touching this table.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(max_length=16, default="android")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.user_id}:{self.platform}"
