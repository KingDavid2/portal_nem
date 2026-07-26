"""Template-method provisioner for demo tenants.

Seeding goes through the existing ``schools/services.py`` and
``students/services.py`` functions (not raw ``.objects.create``) so that
demo data is created by the same code path a real teacher uses. If the
services layer rejects a write — permission denied, workspace mismatch,
invalid parameters — the provision fails fast rather than silently
producing broken demo state. The ``workspace_scope`` context manager
activates RLS for the transaction, so every seeded row is scoped to the
new workspace exactly as it would be during a real request.
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from workspaces.scope import workspace_scope
from workspaces.services import provision_signup

if TYPE_CHECKING:
    from workspaces.models import Membership, Workspace

User = get_user_model()

DEMO_PASSWORD = "DemoPlan2026!"


class DemoProvisioner:
    """Base provisioner — template method that subclasses extend with ``seed``.

    Attributes:
        persona_key: Unique identifier matching the persona registry entry
            (e.g. ``"teacher_minimal"``). Subclasses override this.
    """

    persona_key: str = ""

    def demo_email(self) -> str:
        """Return a unique email address for this provision run.

        The random hex suffix guarantees no collisions when the same
        persona is provisioned twice in quick succession. Mirrors the
        paysys email pattern: ``demo+{key}+{SecureRandom.hex(4)}@example.org``.
        """
        return f"demo+{self.persona_key}+{secrets.token_hex(4)}@example.org"

    def provision(self) -> tuple[User, Workspace]:
        """Provision a real tenant and seed it.

        Steps:
        1. Call ``provision_signup`` to atomically create User + Workspace
           + owner Membership (same path as real signups).
        2. Enter ``workspace_scope`` to activate RLS for the workspace.
        3. Delegate to ``seed`` for persona-specific data.
        4. Return the user and workspace.

        Returns:
            A ``(User, Workspace)`` tuple.
        """
        result = provision_signup(
            email=self.demo_email(), password=DEMO_PASSWORD
        )
        user = result.user
        membership = user.memberships.get()
        workspace = membership.workspace

        with workspace_scope(workspace.id):
            self.seed(membership=membership)

        return user, workspace

    def seed(self, *, membership: Membership) -> None:
        """Subclass hook for persona-specific seeding.

        Override this to create schools, groups, students, etc. Always
        use the services layer (``schools.services``, ``students.services``)
        with the given owner membership — never call ``.objects.create``
        directly on scoped models.

        The base implementation is a no-op: a bare provisioner creates a
        clean workspace with no content.
        """
        pass