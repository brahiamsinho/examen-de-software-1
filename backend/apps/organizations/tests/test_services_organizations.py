"""Service-layer tests for organization CRUD (organization-tenancy spec)."""
import pytest

from apps.organizations import services
from apps.organizations.constants import Plan, Role
from apps.organizations.errors import DuplicateSlugError, OrganizationError
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
        # Backend evidence for web-organization-workspace § "Sole organization deleted
        # falls back to the empty state": zero remaining memberships is exactly the
        # precondition that scenario relies on.
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


class TestBuildSlugBase:
    def test_normal_source_slugifies_to_a_hyphenated_base(self):
        assert services.build_slug_base(source="Acme Corp") == "acme-corp"

    def test_non_latin_source_falls_back_to_the_literal_base(self):
        assert services.build_slug_base(source="日本語") == "workspace"


class TestDeriveWorkspaceName:
    def test_appends_the_workspace_suffix(self):
        assert services.derive_workspace_name(source="Ada") == "Ada's Workspace"


@pytest.mark.django_db
class TestGenerateUniqueSlug:
    """`secrets.token_hex` is patched to a fixed sequence so collisions are
    deterministic (organization-tenancy § Server-Generated Organization Slug).
    """

    def test_first_attempt_is_never_a_bare_base(self, monkeypatch):
        monkeypatch.setattr(services.secrets, "token_hex", lambda n: "abc123")

        slug = services.generate_unique_slug(source="Acme")

        assert slug == "acme-abc123"
        assert slug != "acme"

    def test_collision_retried_up_to_5_suffixed_attempts(self, monkeypatch):
        base_tokens = ["aaaaaa", "bbbbbb", "cccccc", "dddddd", "eeeeee"]
        calls = iter(base_tokens)
        monkeypatch.setattr(services.secrets, "token_hex", lambda n: next(calls))
        for hex_token in base_tokens[:4]:
            make_organization(slug=f"acme-{hex_token}")

        slug = services.generate_unique_slug(source="Acme")

        assert slug == "acme-eeeeee"

    def test_exhaustion_falls_back_to_final_long_token_form(self, monkeypatch):
        base_tokens = ["aaaaaa", "bbbbbb", "cccccc", "dddddd", "eeeeee"]
        fallback_token = "f" * 16
        calls = iter(base_tokens + [fallback_token])
        monkeypatch.setattr(services.secrets, "token_hex", lambda n: next(calls))
        for hex_token in base_tokens:
            make_organization(slug=f"acme-{hex_token}")

        slug = services.generate_unique_slug(source="Acme")

        assert slug == f"workspace-{fallback_token}"

    def test_total_exhaustion_raises_organization_error(self, monkeypatch):
        base_tokens = ["aaaaaa", "bbbbbb", "cccccc", "dddddd", "eeeeee"]
        fallback_token = "f" * 16
        calls = iter(base_tokens + [fallback_token])
        monkeypatch.setattr(services.secrets, "token_hex", lambda n: next(calls))
        for hex_token in base_tokens:
            make_organization(slug=f"acme-{hex_token}")
        make_organization(slug=f"workspace-{fallback_token}")

        with pytest.raises(OrganizationError):
            services.generate_unique_slug(source="Acme")

    def test_generated_slug_never_exceeds_field_length(self):
        long_source = "a" * 100

        slug = services.generate_unique_slug(source=long_source)

        assert len(slug) <= 47
