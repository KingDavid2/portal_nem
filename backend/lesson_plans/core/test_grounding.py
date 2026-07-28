"""The grounding verdict: which rendered PDAs are official, and which are not.

`find_invented_pdas` already decided this at generation time and its answer is
persisted. These tests pin the *rule* it decides by, because the viewer and the
docx renderer now re-apply that same rule per PDA — a rule that drifts would mark
an official PDA as invented in an exported document while the database says the
plan is clean.
"""

from lesson_plans.core.grounding import (
    GroundingReport,
    find_invented_pdas,
    normalize_pda,
)
from lesson_plans.core.schema import ContentPda

OFFICIAL = "Emplea las reglas de acentuación de palabras agudas."
FOREIGN = "Inventa una actividad que nadie autorizó."


def _report(*, invented: list[str] | None = None) -> GroundingReport:
    return GroundingReport(
        selected=[ContentPda(content="Contenido oficial", pdas=[OFFICIAL])],
        invented=invented if invented is not None else [],
    )


def test_normalize_collapses_whitespace_and_case():
    assert normalize_pda("  Emplea   LAS\nreglas ") == normalize_pda("emplea las reglas")


def test_reformatted_official_pda_is_not_invented():
    """Re-wrapping or re-casing official text is a formatting difference, not an
    invention — flagging it would cry wolf on every generation."""
    assert _report().is_official("  EMPLEA las reglas de acentuación\tde palabras agudas. ")


def test_pda_outside_the_selection_is_not_official():
    assert _report().is_official(FOREIGN) is False


def test_empty_selection_makes_every_pda_unofficial():
    """A plan with no persisted selection was never checked against anything; the
    honest verdict is that nothing is confirmed official."""
    report = GroundingReport(selected=[], invented=[])
    assert report.is_official(OFFICIAL) is False


def test_find_invented_pdas_returns_the_offending_text_verbatim():
    """The list — not just its truthiness — is what the audit trail is made of."""
    from lesson_plans.core.schema import Datos, Momento, Proyecto, Rubric, Stage

    proyecto = Proyecto(
        datos=Datos(school_name="", grade="1", campo_formativo="", date=""),
        title="",
        purpose="",
        articulating_axes=[],
        problem_or_theme="",
        contents_and_pdas=[
            ContentPda(content="Contenido oficial", pdas=[OFFICIAL, FOREIGN])
        ],
        stages=[Stage(name="Planeación", momentos=[Momento(number=1, name="", sessions=[])])],
        rubric=Rubric(criteria=[]),
    )

    invented = find_invented_pdas(
        proyecto, [ContentPda(content="Contenido oficial", pdas=[OFFICIAL])]
    )

    assert invented == [FOREIGN]
