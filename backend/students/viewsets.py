"""DRF viewset for Student (school-structure spec — DRF CRUD Endpoints Are
Workspace-Scoped and Isolated). Same shape as `schools/viewsets.py`.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from students.models import Student
from students.serializers import StudentSerializer
from students.services import create_student, delete_student, update_student
from workspaces.permissions import WorkspacePermission

CAPABILITY_MAP = {
    "list": "view_workspace",
    "retrieve": "view_workspace",
    "create": "edit_content",
    "update": "edit_content",
    "partial_update": "edit_content",
    "destroy": "edit_content",
}


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = [IsAuthenticated, WorkspacePermission]
    capability_map = CAPABILITY_MAP

    def get_queryset(self):
        return Student.objects.all()

    def perform_create(self, serializer):
        serializer.instance = create_student(
            membership=self.request.membership, **serializer.validated_data
        )

    def perform_update(self, serializer):
        update_student(
            membership=self.request.membership,
            student=serializer.instance,
            **serializer.validated_data,
        )

    def perform_destroy(self, instance):
        delete_student(membership=self.request.membership, student=instance)
