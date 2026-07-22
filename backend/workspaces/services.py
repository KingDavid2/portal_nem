"""Signup provisioning (workspaces spec — Transactional Signup Provisioning).

A single atomic transaction creates the new User, a personal Workspace for
them, and an owner Membership linking the two. Any failure mid-transaction
(e.g. a duplicate email) rolls back every record created in this attempt —
no orphaned User, Workspace, or Membership is left behind.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from workspaces.models import Membership, Workspace

User = get_user_model()


def provision_signup(*, email: str, password: str) -> "User":
    """Create a User, personal Workspace, and owner Membership atomically."""
    with transaction.atomic():
        workspace = Workspace.objects.create(type=Workspace.Type.PERSONAL)
        user = User.objects.create_user(email=email, password=password)
        Membership.objects.create(
            user=user, workspace=workspace, role=Membership.Role.OWNER
        )
    return user
