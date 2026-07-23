"""TenancyMiddleware (design D-2/D-3, tenancy-isolation spec).

Resolves the active workspace for the request from the `X-Workspace-Id`
header against the authenticated user's memberships:

- Header present, user is a member -> that workspace.
- Header missing -> fall back to the user's personal workspace.
- Header present, user is NOT a member -> 403 (never a silent fallback when
  a workspace is explicitly named).
- Unauthenticated -> no context set; the `ScopedManager` sentinel denies all
  scoped rows downstream.

While a workspace is resolved, the remaining request/response cycle runs
inside `workspaces.scope.workspace_scope()` (design Decision: "Shared
workspace-scope helper reused by middleware and task"), which opens its own
`transaction.atomic()` block so `SET LOCAL app.workspace_id` (issued via
`set_config(..., true)`) is scoped to exactly that transaction — it is
cleared automatically when the transaction commits or rolls back, so it can
never leak into a subsequent request that reuses the same pooled connection.
"""

import uuid

from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse

from workspaces.models import Membership, Workspace
from workspaces.scope import workspace_scope

WORKSPACE_HEADER = "HTTP_X_WORKSPACE_ID"


class TenancyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is None or isinstance(user, AnonymousUser) or not user.is_authenticated:
            return self.get_response(request)

        header_value = request.META.get(WORKSPACE_HEADER)
        if header_value:
            try:
                workspace_id = uuid.UUID(header_value)
            except ValueError:
                return JsonResponse(
                    {"detail": "Invalid X-Workspace-Id header."}, status=403
                )
            membership = Membership.objects.filter(
                user=user, workspace_id=workspace_id
            ).first()
            if membership is None:
                return JsonResponse(
                    {"detail": "Not a member of this workspace."}, status=403
                )
        else:
            membership = (
                Membership.objects.filter(
                    user=user, workspace__type=Workspace.Type.PERSONAL
                )
                .order_by("created_at")
                .first()
            )
            if membership is None:
                return JsonResponse(
                    {"detail": "No personal workspace found for this user."},
                    status=403,
                )
            workspace_id = membership.workspace_id

        request.membership = membership

        with workspace_scope(workspace_id):
            response = self.get_response(request)
        return response
