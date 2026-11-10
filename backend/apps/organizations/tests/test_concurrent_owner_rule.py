"""The "at least one OWNER" rule under concurrency, on MongoDB.

PostgreSQL serialised these writers with row locks. MongoDB aborts the one that
loses a write conflict, and `config.transactions.atomic_retrying` re-runs it.
Without the organization being touched, two owners demoting each other at once
both read the other as a remaining OWNER and both succeed, leaving none.
"""

import threading
from unittest import mock

import pytest
from django.db import connection

from apps.organizations import services
from apps.organizations.constants import Role
from apps.organizations.errors import LastOwnerError
from apps.organizations.models import Membership
from apps.organizations.tests.factories import make_membership, make_organization


@pytest.mark.django_db(transaction=True)
def test_two_owners_demoting_each_other_at_once_never_leave_the_organization_without_one():
    organization = make_organization()
    first_owner = organization.memberships.get().user
    second = make_membership(organization=organization, role=Role.OWNER)

    # Hold both transactions inside the rule check until each has read the
    # other as a remaining OWNER. If the rule were not serialised, both would
    # pass it. A thread that cannot reach the barrier (it lost the conflict and
    # is waiting to run again) simply times out and carries on.
    barrier = threading.Barrier(2)
    real_check = services._assert_not_last_owner

    def meeting_point(**kwargs):
        try:
            barrier.wait(timeout=1)
        except threading.BrokenBarrierError:
            pass
        return real_check(**kwargs)

    outcomes: dict[str, object] = {}

    def demote(label: str, target_user_id) -> None:
        try:
            services.change_member_role(
                organization=organization, target_user_id=target_user_id, new_role=Role.VIEWER
            )
            outcomes[label] = "demoted"
        except LastOwnerError:
            outcomes[label] = "refused"
        finally:
            connection.close()

    with mock.patch.object(services, "_assert_not_last_owner", side_effect=meeting_point):
        threads = [
            threading.Thread(target=demote, args=("first_demotes_second", second.user_id)),
            threading.Thread(target=demote, args=("second_demotes_first", first_owner.id)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

    owners = Membership.objects.for_organization(organization).filter(role=Role.OWNER).count()
    assert owners >= 1
    assert sorted(outcomes.values()) == ["demoted", "refused"]
