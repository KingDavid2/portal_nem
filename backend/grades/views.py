"""Grades activities list/create, score matrix, and bulk upsert API views."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
)
from rest_framework.views import APIView

from grades.models import Activity, Term
from grades.serializers import (
    ActivitiesListQuerySerializer,
    ActivitiesListResponseSerializer,
    ActivityCreateSerializer,
    ActivitySerializer,
    ScoresBulkRequestSerializer,
    ScoresBulkResponseSerializer,
    ScoresMatrixQuerySerializer,
    ScoresMatrixResponseSerializer,
)
from grades.services import (
    bulk_upsert_scores,
    create_activity,
    ensure_terms,
    get_score_matrix,
    list_activities,
)
from schools.models import Group
from students.models import Student
from workspaces.permissions import WorkspacePermission


def _terms_payload(terms: list[Term]) -> list[dict]:
    return [{"id": term.pk, "number": term.number} for term in terms]


def _resolve_group_and_term(
    *, group_id: int, term_id: int
) -> tuple[Group, Term, list[Term]] | Response:
    """Load group + ensure terms; return 404 Response when either is missing."""
    group = Group.objects.filter(pk=group_id).first()
    if group is None:
        return Response({"detail": "Not found."}, status=HTTP_404_NOT_FOUND)

    terms = ensure_terms(school_year=group.school_year)
    term = next((t for t in terms if t.pk == term_id), None)
    if term is None:
        return Response({"detail": "Not found."}, status=HTTP_404_NOT_FOUND)
    return group, term, terms


class ActivitiesView(APIView):
    """GET/POST /api/grades/activities/."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {
        "list": "view_workspace",
        "create": "edit_content",
    }

    def initial(self, request, *args, **kwargs):
        self.action = "list" if request.method.upper() == "GET" else "create"
        super().initial(request, *args, **kwargs)

    @extend_schema(
        parameters=[ActivitiesListQuerySerializer],
        responses={200: ActivitiesListResponseSerializer},
    )
    def get(self, request):
        query = ActivitiesListQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response(query.errors, status=HTTP_400_BAD_REQUEST)

        resolved = _resolve_group_and_term(
            group_id=query.validated_data["group"],
            term_id=query.validated_data["term"],
        )
        if isinstance(resolved, Response):
            return resolved
        group, term, terms = resolved

        try:
            result = list_activities(
                membership=request.membership,
                group=group,
                term=term,
                field=query.validated_data.get("field"),
                subject=query.validated_data.get("subject"),
                type=query.validated_data.get("type"),
                q=query.validated_data.get("q"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response(
            {
                "terms": _terms_payload(terms),
                "activities": ActivitySerializer(result["activities"], many=True).data,
                "stats": result["stats"],
            }
        )

    @extend_schema(
        request=ActivityCreateSerializer,
        responses={201: ActivitySerializer},
    )
    def post(self, request):
        serializer = ActivityCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        resolved = _resolve_group_and_term(
            group_id=data["group"], term_id=data["term"]
        )
        if isinstance(resolved, Response):
            return resolved
        group, term, _terms = resolved

        try:
            activity = create_activity(
                membership=request.membership,
                group=group,
                term=term,
                title=data["title"],
                activity_type=data["type"],
                due_date=data["due_date"],
                formative_field_id=data["field"],
                subject_ids=data["subject_ids"],
                description=data.get("description", ""),
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response(ActivitySerializer(activity).data, status=HTTP_201_CREATED)


class ScoresMatrixView(APIView):
    """GET /api/grades/scores/matrix/."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {"matrix": "view_workspace"}
    action = "matrix"

    @extend_schema(
        parameters=[ScoresMatrixQuerySerializer],
        responses={200: ScoresMatrixResponseSerializer},
    )
    def get(self, request):
        query = ScoresMatrixQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response(query.errors, status=HTTP_400_BAD_REQUEST)

        resolved = _resolve_group_and_term(
            group_id=query.validated_data["group"],
            term_id=query.validated_data["term"],
        )
        if isinstance(resolved, Response):
            return resolved
        group, term, terms = resolved

        try:
            result = get_score_matrix(
                membership=request.membership,
                group=group,
                term=term,
                field=query.validated_data.get("field"),
                subject=query.validated_data.get("subject"),
                type=query.validated_data.get("type"),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response(
            {
                "terms": _terms_payload(terms),
                "students": [
                    {
                        "id": student.pk,
                        "first_name": student.first_name,
                        "last_name_paternal": student.last_name_paternal,
                    }
                    for student in result["students"]
                ],
                "activities": ActivitySerializer(
                    result["activities"], many=True
                ).data,
                "scores": [
                    {
                        "student": cell["student_id"],
                        "activity": cell["activity_id"],
                        "score": cell["score"],
                    }
                    for cell in result["scores"]
                ],
            }
        )


class ScoresBulkView(APIView):
    """PUT /api/grades/scores/bulk/."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {"bulk": "edit_content"}
    action = "bulk"

    @extend_schema(
        request=ScoresBulkRequestSerializer,
        responses={200: ScoresBulkResponseSerializer},
    )
    def put(self, request):
        serializer = ScoresBulkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        group = Group.objects.filter(pk=serializer.validated_data["group"]).first()
        if group is None:
            return Response({"detail": "Not found."}, status=HTTP_404_NOT_FOUND)

        entries_data = serializer.validated_data["entries"]
        student_ids = [entry["student"] for entry in entries_data]
        activity_ids = [entry["activity"] for entry in entries_data]

        students_by_id = {
            student.pk: student
            for student in Student.objects.filter(pk__in=student_ids)
        }
        activities_by_id = {
            activity.pk: activity
            for activity in Activity.objects.filter(pk__in=activity_ids)
        }

        if len(students_by_id) != len(set(student_ids)):
            return Response(
                {"detail": "Student does not belong to the supplied group."},
                status=HTTP_400_BAD_REQUEST,
            )
        if len(activities_by_id) != len(set(activity_ids)):
            return Response(
                {"detail": "Activity does not belong to the supplied group."},
                status=HTTP_400_BAD_REQUEST,
            )

        entries = [
            {
                "student": students_by_id[entry["student"]],
                "activity": activities_by_id[entry["activity"]],
                "score": entry.get("score"),
            }
            for entry in entries_data
        ]

        try:
            bulk_upsert_scores(
                membership=request.membership,
                group=group,
                entries=entries,
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response({"saved": len(entries)})
