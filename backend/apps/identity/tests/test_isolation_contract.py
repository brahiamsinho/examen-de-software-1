"""The spec-mandated enumeration test (tenant-isolation spec, Requirement:
Unscoped-Reachability Test Coverage): every concrete `TenantScopedModel`
subclass must carry a non-null `organization` FK and a scoped-only default
manager. Fails automatically when a future cycle adds a subclass that
doesn't satisfy the contract.
"""
import pytest
from django.apps import apps

from apps.identity.errors import TenantScopeViolation
from apps.identity.models import TenantScopedModel


def _concrete_tenant_scoped_models():
    return [
        model
        for model in apps.get_models()
        if issubclass(model, TenantScopedModel) and not model._meta.abstract
    ]


def test_every_tenant_scoped_model_has_a_non_null_organization_fk():
    models = _concrete_tenant_scoped_models()
    assert models, "expected at least one concrete TenantScopedModel subclass"

    for model in models:
        field = model._meta.get_field("organization")
        assert field.null is False
        assert field.many_to_one is True


def test_every_tenant_scoped_model_has_a_raising_default_manager():
    models = _concrete_tenant_scoped_models()
    assert models, "expected at least one concrete TenantScopedModel subclass"

    for model in models:
        with pytest.raises(TenantScopeViolation):
            model.objects.all()
