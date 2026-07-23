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
inside an explicit `transaction.atomic()` block so `SET LOCAL
app.workspace_id` (issued via `set_config(..., true)`) is scoped to exactly
that transaction — it is cleared automatically when the transaction commits
or rolls back, so it can never leak into a subsequent request that reuses
the same pooled connection.
"""

import uuid

from django.contrib.auth.models import AnonymousUser
from django.db import connection, transaction
from django.http import JsonResponse

from workspaces.context import active_workspace
from workspaces.models import Membership, Workspace

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

        token = active_workspace.set(workspace_id)
        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT set_config('app.workspace_id', %s, %s)",
                        [str(workspace_id), True],
                    )
                response = self.get_response(request)
        finally:
            active_workspace.reset(token)
        return response
