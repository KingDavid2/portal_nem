"""Schema is the contract that survives into production — pin its shape."""

from __future__ import annotations

from lesson_plans.core.schema import (
    CCT_PLACEHOLDER,
    METHODOLOGY_ABPC,
    ContentPda,
    Datos,
    Momento,
    Proyecto,
    Session,
    Step,
)


def _minimal_proyecto(**overrides) -> Proyecto:
    data = dict(
        datos=Datos(
            school_name="Escuela Secundaria General Jesús Reyes Heroles",
            grade="SEGUNDO",
            campo_formativo="ÉTICA, NATURALEZA Y SOCIEDADES",
            date="JUEVES, 18 DE SEPTIEMBRE DE 2025",
        ),
        title="Héroes y Gestas",
        purpose="Fomentar la comprensión...",
        articulating_axes=[{"name": "Inclusión", "justification": "..."}],
        problem_or_theme="LA INDEPENDENCIA DE MEXICO",
        contents_and_pdas=[
            ContentPda(
                content="Las gestas de resistencia.",
                pdas=["Relaciona la Revolución de Independencia de 1810..."],
            )
        ],
        stages=[
            {
                "name": "Planeación",
                "momentos": [
                    Momento(
                        number=1,
                        name="Identificación",
                        sessions=[
                            Session(
                                duration_minutes=30,
                                steps=[Step(number=1, dynamic="Introducción...")],
                            )
                        ],
                    )
                ],
            }
        ],
        rubric={"criteria": [{"criterion": "Participación", "levels": ["A", "B", "C", "D"]}]},
    )
    data.update(overrides)
    return Proyecto(**data)


def test_proyecto_roundtrips_through_pydantic():
    p = _minimal_proyecto()
    dumped = p.model_dump()
    assert Proyecto(**dumped) == p


def test_datos_defaults_are_nem_canonical():
    d = Datos(school_name="X", grade="PRIMERO", campo_formativo="LENGUAJES", date="HOY")
    assert d.cct == CCT_PLACEHOLDER
    assert d.phase == 6
    assert d.methodology == METHODOLOGY_ABPC


def test_datos_subject_and_period_default_to_empty():
    """The model never fills these — the server stamps them after the parse, and
    a plan generated before they existed must still load."""
    d = Datos(school_name="X", grade="PRIMERO", campo_formativo="LENGUAJES", date="HOY")
    assert (d.subject, d.start_date, d.end_date) == ("", "", "")


def test_all_pdas_flattens_every_pda_string():
    p = _minimal_proyecto(
        contents_and_pdas=[
            ContentPda(content="c1", pdas=["pda-a", "pda-b"]),
            ContentPda(content="c2", pdas=["pda-c"]),
        ]
    )
    assert p.all_pdas() == ["pda-a", "pda-b", "pda-c"]
