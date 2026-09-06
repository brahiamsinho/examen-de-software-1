"""Membership model contract: (user, organization) uniqueness, role choices,
cascade on organization delete, and equal field visibility across roles.
"""
import pytest
from django.db import IntegrityError, transaction

from apps.organizations.constants import Role
from apps.organizations.models import Membership, Organization
from apps.users.models import User


@pytest.mark.django_db
def test_user_organization_pair_is_unique():
    user = User.objects.create_user(email="dana@example.com", password="a-strong-pass-5")
    org = Organization.objects.create(name="Acme Inc", slug="acme")
    Membership.all_objects.create(user=user, organization=org, role=Role.OWNER)

    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.all_objects.create(user=user, organization=org, role=Role.EDITOR)


@pytest.mark.django_db
def test_role_must_be_one_of_the_defined_choices():
    field = Membership._meta.get_field("role")
    choice_values = {value for value, _label in field.choices}

    assert choice_values == {Role.OWNER, Role.EDITOR, Role.VIEWER}


@pytest.mark.django_db
def test_deleting_organization_cascades_its_memberships():
    user = User.objects.create_user(email="erin@example.com", password="a-strong-pass-6")
    org = Organization.objects.create(name="Acme Inc", slug="acme")
    membership = Membership.all_objects.create(user=user, organization=org, role=Role.OWNER)
    membership_pk = membership.pk

    org.delete()

    assert not Membership.all_objects.filter(pk=membership_pk).exists()


@pytest.mark.django_db
def test_viewer_membership_exposes_the_same_identity_fields_as_other_roles():
    user_a = User.objects.create_user(email="frank@example.com", password="a-strong-pass-7")
    user_b = User.objects.create_user(email="grace@example.com", password="a-strong-pass-8")
    user_c = User.objects.create_user(email="heidi@example.com", password="a-strong-pass-9")
    org = Organization.objects.create(name="Acme Inc", slug="acme")

    owner = Membership.all_objects.create(user=user_a, organization=org, role=Role.OWNER)
    editor = Membership.all_objects.create(user=user_b, organization=org, role=Role.EDITOR)
    viewer = Membership.all_objects.create(user=user_c, organization=org, role=Role.VIEWER)

    identity_fields = {f.name for f in Membership._meta.get_fields()}
    for membership in (owner, editor, viewer):
        available = {f for f in identity_fields if hasattr(membership, f)}
        assert available == identity_fields
