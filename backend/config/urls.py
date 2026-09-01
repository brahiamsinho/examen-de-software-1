"""
URL configuration for the config project.

The `urlpatterns` list routes URLs to views. No business apps exist yet
(see backend/apps/), so only the Django admin and the Ninja API root
(with its one health-check endpoint) are wired up for now.
"""
from django.contrib import admin
from django.urls import path

from config.api import api

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", api.urls),
]
