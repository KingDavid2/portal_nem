"""Contract tests for `LessonPlanCreateSerializer` — the only writable
surface of `POST /api/lesson-plans/`.

The serializer resolves its `group` through the workspace-scoped manager, so
every test runs inside `workspace_scope(...)` exactly as a request would.
"""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from lesson_plans.serializers import LessonPlanCreateSerializer
from schools.models import Group, School, SchoolYear
from workspaces.models import Membership, Workspace
from workspaces.scope import workspace_scope

pytestmark = pytest.mark.django_db

User = get_user_model()

VALID_CONTENT_SELECTIONS = [
    {
        "content_id": "languages-text-resources",
        "pda_ids": ["languages-accentuation", "languages-coherent-texts"],
    }
]


@pytest.fixture
def membership_factory():
    def make(*, role="member"):
        workspace = Workspace.objects.create(type=Workspace.Type.GROUP)
        user = User.objects.create_user(
            email=f"user-{Membership.objects.count()}@example.com",
            password="s3cret-pass",
        )
        return Membership.objects.create(user=user, workspace=workspace, role=role)

    return make


@pytest.fixture
def group_factory():
    def make(membership, *, level=School.Level.SECUNDARIA, grade=2):
        school = School.objects.create(
            workspace=membership.workspace, name="Escuela Uno", level=level
        )
        year = SchoolYear.objects.create(
            workspace=membership.workspace, school=school, label="2025-2026"
        )
        return Group.objects.create(
            workspace=membership.workspace, school_year=year, grado=grade, grupo="A"
        )

    return make


@pytest.fixture
def membership(membership_factory):
    return membership_factory()


@pytest.fixture
def group(group_factory, membership):
    return group_factory(membership)


def payload_for(group, **overrides):
    payload = {
        "group": group.pk,
        "field_id": "languages",
        "subject_id": "spanish",
        "methodology_id": "community-based-project-learning",
        "theme": "La independencia contada por la comunidad",
        "context_diagnosis": "El grupo requiere fortalecer la producción escrita.",
        "scenario": "community",
        "duration_weeks": 4,
        "start_date": "2026-01-12",
        "end_date": "2026-02-06",
        "cross_cutting_theme_ids": ["critical-thinking", "inclusion"],
        "content_selections": [
            dict(selection) for selection in VALID_CONTENT_SELECTIONS
        ],
    }
    payload.update(overrides)
    return payload


def validate(membership, data):
    """Run the serializer under the caller's workspace scope, returning the
    serializer so tests can assert on `validated_data` or on `errors`."""
    with workspace_scope(membership.workspace_id):
        serializer = LessonPlanCreateSerializer(data=data)
        serializer.is_valid()
        return serializer


def test_valid_payload_is_accepted_with_canonical_catalog_ids(membership, group):
    serializer = validate(membership, payload_for(group))

    assert serializer.errors == {}
    validated = serializer.validated_data
    assert validated["group"] == group
    assert validated["field_id"] == "languages"
    assert validated["subject_id"] == "spanish"
    assert validated["methodology_id"] == "community-based-project-learning"
    assert validated["cross_cutting_theme_ids"] == ["critical-thinking", "inclusion"]
    assert validated["content_selections"] == VALID_CONTENT_SELECTIONS


def test_subject_id_is_optional(membership, group):
    serializer = validate(membership, payload_for(group, subject_id=""))

    assert serializer.errors == {}
    assert serializer.validated_data["subject_id"] == ""


def test_campo_and_grade_are_not_part_of_the_write_contract(membership, group):
    serializer = validate(
        membership,
        payload_for(group, campo="Matemáticas", grade="NOVENO"),
    )

    assert serializer.errors == {}
    assert "campo" not in serializer.validated_data
    assert "grade" not in serializer.validated_data


def test_group_from_another_workspace_is_invisible(membership, group_factory, membership_factory):
    foreign_group = group_factory(membership_factory())

    serializer = validate(membership, payload_for(foreign_group))

    assert "group" in serializer.errors


def test_non_secondary_group_is_rejected(membership, group_factory):
    primaria_group = group_factory(membership, level=School.Level.PRIMARIA)

    serializer = validate(membership, payload_for(primaria_group))

    assert serializer.errors["group"] == ["The group must belong to a secondary school."]


def test_unsupported_field_id_is_rejected(membership, group):
    serializer = validate(membership, payload_for(group, field_id="astrology"))

    assert serializer.errors == {"field_id": ["Unsupported field id."]}


def test_subject_from_another_field_is_rejected(membership, group):
    serializer = validate(membership, payload_for(group, subject_id="biology"))

    assert serializer.errors == {
        "subject_id": ["Subject does not belong to the selected field."]
    }


def test_unsupported_methodology_id_is_rejected(membership, group):
    serializer = validate(membership, payload_for(group, methodology_id="lecture"))

    assert serializer.errors == {"methodology_id": ["Unsupported methodology id."]}


def test_empty_cross_cutting_theme_ids_are_rejected(membership, group):
    serializer = validate(membership, payload_for(group, cross_cutting_theme_ids=[]))

    assert serializer.errors == {
        "cross_cutting_theme_ids": ["The cross-cutting theme ids must not be empty."]
    }


def test_duplicated_cross_cutting_theme_ids_are_rejected(membership, group):
    serializer = validate(
        membership,
        payload_for(group, cross_cutting_theme_ids=["inclusion", "inclusion"]),
    )

    assert serializer.errors == {
        "cross_cutting_theme_ids": [
            "The cross-cutting theme ids must not contain duplicates."
        ]
    }


def test_unsupported_cross_cutting_theme_id_is_rejected(membership, group):
    serializer = validate(
        membership, payload_for(group, cross_cutting_theme_ids=["inclusion", "nope"])
    )

    assert serializer.errors == {
        "cross_cutting_theme_ids": ["Unsupported cross-cutting theme id."]
    }


def test_empty_content_selections_are_rejected(membership, group):
    serializer = validate(membership, payload_for(group, content_selections=[]))

    assert serializer.errors == {
        "content_selections": ["The content selections must not be empty."]
    }


def test_content_selection_without_pdas_is_rejected(membership, group):
    serializer = validate(
        membership,
        payload_for(
            group,
            content_selections=[
                {"content_id": "languages-text-resources", "pda_ids": []}
            ],
        ),
    )

    assert "pda_ids" in serializer.errors["content_selections"][0]


def test_unsupported_content_id_is_reported_by_index(membership, group):
    serializer = validate(
        membership,
        payload_for(
            group,
            content_selections=[
                {"content_id": "not-a-content", "pda_ids": ["languages-accentuation"]}
            ],
        ),
    )

    assert serializer.errors == {
        "content_selections": [{"content_id": ["Unsupported content id."]}]
    }


def test_unresolvable_pda_id_is_reported_by_index(membership, group):
    serializer = validate(
        membership,
        payload_for(
            group,
            content_selections=[
                {
                    "content_id": "languages-text-resources",
                    "pda_ids": ["languages-accentuation", "not-a-pda"],
                }
            ],
        ),
    )

    assert serializer.errors == {
        "content_selections": [
            {"pda_ids": ["PDA does not belong to the selected content."]}
        ]
    }


def test_pda_belonging_to_a_non_selected_content_is_rejected(membership, group):
    """`ethics-independence-graphics` is a real PDA, but of another field's
    content — selecting it under a Lenguajes content must not pass."""
    serializer = validate(
        membership,
        payload_for(
            group,
            field_id="ethics-nature-societies",
            subject_id="history",
            content_selections=[
                {
                    "content_id": "ethics-independence",
                    "pda_ids": ["ethics-independence-graphics"],
                },
                {
                    "content_id": "ethics-independence",
                    "pda_ids": ["languages-accentuation"],
                },
            ],
        ),
    )

    assert serializer.errors == {
        "content_selections": [
            {},
            {"pda_ids": ["PDA does not belong to the selected content."]},
        ]
    }


def test_duplicate_content_ids_across_selections_are_rejected(membership, group):
    serializer = validate(
        membership,
        payload_for(
            group,
            content_selections=[
                {
                    "content_id": "languages-text-resources",
                    "pda_ids": ["languages-accentuation"],
                },
                {
                    "content_id": "languages-text-resources",
                    "pda_ids": ["languages-coherent-texts"],
                },
            ],
        ),
    )

    assert serializer.errors == {
        "content_selections": [
            "The content selections must not contain duplicate content ids."
        ]
    }


def test_duplicate_pda_ids_within_one_selection_are_rejected(membership, group):
    serializer = validate(
        membership,
        payload_for(
            group,
            content_selections=[
                {
                    "content_id": "languages-text-resources",
                    "pda_ids": ["languages-accentuation", "languages-accentuation"],
                }
            ],
        ),
    )

    assert serializer.errors == {
        "content_selections": [
            {"pda_ids": ["The pda ids must not contain duplicates."]}
        ]
    }


@pytest.mark.parametrize("duration_weeks", [0, 13])
def test_duration_weeks_outside_the_supported_range_is_rejected(
    membership, group, duration_weeks
):
    serializer = validate(membership, payload_for(group, duration_weeks=duration_weeks))

    assert "duration_weeks" in serializer.errors


def test_end_date_before_start_date_is_rejected(membership, group):
    serializer = validate(
        membership, payload_for(group, start_date="2026-02-06", end_date="2026-01-12")
    )

    assert serializer.errors == {
        "end_date": ["The end date must not precede the start date."]
    }


@pytest.mark.parametrize("missing", ["start_date", "end_date"])
def test_both_dates_are_required(membership, group, missing):
    data = payload_for(group)
    del data[missing]

    serializer = validate(membership, data)

    assert missing in serializer.errors


def test_blank_context_diagnosis_is_rejected(membership, group):
    serializer = validate(membership, payload_for(group, context_diagnosis=""))

    assert "context_diagnosis" in serializer.errors


def test_unsupported_scenario_is_rejected(membership, group):
    serializer = validate(membership, payload_for(group, scenario="playground"))

    assert "scenario" in serializer.errors


@pytest.mark.parametrize("field_id", ["scientific-thinking", "human-community"])
def test_a_field_without_verified_content_cannot_produce_a_valid_request(
    membership, group, field_id
):
    """These fields expose no verified curriculum text, so the catalog offers
    no content for them and every selection is unsupported."""
    serializer = validate(
        membership,
        payload_for(
            group,
            field_id=field_id,
            subject_id="",
            content_selections=[
                {
                    "content_id": "languages-text-resources",
                    "pda_ids": ["languages-accentuation"],
                }
            ],
        ),
    )

    assert serializer.errors == {
        "content_selections": [{"content_id": ["Unsupported content id."]}]
    }
