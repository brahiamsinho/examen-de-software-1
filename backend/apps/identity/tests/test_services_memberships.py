"""Service-layer tests for membership add/change-role/remove and the
last-owner invariant (organization-membership spec).
"""
import pytest

from apps.identity import services
from apps.identity.constants import Role
from apps.identity.errors import DuplicateMembershipError, LastOwnerError, UserNotFoundError
from apps.identity.models import Membership
from apps.identity.tests.factories import make_membership, make_org_with_roles, make_organization, make_user


@pytest.mark.django_db
class TestAddMember:
    def test_add_existing_user_by_email(self):
        org = make_organization()
        new_user = make_user(email="new-member@example.com")

        membership = services.add_member(organization=org, email="new-member@example.com", role=Role.EDITOR)

        assert membership.user_id == new_user.id
        assert membership.organization_id == org.id
        assert membership.role == Role.EDITOR

    def test_unregistered_email_fails(self):
        org = make_organization()

        with pytest.raises(UserNotFoundError):
            services.add_member(organization=org, email="ghost@example.com", role=Role.EDITOR)

    def test_duplicate_membership_rejected(self):
        org = make_organization()
        user = make_user(email="dupe@example.com")
        make_membership(organization=org, user=user, role=Role.VIEWER)

        with pytest.raises(DuplicateMembershipError):
            services.add_member(organization=org, email="dupe@example.com", role=Role.EDITOR)


@pytest.mark.django_db
class TestChangeMemberRole:
    def test_owner_changes_editor_to_viewer(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()

        membership = services.change_member_role(organization=org, target_user_id=editor.id, new_role=Role.VIEWER)

        assert membership.role == Role.VIEWER

    def test_demoting_sole_owner_fails(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()

        with pytest.raises(LastOwnerError):
            services.change_member_role(organization=org, target_user_id=owner.id, new_role=Role.EDITOR)

        membership = Membership.all_objects.get(organization=org, user=owner)
        assert membership.role == Role.OWNER

    def test_demoting_one_of_two_owners_succeeds(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()
        second_owner = make_user()
        make_membership(organization=org, user=second_owner, role=Role.OWNER)

        membership = services.change_member_role(organization=org, target_user_id=owner.id, new_role=Role.EDITOR)

        assert membership.role == Role.EDITOR


@pytest.mark.django_db
class TestRemoveMember:
    def test_owner_removes_another_member(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()

        services.remove_member(organization=org, target_user_id=editor.id)

        assert not Membership.all_objects.filter(organization=org, user=editor).exists()

    def test_self_removal_by_non_owner(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()

        services.remove_member(organization=org, target_user_id=viewer.id)

        assert not Membership.all_objects.filter(organization=org, user=viewer).exists()

    def test_removing_sole_owner_fails(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()

        with pytest.raises(LastOwnerError):
            services.remove_member(organization=org, target_user_id=owner.id)

        assert Membership.all_objects.filter(organization=org, user=owner).exists()


@pytest.mark.django_db
class TestListMemberships:
    def test_lists_only_this_organizations_memberships(self):
        org, owner, editor, viewer, outsider = make_org_with_roles()
        other_org = make_organization()

        result = list(services.list_memberships(organization=org))

        assert {m.user_id for m in result} == {owner.id, editor.id, viewer.id}
