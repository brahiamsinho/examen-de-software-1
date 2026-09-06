"""Service-layer tests for organization CRUD (organization-tenancy spec)."""
import pytest

from apps.organizations import services
from apps.organizations.constants import Plan, Role
from apps.organizations.errors import DuplicateSlugError
from apps.organizations.models import Membership, Organization
from apps.organizations.tests.factories import make_organization
from apps.users.tests.factories import make_user


@pytest.mark.django_db
class TestCreateOrganization:
    def test_creator_becomes_owner_atomically(self):
        user = make_user()

        org = services.create_organization(owner=user, name="Acme", slug="acme")

        assert isinstance(org, Organization)
        assert org.plan == Plan.STARTER
        membership = Membership.all_objects.get(organization=org, user=user)
        assert membership.role == Role.OWNER

    def test_duplicate_slug_rejected(self):
        make_organization(slug="taken")
        user = make_user()

        with pytest.raises(DuplicateSlugError):
            services.create_organization(owner=user, name="Other", slug="taken")


@pytest.mark.django_db
class TestRenameOrganization:
    def test_rename_updates_name(self):
        org = make_organization(name="Old Name")

        updated = services.rename_organization(organization=org, name="New Name")

        org.refresh_from_db()
        assert updated.name == "New Name"
        assert org.name == "New Name"


@pytest.mark.django_db
class TestDeleteOrganization:
    def test_hard_delete_cascades_memberships(self):
        org = make_organization()
        org_id = org.id

        services.delete_organization(organization=org)

        assert not Organization.objects.filter(id=org_id).exists()
        assert not Membership.all_objects.filter(organization_id=org_id).exists()


@pytest.mark.django_db
class TestListUserOrganizations:
    def test_returns_only_orgs_the_user_belongs_to(self):
        user = make_user()
        org_a = make_organization(owner=user)
        make_organization()  # unrelated org

        result = list(services.list_user_organizations(user=user))

        assert result == [org_a]
