"""Attendance roster read and bulk upsert API views."""

from __future__ import annotations

from django.core.exceptions import ValidationError
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from rest_framework.views import APIView

from attendance.serializers import (
    AttendanceBulkRequestSerializer,
    AttendanceBulkResponseSerializer,
    AttendanceRosterEntrySerializer,
    AttendanceRosterQuerySerializer,
    AttendanceWeekBulkRequestSerializer,
    AttendanceWeekQuerySerializer,
    AttendanceWeekResponseSerializer,
)
from attendance.services import bulk_upsert, bulk_upsert_week, get_roster, get_week_roster
from schools.models import Group
from students.models import Student
from workspaces.permissions import WorkspacePermission


class AttendanceRosterView(APIView):
    """GET /api/attendance/roster/ — full group roster merged with saved rows."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {"roster": "view_workspace"}
    action = "roster"

    @extend_schema(
        parameters=[AttendanceRosterQuerySerializer],
        responses={200: AttendanceRosterEntrySerializer(many=True)},
    )
    def get(self, request):
        query = AttendanceRosterQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response(query.errors, status=HTTP_400_BAD_REQUEST)

        group = Group.objects.filter(pk=query.validated_data["group"]).first()
        if group is None:
            return Response({"detail": "Not found."}, status=HTTP_404_NOT_FOUND)
        date = query.validated_data["date"]

        try:
            roster = get_roster(membership=request.membership, group=group, date=date)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response(AttendanceRosterEntrySerializer(roster, many=True).data)


class AttendanceBulkView(APIView):
    """PUT /api/attendance/bulk/ — atomic upsert for one group+date."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {"bulk": "edit_content"}
    action = "bulk"

    @extend_schema(
        request=AttendanceBulkRequestSerializer,
        responses={200: AttendanceBulkResponseSerializer},
    )
    def put(self, request):
        serializer = AttendanceBulkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        group = Group.objects.filter(pk=serializer.validated_data["group"]).first()
        if group is None:
            return Response({"detail": "Not found."}, status=HTTP_404_NOT_FOUND)
        date = serializer.validated_data["date"]
        entries_data = serializer.validated_data["entries"]

        student_ids = [entry["student"] for entry in entries_data]
        students_by_id = {
            student.pk: student
            for student in Student.objects.filter(pk__in=student_ids)
        }
        if len(students_by_id) != len(set(student_ids)):
            return Response(
                {"detail": "Student does not belong to the supplied group."},
                status=HTTP_400_BAD_REQUEST,
            )

        entries = [
            {
                "student": students_by_id[entry["student"]],
                "status": entry["status"],
                "notes": entry.get("notes", ""),
            }
            for entry in entries_data
        ]

        try:
            bulk_upsert(
                membership=request.membership,
                group=group,
                date=date,
                entries=entries,
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response({"saved": len(entries)})


class AttendanceWeekView(APIView):
    """GET /api/attendance/week/ — Mon–Fri matrix for one group."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {"week": "view_workspace"}
    action = "week"

    @extend_schema(
        parameters=[AttendanceWeekQuerySerializer],
        responses={200: AttendanceWeekResponseSerializer},
    )
    def get(self, request):
        query = AttendanceWeekQuerySerializer(data=request.query_params)
        if not query.is_valid():
            return Response(query.errors, status=HTTP_400_BAD_REQUEST)

        group = Group.objects.filter(pk=query.validated_data["group"]).first()
        if group is None:
            return Response({"detail": "Not found."}, status=HTTP_404_NOT_FOUND)
        week_start = query.validated_data["week_start"]

        try:
            matrix = get_week_roster(
                membership=request.membership, group=group, week_start=week_start
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response(AttendanceWeekResponseSerializer(matrix).data)


class AttendanceWeekBulkView(APIView):
    """PUT /api/attendance/week/bulk/ — atomic status upsert for Mon–Fri; notes preserved."""

    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = {"week_bulk": "edit_content"}
    action = "week_bulk"

    @extend_schema(
        request=AttendanceWeekBulkRequestSerializer,
        responses={200: AttendanceBulkResponseSerializer},
    )
    def put(self, request):
        serializer = AttendanceWeekBulkRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

        group = Group.objects.filter(pk=serializer.validated_data["group"]).first()
        if group is None:
            return Response({"detail": "Not found."}, status=HTTP_404_NOT_FOUND)
        week_start = serializer.validated_data["week_start"]
        entries_data = serializer.validated_data["entries"]

        student_ids = [entry["student"] for entry in entries_data]
        students_by_id = {
            student.pk: student
            for student in Student.objects.filter(pk__in=student_ids)
        }
        if len(students_by_id) != len(set(student_ids)):
            return Response(
                {"detail": "Student does not belong to the supplied group."},
                status=HTTP_400_BAD_REQUEST,
            )

        entries = [
            {
                "student": students_by_id[entry["student"]],
                "date": entry["date"],
                "status": entry["status"],
            }
            for entry in entries_data
        ]

        try:
            bulk_upsert_week(
                membership=request.membership,
                group=group,
                week_start=week_start,
                entries=entries,
            )
        except ValidationError as exc:
            return Response(exc.message_dict, status=HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=HTTP_400_BAD_REQUEST)

        return Response({"saved": len(entries)})
