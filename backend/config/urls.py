"""
URL configuration for the config project.

The `urlpatterns` list routes URLs to views. No business apps exist yet
(see backend/apps/), so only the Django admin is wired up for now.
"""
from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
