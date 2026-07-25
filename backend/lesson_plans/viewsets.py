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

from dataclasses import asdict

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer
from rest_framework.response import Response

from lesson_plans.core.render.docx import render_docx
from lesson_plans.core.render.markdown import render_md
from lesson_plans.core.catalog import (
    CROSS_CUTTING_THEMES,
    FIELDS,
    METHODOLOGIES,
    PHASE,
    official_content_for,
    pda_by_id,
    subjects_for,
)
from lesson_plans.core.schema import Proyecto
from lesson_plans.models import LessonPlan
from lesson_plans.serializers import (
    CatalogFieldSerializer,
    GenerationQuotaSerializer,
    LessonPlanCatalogSerializer,
    LessonPlanCreateSerializer,
    LessonPlanSerializer,
)
from lesson_plans.quota import (
    QuotaExceeded,
    current_period,
    current_usage,
    format_period,
)
from lesson_plans.services import delete_lesson_plan, generate_lesson_plan
from lesson_plans.validation import require_secondary_group, resolve_field
from schools.models import Group
from workspaces.permissions import WorkspacePermission

CAPABILITY_MAP = {
    "list": "view_workspace",
    "retrieve": "view_workspace",
    "create": "edit_content",
    "catalog": "view_workspace",
    "formative_fields": "view_workspace",
    # Reading your own allowance is not an editing action, so it stays on
    # `view_workspace` even though the counter it reports is only ever moved
    # by `create` (`edit_content`).
    "quota": "view_workspace",
    "destroy": "edit_content",
    "export": "view_workspace",
}

DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


class GenerationQuotaExceeded(APIException):
    """HTTP shape of `quota.QuotaExceeded` (429 + the counters the UI shows).

    A plain `APIException` subclass rather than DRF's `Throttled`: `Throttled`
    models a rate limit that clears after `wait` seconds and makes the handler
    emit a `Retry-After` header. This is a monthly allowance, not a rate — the
    only honest `Retry-After` would be "the rest of the month", and clients
    treating it as a backoff hint would poll pointlessly. The service layer
    raises the framework-free `QuotaExceeded`; only this boundary knows 429.
    """

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "generation_quota_exceeded"

    def __init__(self, exceeded: QuotaExceeded) -> None:
        super().__init__(detail="Monthly generation limit reached.")
        # Assigned after `super().__init__` on purpose: `APIException` runs
        # every detail value through `ErrorDetail(str(value))`, which would
        # ship `used`/`limit` as JSON strings. The counters feed a numeric
        # progress indicator, so they must stay integers on the wire.
        self.detail = {
            "detail": "Monthly generation limit reached.",
            "code": self.default_code,
            "used": exceeded.used,
            "limit": exceeded.limit,
            "period": format_period(exceeded.period),
        }


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

    def get_serializer_class(self):
        if self.action == "create":
            return LessonPlanCreateSerializer
        return LessonPlanSerializer

    @extend_schema(
        request=LessonPlanCreateSerializer,
        responses={202: LessonPlanSerializer, 429: OpenApiTypes.OBJECT},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            plan = generate_lesson_plan(
                membership=request.membership, **serializer.validated_data
            )
        except QuotaExceeded as exceeded:
            raise GenerationQuotaExceeded(exceeded) from exceeded
        output = LessonPlanSerializer(plan)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_202_ACCEPTED, headers=headers)

    def perform_destroy(self, instance):
        delete_lesson_plan(membership=self.request.membership, lesson_plan=instance)

    @extend_schema(responses=CatalogFieldSerializer(many=True))
    @action(detail=False, methods=["get"], url_path="fields")
    def formative_fields(self, request):
        """GET /api/lesson-plans/fields/ — every formative field of the
        curriculum, in catalog order.

        Deliberately not folded into `catalog`: `catalog` needs a field id to
        answer, and the picker that supplies it has to be rendered first. Every
        field is listed, including the two with no verified content yet — the
        form keeps them selectable behind an empty state rather than pretending
        they do not exist.

        Named `formative_fields` with an explicit `url_path` so the method does
        not shadow anything named `fields` on the view.
        """
        return Response(CatalogFieldSerializer(FIELDS, many=True).data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="group",
                type=OpenApiTypes.INT,
                required=True,
                description="Id of the secondary-school group being planned for.",
            ),
            OpenApiParameter(
                name="field",
                type=OpenApiTypes.STR,
                required=True,
                description="Id of the formative field whose catalog is requested.",
            ),
        ],
        responses=LessonPlanCatalogSerializer,
    )
    @action(detail=False, methods=["get"])
    def catalog(self, request):
        group_value = request.query_params.get("group")
        field_id = request.query_params.get("field")
        errors = {}
        try:
            group_id = int(group_value)
        except (TypeError, ValueError):
            errors["group"] = "A valid group id is required."
        if not field_id:
            errors["field"] = "A field id is required."
        if errors:
            raise ValidationError(errors)

        field = resolve_field(field_id, error_key="field")

        group = get_object_or_404(
            Group.objects.select_related("school_year__school"),
            pk=group_id,
        )
        require_secondary_group(group, error_key="group")

        contents = []
        for content in official_content_for(field.id):
            contents.append(
                {
                    "id": content.id,
                    "text": content.text,
                    "pdas": [
                        {
                            "id": pda_id,
                            "text": pda_by_id(field.id, pda_id).text,
                        }
                        for pda_id in content.pda_ids
                    ],
                }
            )
        school = group.school_year.school
        payload = {
            "phase": PHASE,
            "grade": group.grado,
            "field": {"id": field.id, "name": field.name},
            "methodology": asdict(METHODOLOGIES[0]),
            "subjects": [asdict(subject) for subject in subjects_for(field.id)],
            "cross_cutting_themes": [asdict(theme) for theme in CROSS_CUTTING_THEMES],
            "contents": contents,
            "group": {
                "id": group.pk,
                "label": f"{group.grado}° {group.grupo}",
                "grade": group.grado,
                "school_name": school.name,
                "school_cct": school.cct,
                "school_year_label": group.school_year.label,
            },
            "teacher": {"email": request.user.email},
        }
        return Response(LessonPlanCatalogSerializer(payload).data)

    @extend_schema(responses=GenerationQuotaSerializer)
    @action(detail=False, methods=["get"])
    def quota(self, request):
        """GET /api/lesson-plans/quota/ — the monthly allowance of the active
        workspace ("Generaciones de este mes").

        Deliberately not folded into `catalog`: the card is rendered before
        the teacher has picked a group or a field, and `catalog` requires
        both. Reading is side-effect free — `current_usage` reports an absent
        ledger row as `0` instead of seeding one, so merely opening the form
        never writes.
        """
        used, limit = current_usage(request.membership.workspace)
        payload = {
            "period": format_period(current_period()),
            "used": used,
            "limit": limit,
            # Floored: a limit lowered below what a workspace already spent
            # would otherwise report a negative countdown.
            "remaining": max(limit - used, 0),
        }
        return Response(GenerationQuotaSerializer(payload).data)

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
