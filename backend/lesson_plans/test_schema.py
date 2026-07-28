"""The read schema must type the catalog selections it stores as JSON.

A bare `JSONField` is emitted by drf-spectacular as an untyped value, which
reaches the TypeScript client as `unknown` and makes it impossible to rebuild
a create body from a lesson plan the API just returned.
"""

import pytest
from drf_spectacular.generators import SchemaGenerator


@pytest.fixture(scope="module")
def lesson_plan_schema():
    schema = SchemaGenerator().get_schema(request=None, public=True)
    return schema["components"]["schemas"]["LessonPlan"]["properties"]


def test_cross_cutting_theme_ids_is_an_array_of_strings(lesson_plan_schema):
    assert lesson_plan_schema["cross_cutting_theme_ids"] == {
        "type": "array",
        "items": {"type": "string"},
        "readOnly": True,
    }


def test_content_selections_references_the_content_selection_schema(
    lesson_plan_schema,
):
    assert lesson_plan_schema["content_selections"] == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/ContentSelection"},
        "readOnly": True,
    }


def test_invented_pda_texts_is_typed_and_read_only(lesson_plan_schema):
    assert lesson_plan_schema["invented_pda_texts"] == {
        "type": "array",
        "items": {"type": "string"},
        "readOnly": True,
    }


def test_grounding_selections_references_the_content_pda_text_schema(
    lesson_plan_schema,
):
    assert lesson_plan_schema["grounding_selections"] == {
        "type": "array",
        "items": {"$ref": "#/components/schemas/ContentPdaText"},
        "readOnly": True,
    }
