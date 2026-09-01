"""Smoke test proving the Django Ninja wiring works end-to-end.

Uses SimpleTestCase (no database) since the health endpoint touches no
models — this keeps the smoke test runnable without a live Postgres.
"""
from django.test import Client, SimpleTestCase


class HealthEndpointTests(SimpleTestCase):
    def test_health_returns_ok(self):
        response = Client().get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
