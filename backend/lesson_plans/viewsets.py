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

from django.http import HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response

from lesson_plans.core.render.docx import render_docx
from lesson_plans.core.render.markdown import render_md
from lesson_plans.core.schema import Proyecto
from lesson_plans.models import LessonPlan
from lesson_plans.serializers import LessonPlanSerializer
from lesson_plans.services import delete_lesson_plan, generate_lesson_plan
from workspaces.permissions import WorkspacePermission

CAPABILITY_MAP = {
    "list": "view_workspace",
    "retrieve": "view_workspace",
    "create": "edit_content",
    "destroy": "edit_content",
    "export": "view_workspace",
}

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class _DocxRenderer(BaseRenderer):
    """Registers `format=docx` with DRF's content negotiation (the
    `?format=` query param is also DRF's own format-override switch — see
    `URL_FORMAT_OVERRIDE` — so the export action must expose a renderer for
    every format value it accepts or negotiation raises before the view
    body runs)."""

    media_type = DOCX_CONTENT_TYPE
    format = "docx"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class _MarkdownRenderer(BaseRenderer):
    media_type = "text/markdown"
    format = "md"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="format",
                type=OpenApiTypes.STR,
                enum=["docx", "md"],
                required=False,
                description="Export format; defaults to docx.",
            )
        ],
        responses={200: OpenApiTypes.BINARY},
    )
    @action(
        detail=True,
        methods=["get"],
        renderer_classes=[_DocxRenderer, _MarkdownRenderer],
    )
    def export(self, request, pk=None):
        """GET /api/lesson-plans/<id>/export?format=docx|md (ai-planeaciones
        spec — "Ready LessonPlan Can Be Exported as Docx or Markdown").

        Only a `ready` plan may be exported; `pending`/`failed` are rejected
        (no partial/empty document is ever returned).
        """
        plan = self.get_object()
        if plan.status != LessonPlan.Status.READY:
            raise ValidationError("Only a ready LessonPlan can be exported.")

        proyecto = Proyecto.model_validate(plan.proyecto)
        export_format = request.query_params.get("format", "docx")

        if export_format == "md":
            body = render_md(proyecto)
            return HttpResponse(body, content_type="text/markdown; charset=utf-8")

        if export_format != "docx":
            raise ValidationError(f"Unsupported export format: {export_format!r}")

        buffer = render_docx(proyecto)
        response = HttpResponse(buffer.getvalue(), content_type=DOCX_CONTENT_TYPE)
        filename = f"{plan.title or plan.theme}.docx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
