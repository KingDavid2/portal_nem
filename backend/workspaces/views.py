"""Workspace-list view (workspaces spec — "Workspace-List Endpoint Returns
Only the Caller's Memberships"; tenancy-isolation spec — "Workspace-List
Read Exposes Only the Caller's Own Membership Rows").

Deliberately reads `Membership` via the DEFAULT manager (RLS-excluded, same
as `WorkspaceInvitation`/`WorkspaceHistory`) rather than `ScopedManager`: a
caller listing their own memberships necessarily spans multiple workspaces
in one query, which no single-workspace `ScopedManager`/RLS scope could
satisfy. Explicitly filtered to `user=request.user` here instead — no
`WorkspacePermission`/`capability_map`, no `X-Workspace-Id` requirement.
"""

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from workspaces.models import Membership
from workspaces.serializers import MembershipListSerializer


class WorkspaceListView(ListAPIView):
    serializer_class = MembershipListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Membership.objects.filter(user=self.request.user).select_related(
            "workspace"
        )
