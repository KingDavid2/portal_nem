"""Tests for the provisioning base class and TeacherMinimal persona.

Validates that provisioning creates a real tenant (User + Workspace +
owner Membership) through the same atomic path as `provision_signup`,
seeds data inside the workspace scope so RLS applies, and produces
unique emails per call to prevent collisions across demo sessions.
"""

from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model

import pytest

from schools.models import Group, School, SchoolYear
from workspaces.models import Membership, Workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db

User = get_user_model()


def test_provision_returns_persisted_user_workspace_and_owner_membership():
    """provision() creates a real User, Workspace, and owner Membership."""
    from demo.provisioning.base import DemoProvisioner

    class _Concrete(DemoProvisioner):
        persona_key = "test_provisioner"

    user, workspace = _Concrete().provision()

    # User is persisted (not just in-memory):
    assert User.objects.filter(pk=user.pk).exists()
    # Workspace is persisted:
    assert Workspace.objects.filter(pk=workspace.pk).exists()
    # An owner Membership links them:
    membership = Membership.objects.get(user=user, workspace=workspace)
    assert membership.role == Membership.Role.OWNER


def test_two_provisions_produce_different_emails():
    """Each provision() call generates a unique email — no collision."""
    from demo.provisioning.teacher_minimal import TeacherMinimal

    user_a, _ = TeacherMinimal().provision()
    user_b, _ = TeacherMinimal().provision()

    assert user_a.email != user_b.email
    assert user_a.pk != user_b.pk


def test_provisioned_user_authenticates_with_demo_password():
    """The provisioned user can log in with DEMO_PASSWORD."""
    from demo.provisioning.base import DEMO_PASSWORD
    from demo.provisioning.teacher_minimal import TeacherMinimal

    user, _ = TeacherMinimal().provision()

    assert user.check_password(DEMO_PASSWORD)
    # authenticate() returns a freshly-loaded instance, so assert non-None:
    assert authenticate(username=user.email, password=DEMO_PASSWORD) is not None


def test_teacher_minimal_seeds_one_school_year_and_group():
    """TeacherMinimal seeds exactly one school, one school year, one group —
    all owned by the provisioned workspace.

    The workspace_id assertions are the tenancy guarantee: if seeding
    bypassed workspace_scope or the services layer, rows would lack the
    correct workspace reference and leak across tenants.

    Read-back must happen inside ``workspace_scope`` because ScopedManager
    filters by the active workspace context — this is the same pattern
    the app uses for every scoped query.
    """
    from demo.provisioning.teacher_minimal import TeacherMinimal

    user, workspace = TeacherMinimal().provision()

    with workspace_scope(workspace.id):
        schools = School.objects.all()
        assert schools.count() == 1

        school = schools.first()
        assert school.workspace_id == workspace.id

        years = SchoolYear.objects.filter(school=school)
        assert years.count() == 1

        year = years.first()
        assert year.workspace_id == workspace.id

        groups = Group.objects.filter(school_year=year)
        assert groups.count() == 1

        group = groups.first()
        assert group.workspace_id == workspace.id


def test_base_provisioner_creates_no_schools():
    """A bare DemoProvisioner subclass (no seed override) creates zero schools."""
    from demo.provisioning.base import DemoProvisioner

    class _Bare(DemoProvisioner):
        persona_key = "bare_test"

    _, workspace = _Bare().provision()

    with workspace_scope(workspace.id):
        assert School.objects.count() == 0