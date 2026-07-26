"""Frozen in-code registry of demo personas (port of paysys/crm Demo::Persona).

Each persona is a seedable demo profile: a ``teacher_minimal`` account with
one school and one grupo, a ``teacher_full`` account with a cycle in progress,
and a ``quota_exhausted`` account to demonstrate the generation-limit UI.

The ``provisioner`` field is a **dotted import path string** — resolved
lazily via ``django.utils.module_loading.import_string``. This avoids any
import cycle at module load time because the provisioner classes do not
exist until D3/D4.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.utils.module_loading import import_string


class UnknownPersona(ValueError):
    """Raised when a persona key is not found in the registry."""


@dataclass(frozen=True)
class Persona:
    """One demo persona entry.

    Attributes:
        key: Unique machine-readable identifier.
        label: Human-readable name (Spanish).
        description: What the persona provides (Spanish).
        features: List of feature highlights (Spanish).
        provisioner: Dotted import path to the provisioner class, resolved lazily.
    """

    key: str
    label: str
    description: str
    features: tuple[str, ...]
    provisioner: str

    def resolve_provisioner(self):
        """Lazily import the provisioner class.

        Returns:
            The provisioner class (e.g. ``TeacherMinimal``).
        """
        return import_string(self.provisioner)


_REGISTRY = (
    Persona(
        key="teacher_minimal",
        label="Docente nuevo",
        description="Un docente que acaba de registrarse. Incluye una escuela, un ciclo escolar y un grupo sin planeaciones.",
        features=(
            "Una escuela",
            "Un ciclo escolar",
            "Un grupo",
        ),
        provisioner="demo.provisioning.teacher_minimal.TeacherMinimal",
    ),
    Persona(
        key="teacher_full",
        label="Docente con ciclo en marcha",
        description="Un docente con su ciclo escolar activo: escuela, ciclo, dos grupos, alumnos y dos planeaciones ya generadas.",
        features=(
            "Una escuela",
            "Un ciclo escolar",
            "Dos grupos con alumnos",
            "Dos planeaciones listas",
        ),
        provisioner="demo.provisioning.teacher_full.TeacherFull",
    ),
    Persona(
        key="quota_exhausted",
        label="Cuota agotada",
        description="Mismo perfil que un docente con ciclo en marcha, pero con la cuota mensual de generación ya consumida para demostrar el límite.",
        features=(
            "Una escuela",
            "Un ciclo escolar",
            "Dos grupos con alumnos",
            "Dos planeaciones listas",
            "Cuota mensual agotada",
        ),
        provisioner="demo.provisioning.quota_exhausted.QuotaExhausted",
    ),
)


def all() -> tuple[Persona, ...]:
    """Return all registered personas."""
    return _REGISTRY


def keys() -> tuple[str, ...]:
    """Return all persona keys."""
    return tuple(p.key for p in _REGISTRY)


def find(key: str) -> Persona:
    """Look up a persona by key.

    Args:
        key: The persona key (e.g. ``"teacher_minimal"``).

    Returns:
        The matching ``Persona``.

    Raises:
        UnknownPersona: If the key is not registered.
    """
    for persona in _REGISTRY:
        if persona.key == key:
            return persona
    raise UnknownPersona(f"Unknown demo persona: {key!r}")