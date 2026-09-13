"""`UmlDocument` model contract: shape, tenant-scoping manager wiring.

Mirrors `apps.organizations.tests.test_models_membership`'s style of
asserting on `Meta`/manager wiring directly, without going through the
service layer (model-layer tests must not depend on `services.py`).
"""
import uuid

from django.db import models

from apps.organizations.models import TenantScopedManager
from apps.uml_documents.models import UmlDocument


def test_uml_document_has_expected_fields():
    fields_by_name = {field.name: field for field in UmlDocument._meta.get_fields()}

    assert isinstance(fields_by_name["id"], models.UUIDField)
    assert fields_by_name["id"].primary_key is True
    assert fields_by_name["id"].default is uuid.uuid4

    assert isinstance(fields_by_name["owner_id"], models.CharField)

    assert isinstance(fields_by_name["revision"], models.PositiveIntegerField)
    assert fields_by_name["revision"].default == 1

    assert isinstance(fields_by_name["created_at"], models.DateTimeField)
    assert isinstance(fields_by_name["updated_at"], models.DateTimeField)

    data_field = fields_by_name["data"]
    assert isinstance(data_field, models.JSONField)
    assert data_field.default() == {}


def test_uml_document_managers():
    assert isinstance(UmlDocument.objects, TenantScopedManager)
    assert isinstance(UmlDocument.all_objects, models.Manager)
    assert not isinstance(UmlDocument.all_objects, TenantScopedManager)
    assert UmlDocument._meta.base_manager_name == "all_objects"
