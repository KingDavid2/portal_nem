"""RED tests for TenancyMiddleware (design D-2/D-3, tenancy-isolation spec)."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

pytestmark = pytest.mark.django_db

User = get_user_model()


class _ContextProbe(APIView):
    """Echoes the resolved active-workspace context + the raw DB setting."""

    permission_classes = [AllowAny]

    def get(self, request):
        from workspaces.context import WORKSPACE_UNSET, active_workspace

        workspace_id = active_workspace.get()
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_setting('app.workspace_id', true)")
            (db_setting,) = cursor.fetchone()

        return Response(
            {
                "context_set": workspace_id is not WORKSPACE_UNSET,
                "context_value": (
                    str(workspace_id) if workspace_id is not WORKSPACE_UNSET else None
                ),
                "db_setting": db_setting,
            }
        )


urlpatterns = [path("probe/", _ContextProbe.as_view())]


@pytest.fixture(autouse=True)
def _urlconf(settings):
    settings.ROOT_URLCONF = __name__


@pytest.fixture
def user_with_personal_and_group_workspace():
    from workspaces.models import Membership, Workspace

    user = User.objects.create_user(
        email="teacher@example.com", password="s3cret-pass"
    )
    personal = Workspace.objects.create(type=Workspace.Type.PERSONAL)
    Membership.objects.create(
        user=user, workspace=personal, role=Membership.Role.OWNER
    )
    group = Workspace.objects.create(type=Workspace.Type.GROUP)
    Membership.objects.create(user=user, workspace=group, role=Membership.Role.MEMBER)
    return user, personal, group


def test_header_resolves_membership_and_sets_that_workspace(
    client: Client, user_with_personal_and_group_workspace
):
    user, _personal, group = user_with_personal_and_group_workspace
    client.force_login(user)

    response = client.get("/probe/", HTTP_X_WORKSPACE_ID=str(group.id))

    assert response.status_code == 200
    assert response.data["context_set"] is True
    assert response.data["context_value"] == str(group.id)


def test_missing_header_falls_back_to_personal_workspace(
    client: Client, user_with_personal_and_group_workspace
):
    user, personal, _group = user_with_personal_and_group_workspace
    client.force_login(user)

    response = client.get("/probe/")

    assert response.status_code == 200
    assert response.data["context_value"] == str(personal.id)


def test_header_present_but_not_member_returns_403(
    client: Client, user_with_personal_and_group_workspace
):
    user, _personal, _group = user_with_personal_and_group_workspace
    client.force_login(user)

    foreign_workspace_id = uuid.uuid4()
    response = client.get("/probe/", HTTP_X_WORKSPACE_ID=str(foreign_workspace_id))

    assert response.status_code == 403


def test_unauthenticated_request_has_no_context_set(client: Client):
    response = client.get("/probe/")

    assert response.status_code == 200
    assert response.data["context_set"] is False


def test_set_local_is_issued_inside_the_request_transaction(
    client: Client, user_with_personal_and_group_workspace
):
    user, _personal, group = user_with_personal_and_group_workspace
    client.force_login(user)

    response = client.get("/probe/", HTTP_X_WORKSPACE_ID=str(group.id))

    assert response.data["db_setting"] == str(group.id)


@pytest.mark.django_db(transaction=True)
def test_set_local_does_not_persist_past_the_request_transaction(
    client: Client, user_with_personal_and_group_workspace
):
    user, _personal, group = user_with_personal_and_group_workspace
    client.force_login(user)

    client.get("/probe/", HTTP_X_WORKSPACE_ID=str(group.id))

    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.workspace_id', true)")
        (leftover,) = cursor.fetchone()

    assert leftover in (None, "")
