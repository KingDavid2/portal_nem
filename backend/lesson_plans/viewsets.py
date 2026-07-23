"""DRF viewset for LessonPlan (ai-planeaciones spec — CRUD Endpoints Are
Workspace-Scoped; Generation Runs Asynchronously via a Celery Task).

Reads rely on `LessonPlan.objects.all()` — the `ScopedManager` filters by the
active-workspace context set by `TenancyMiddleware`, so cross-workspace rows
are invisible/404 without any explicit filtering here (same pattern as
`schools/viewsets.py`/`students/viewsets.py`). `create` delegates to
`services.generate_lesson_plan`, which creates the `pending` row and enqueues
the Celery task — the sole place authorization + the `workspace ==
group.workspace` invariant are enforced. `list` additionally supports a
`?group=<id>` filter (design Interfaces — "list -> view_workspace (?group=
filter)").
"""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from lesson_plans.models import LessonPlan
from lesson_plans.serializers import LessonPlanSerializer
from lesson_plans.services import delete_lesson_plan, generate_lesson_plan
from workspaces.permissions import WorkspacePermission

CAPABILITY_MAP = {
    "list": "view_workspace",
    "retrieve": "view_workspace",
    "create": "edit_content",
    "destroy": "edit_content",
}


class LessonPlanViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "delete", "head", "options"]
    serializer_class = LessonPlanSerializer
    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = CAPABILITY_MAP

    def get_queryset(self):
        queryset = LessonPlan.objects.all()
        group_id = self.request.query_params.get("group")
        if group_id is not None:
            queryset = queryset.filter(group_id=group_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = generate_lesson_plan(
            membership=request.membership, **serializer.validated_data
        )
        output = self.get_serializer(plan)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_202_ACCEPTED, headers=headers)

    def perform_destroy(self, instance):
        delete_lesson_plan(membership=self.request.membership, lesson_plan=instance)
