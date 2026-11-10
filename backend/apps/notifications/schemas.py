"""Request schemas for device registration."""
from ninja import Schema
from pydantic import Field


class DeviceIn(Schema):
    token: str = Field(min_length=1, max_length=512, pattern=r"\S")
    platform: str = Field(default="android", max_length=16)


class DeviceRemoveIn(Schema):
    token: str = Field(min_length=1, max_length=512)
