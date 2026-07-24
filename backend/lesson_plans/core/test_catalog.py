import pytest

from .catalog import (
    CROSS_CUTTING_THEMES,
    FIELDS,
    METHODOLOGIES,
    PDAS,
    PHASE,
    SUBJECTS,
    field_by_id,
    official_content_for,
    pda_by_id,
    subjects_for,
)


def test_catalog_defines_phase_six_and_only_community_project_learning():
    assert PHASE == 6
    assert [(item.id, item.name) for item in METHODOLOGIES] == [
        (
            "community-based-project-learning",
            "Community-Based Project Learning",
        )
    ]


def test_fields_have_stable_ids_and_official_subject_relationships():
    assert {field.id for field in FIELDS} == {
        "languages",
        "scientific-thinking",
        "ethics-nature-societies",
        "human-community",
    }
    assert [subject.id for subject in subjects_for("languages")] == [
        "spanish",
        "english",
        "arts",
    ]
    assert [subject.id for subject in subjects_for("scientific-thinking")] == [
        "mathematics",
        "biology",
        "physics",
        "chemistry",
    ]
    assert [subject.id for subject in subjects_for("ethics-nature-societies")] == [
        "geography",
        "history",
        "civics-ethics",
    ]
    assert [subject.id for subject in subjects_for("human-community")] == [
        "technology",
        "physical-education",
        "socioemotional-tutoring",
    ]


def test_field_lookup_uses_stable_id_and_rejects_display_text():
    assert field_by_id("languages").name == "Lenguajes"
    with pytest.raises(KeyError, match="Unsupported field"):
        field_by_id("Lenguajes")


def test_catalog_has_the_seven_official_cross_cutting_themes():
    assert [(theme.id, theme.name) for theme in CROSS_CUTTING_THEMES] == [
        ("inclusion", "Inclusión"),
        ("critical-thinking", "Pensamiento crítico"),
        ("critical-interculturality", "Interculturalidad crítica"),
        ("gender-equality", "Igualdad de género"),
        ("healthy-living", "Vida saludable"),
        (
            "cultures-through-reading-writing",
            "Apropiación de las culturas a través de la lectura y la escritura",
        ),
        ("arts-aesthetic-experiences", "Artes y experiencias estéticas"),
    ]


def test_verified_official_content_and_pda_are_retrievable_by_stable_ids():
    content = official_content_for("languages")
    assert [(item.id, item.text) for item in content] == [
        (
            "languages-text-resources",
            "Recursos lingüísticos y textuales para la comprensión y producción de textos.",
        )
    ]
    assert pda_by_id("languages", "languages-accentuation").text == (
        "Emplea las reglas de acentuación de palabras agudas, graves, esdrújulas y "
        "sobresdrújulas para escribir con corrección."
    )


def test_content_lookup_distinguishes_empty_verified_subset_and_invalid_field():
    assert official_content_for("scientific-thinking") == ()
    with pytest.raises(KeyError, match="Unsupported field"):
        official_content_for("unknown")
    with pytest.raises(KeyError, match="Unsupported PDA"):
        pda_by_id("languages", "unknown")


def test_all_catalog_ids_are_unique_within_their_lookup_scope():
    assert len({field.id for field in FIELDS}) == len(FIELDS)
    assert len({theme.id for theme in CROSS_CUTTING_THEMES}) == len(
        CROSS_CUTTING_THEMES
    )
    for field in FIELDS:
        subjects = [subject for subject in SUBJECTS if subject.field_id == field.id]
        assert len({subject.id for subject in subjects}) == len(subjects)
        content_ids = {content.id for content in official_content_for(field.id)}
        pdas = [pda for pda in PDAS if pda.content_id in content_ids]
        assert len({pda.id for pda in pdas}) == len(pdas)
