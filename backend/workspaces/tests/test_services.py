"""RED tests for transactional signup provisioning (workspaces spec)."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_successful_signup_creates_user_workspace_and_owner_membership():
    from workspaces.models import Membership, Workspace
    from workspaces.services import provision_signup

    result = provision_signup(email="new.teacher@example.com", password="s3cret-pass")
    user = result.user

    assert User.objects.filter(pk=user.pk).exists()
    assert result.pending_invites == []

    workspace = Workspace.objects.get(memberships__user=user)
    assert workspace.type == Workspace.Type.PERSONAL

    membership = Membership.objects.get(user=user, workspace=workspace)
    assert membership.role == Membership.Role.OWNER


def test_failure_during_provisioning_rolls_back_all_records():
    """Forced failure: duplicate email mid-transaction leaves zero rows.

    We pre-create a user with the target email so the internal User.objects
    .create_user(...) call inside provision_signup raises IntegrityError
    (unique email constraint). provision_signup creates the personal
    Workspace *before* the User inside the same atomic block, so this
    failure proves the whole transaction rolls back (including the
    already-created Workspace row) — not just the failing step.
    """
    from workspaces.models import Membership, Workspace
    from workspaces.services import provision_signup

    User.objects.create_user(email="dup@example.com", password="existing-pass")

    workspace_count_before = Workspace.objects.count()
    membership_count_before = Membership.objects.count()
    user_count_before = User.objects.count()

    with pytest.raises(IntegrityError):
        provision_signup(email="dup@example.com", password="another-pass")

    assert User.objects.count() == user_count_before
    assert Workspace.objects.count() == workspace_count_before
    assert Membership.objects.count() == membership_count_before
