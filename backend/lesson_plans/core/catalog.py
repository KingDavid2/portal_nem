"""Immutable Phase 6 planning catalog.

Only curriculum text already verified in ``pdas.py`` is exposed as official
content. Fields without verified text intentionally return no content.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata

PHASE = 6


@dataclass(frozen=True, slots=True)
class Methodology:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Field:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Subject:
    id: str
    name: str
    field_id: str


@dataclass(frozen=True, slots=True)
class Theme:
    id: str
    name: str


@dataclass(frozen=True, slots=True)
class Pda:
    id: str
    text: str
    content_id: str


@dataclass(frozen=True, slots=True)
class Content:
    id: str
    text: str
    field_id: str
    pda_ids: tuple[str, ...]


COMMUNITY_BASED_PROJECT_LEARNING = Methodology(
    "community-based-project-learning",
    "Community-Based Project Learning",
)
METHODOLOGIES = (COMMUNITY_BASED_PROJECT_LEARNING,)

FIELDS = (
    Field("languages", "Lenguajes"),
    Field("scientific-thinking", "Saberes y Pensamiento Científico"),
    Field("ethics-nature-societies", "Ética, Naturaleza y Sociedades"),
    Field("human-community", "De lo Humano y lo Comunitario"),
)

SUBJECTS = (
    Subject("spanish", "Español", "languages"),
    Subject("english", "Inglés", "languages"),
    Subject("arts", "Artes", "languages"),
    Subject("mathematics", "Matemáticas", "scientific-thinking"),
    Subject("biology", "Biología", "scientific-thinking"),
    Subject("physics", "Física", "scientific-thinking"),
    Subject("chemistry", "Química", "scientific-thinking"),
    Subject("geography", "Geografía", "ethics-nature-societies"),
    Subject("history", "Historia", "ethics-nature-societies"),
    Subject("civics-ethics", "Formación Cívica y Ética", "ethics-nature-societies"),
    Subject("technology", "Tecnología", "human-community"),
    Subject("physical-education", "Educación Física", "human-community"),
    Subject(
        "socioemotional-tutoring",
        "Educación Socioemocional/Tutoría",
        "human-community",
    ),
)

CROSS_CUTTING_THEMES = (
    Theme("inclusion", "Inclusión"),
    Theme("critical-thinking", "Pensamiento crítico"),
    Theme("critical-interculturality", "Interculturalidad crítica"),
    Theme("gender-equality", "Igualdad de género"),
    Theme("healthy-living", "Vida saludable"),
    Theme(
        "cultures-through-reading-writing",
        "Apropiación de las culturas a través de la lectura y la escritura",
    ),
    Theme("arts-aesthetic-experiences", "Artes y experiencias estéticas"),
)

PDAS = (
    Pda(
        "ethics-independence-relationship",
        "Relaciona la Revolución de Independencia de 1810 en nuestro país con el "
        "agotamiento del imperio español para mantener la cohesión de sus colonias "
        "ultramarinas.",
        "ethics-independence",
    ),
    Pda(
        "ethics-independence-processes",
        "Comprende la confluencia de procesos (por ejemplo, las reformas borbónicas) "
        "y hechos (como la invasión napoleónica en España) en la configuración de la "
        "lucha por la Independencia de la Nueva España.",
        "ethics-independence",
    ),
    Pda(
        "ethics-independence-graphics",
        "Diseña recursos gráficos capaces de transmitir el conocimiento sobre la "
        "Independencia de México.",
        "ethics-independence",
    ),
    Pda(
        "languages-accentuation",
        "Emplea las reglas de acentuación de palabras agudas, graves, esdrújulas y "
        "sobresdrújulas para escribir con corrección.",
        "languages-text-resources",
    ),
    Pda(
        "languages-coherent-texts",
        "Produce textos en los que organiza las ideas en párrafos con coherencia y "
        "cohesión para comunicar información a una audiencia determinada.",
        "languages-text-resources",
    ),
)

CONTENTS = (
    Content(
        "ethics-independence",
        "Las gestas de resistencia y los movimientos independentistas.",
        "ethics-nature-societies",
        tuple(p.id for p in PDAS[:3]),
    ),
    Content(
        "languages-text-resources",
        "Recursos lingüísticos y textuales para la comprensión y producción de textos.",
        "languages",
        tuple(p.id for p in PDAS[3:]),
    ),
)


def _normalize(identifier: str) -> str:
    decomposed = unicodedata.normalize("NFKD", identifier)
    ascii_text = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.casefold()).strip("-")


def _lookup(identifier: str, records: tuple, kind: str):
    normalized = _normalize(identifier)
    for record in records:
        if _normalize(record.id) == normalized:
            return record
    raise KeyError(f"Unsupported {kind}: {identifier!r}")


def field_by_id(identifier: str) -> Field:
    return _lookup(identifier, FIELDS, "field")


def theme_by_id(identifier: str) -> Theme:
    return _lookup(identifier, CROSS_CUTTING_THEMES, "theme")


def methodology_by_id(identifier: str) -> Methodology:
    return _lookup(identifier, METHODOLOGIES, "methodology")


def pda_by_id(field_id: str, identifier: str) -> Pda:
    content_ids = {content.id for content in content_for_field(field_id)}
    pdas = tuple(pda for pda in PDAS if pda.content_id in content_ids)
    return _lookup(identifier, pdas, "PDA")


def subjects_for_field(field_id: str) -> tuple[Subject, ...]:
    field = field_by_id(field_id)
    return tuple(subject for subject in SUBJECTS if subject.field_id == field.id)


def content_for_field(field_id: str) -> tuple[Content, ...]:
    field = field_by_id(field_id)
    return tuple(content for content in CONTENTS if content.field_id == field.id)


def subjects_for(field_id: str) -> tuple[Subject, ...]:
    return subjects_for_field(field_id)


def official_content_for(field_id: str) -> tuple[Content, ...]:
    return content_for_field(field_id)
