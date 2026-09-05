"""Organization model contract: slug-addressed tenant, `plan` default, UUID pk."""
import uuid

import pytest
from django.db import IntegrityError, transaction

from apps.identity.constants import Plan
from apps.identity.models import Organization


@pytest.mark.django_db
def test_new_organization_defaults_to_starter_plan():
    org = Organization.objects.create(name="Acme Inc", slug="acme")

    assert org.plan == Plan.STARTER


@pytest.mark.django_db
def test_slug_uniqueness_is_enforced():
    Organization.objects.create(name="Acme Inc", slug="acme")

    with pytest.raises(IntegrityError), transaction.atomic():
        Organization.objects.create(name="Acme Duplicate", slug="acme")


@pytest.mark.django_db
def test_organization_primary_key_is_a_uuid():
    org = Organization.objects.create(name="Acme Inc", slug="acme")

    assert isinstance(org.id, uuid.UUID)
