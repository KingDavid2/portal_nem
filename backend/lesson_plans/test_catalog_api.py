import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from schools.models import Group, School, SchoolYear
from workspaces.models import Membership, Workspace

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def membership_factory():
    def make(*, role="member", workspace=None):
        workspace = workspace or Workspace.objects.create(type=Workspace.Type.GROUP)
        user = User.objects.create_user(
            email=f"user-{Membership.objects.count()}@example.com",
            password="s3cret-pass",
        )
        return Membership.objects.create(
            user=user,
            workspace=workspace,
            role=role,
        )

    return make


@pytest.fixture
def client_for():
    def make(membership):
        client = APIClient()
        client.force_login(membership.user)
        client.credentials(HTTP_X_WORKSPACE_ID=str(membership.workspace_id))
        return client

    return make


@pytest.fixture
def group_factory():
    def make(membership, *, level=School.Level.SECUNDARIA, grade=2):
        school = School.objects.create(
            workspace=membership.workspace,
            name="Escuela Uno",
            level=level,
        )
        year = SchoolYear.objects.create(
            workspace=membership.workspace,
            school=school,
            label="2025-2026",
        )
        return Group.objects.create(
            workspace=membership.workspace,
            school_year=year,
            grado=grade,
            grupo="A",
        )

    return make


def test_catalog_returns_group_context_and_verified_field_content(
    membership_factory,
    client_for,
    group_factory,
):
    membership = membership_factory()
    group = group_factory(membership, grade=2)

    response = client_for(membership).get(
        "/api/lesson-plans/catalog/",
        {"group": group.id, "field": "languages"},
    )

    assert response.status_code == 200
    assert response.data["phase"] == 6
    assert response.data["grade"] == 2
    assert response.data["methodology"] == {
        "id": "community-based-project-learning",
        "name": "Community-Based Project Learning",
    }
    assert [subject["id"] for subject in response.data["subjects"]] == [
        "spanish",
        "english",
        "arts",
    ]
    assert len(response.data["cross_cutting_themes"]) == 7
    assert response.data["contents"][0]["id"] == "languages-text-resources"
    assert [pda["id"] for pda in response.data["contents"][0]["pdas"]] == [
        "languages-accentuation",
        "languages-coherent-texts",
    ]


def test_catalog_returns_empty_verified_content_for_supported_field(
    membership_factory,
    client_for,
    group_factory,
):
    membership = membership_factory()
    group = group_factory(membership, grade=1)

    response = client_for(membership).get(
        "/api/lesson-plans/catalog/",
        {"group": group.id, "field": "scientific-thinking"},
    )

    assert response.status_code == 200
    assert response.data["grade"] == 1
    assert response.data["contents"] == []
    assert [subject["id"] for subject in response.data["subjects"]] == [
        "mathematics",
        "biology",
        "physics",
        "chemistry",
    ]


def test_catalog_requires_authentication():
    response = APIClient().get(
        "/api/lesson-plans/catalog/",
        {"group": 1, "field": "languages"},
    )

    assert response.status_code in {401, 403}


def test_catalog_requires_view_workspace_permission(
    membership_factory,
    client_for,
    group_factory,
):
    membership = membership_factory(role="no-capabilities-role")
    group = group_factory(membership)

    response = client_for(membership).get(
        "/api/lesson-plans/catalog/",
        {"group": group.id, "field": "languages"},
    )

    assert response.status_code == 403


def test_catalog_does_not_reveal_a_group_from_another_workspace(
    membership_factory,
    client_for,
    group_factory,
):
    caller = membership_factory()
    other = membership_factory()
    foreign_group = group_factory(other)

    response = client_for(caller).get(
        "/api/lesson-plans/catalog/",
        {"group": foreign_group.id, "field": "languages"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("query", "expected_error"),
    [
        ({"field": "languages"}, "group"),
        ({"group": "1"}, "field"),
        ({"group": "not-an-integer", "field": "languages"}, "group"),
    ],
)
def test_catalog_rejects_missing_or_invalid_query_parameters(
    membership_factory,
    client_for,
    query,
    expected_error,
):
    membership = membership_factory()

    response = client_for(membership).get("/api/lesson-plans/catalog/", query)

    assert response.status_code == 400
    assert expected_error in response.data


def test_catalog_rejects_non_secondary_group(
    membership_factory,
    client_for,
    group_factory,
):
    membership = membership_factory()
    group = group_factory(membership, level=School.Level.PRIMARIA)

    response = client_for(membership).get(
        "/api/lesson-plans/catalog/",
        {"group": group.id, "field": "languages"},
    )

    assert response.status_code == 400
    assert "group" in response.data


def test_catalog_rejects_unsupported_field_id(
    membership_factory,
    client_for,
    group_factory,
):
    membership = membership_factory()
    group = group_factory(membership)

    response = client_for(membership).get(
        "/api/lesson-plans/catalog/",
        {"group": group.id, "field": "unknown"},
    )

    assert response.status_code == 400
    assert "field" in response.data
