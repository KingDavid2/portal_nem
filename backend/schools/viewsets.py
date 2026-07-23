"""DRF viewsets for School / SchoolYear / Group (school-structure spec — DRF
CRUD Endpoints Are Workspace-Scoped and Isolated; PROTECT Surfaces a Clean
4xx on Group Delete With Students).

Reads rely on `Model.objects.all()` — the `ScopedManager` on every
`ScopedModel` filters by the active-workspace context set by
`TenancyMiddleware`, so cross-workspace rows are invisible/404 without any
explicit filtering here. Writes delegate to the services layer, which is
the sole place authorization + cross-entity workspace-consistency checks
live.
"""

from django.db.models import ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from schools.models import Group, School, SchoolYear
from schools.serializers import GroupSerializer, SchoolSerializer, SchoolYearSerializer
from schools.services import (
    create_group,
    create_school,
    create_school_year,
    delete_group,
    delete_school,
    delete_school_year,
    update_group,
    update_school,
    update_school_year,
)
from workspaces.permissions import WorkspacePermission

CAPABILITY_MAP = {
    "list": "view_workspace",
    "retrieve": "view_workspace",
    "create": "edit_content",
    "update": "edit_content",
    "partial_update": "edit_content",
    "destroy": "edit_content",
}


class SchoolViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolSerializer
    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = CAPABILITY_MAP

    def get_queryset(self):
        return School.objects.all()

    def perform_create(self, serializer):
        serializer.instance = create_school(
            membership=self.request.membership, **serializer.validated_data
        )

    def perform_update(self, serializer):
        update_school(
            membership=self.request.membership,
            school=serializer.instance,
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_school(membership=self.request.membership, school=instance)


class SchoolYearViewSet(viewsets.ModelViewSet):
    serializer_class = SchoolYearSerializer
    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = CAPABILITY_MAP

    def get_queryset(self):
        return SchoolYear.objects.all()

    def perform_create(self, serializer):
        serializer.instance = create_school_year(
            membership=self.request.membership, **serializer.validated_data
        )

    def perform_update(self, serializer):
        update_school_year(
            membership=self.request.membership,
            school_year=serializer.instance,
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_school_year(membership=self.request.membership, school_year=instance)


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = CAPABILITY_MAP

    def get_queryset(self):
        return Group.objects.all()

    def perform_create(self, serializer):
        serializer.instance = create_group(
            membership=self.request.membership, **serializer.validated_data
        )

    def perform_update(self, serializer):
        update_group(
            membership=self.request.membership,
            group=serializer.instance,
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        try:
            delete_group(membership=self.request.membership, group=instance)
        except ProtectedError:
            raise ValidationError(
                "Cannot delete a group that still has students assigned to it."
            )
