"""Aporte ponderado de cada variable a cada arquitectura (modelo SAW).

contribucion(arquitectura, variable) = peso(variable) x puntaje(arquitectura, nivel)
"""

from collections.abc import Mapping

from app.decision_engine.architectures import ArchitectureId
from app.decision_engine.compatibility_table import get_score
from app.schemas.business_case import RequirementKey

UNKNOWN_LEVEL = "unknown"
# Punto medio real de la escala -2..+3. Se suma igual a las 3 arquitecturas, asi que no
# cambia cual gana: solo evita que un dato faltante cuente como "ni bueno ni malo" (0).
UNKNOWN_SCORE = 0.5


def unknown_variables(requirements: Mapping[RequirementKey, str]) -> tuple[RequirementKey, ...]:
    """Variables sin dato (o con conflicto: el esquema las normaliza a 'unknown')."""
    return tuple(key for key in RequirementKey if str(requirements[key]) == UNKNOWN_LEVEL)


def score_by_variable(
    requirements: Mapping[RequirementKey, str],
    weights: Mapping[RequirementKey, float],
) -> dict[ArchitectureId, dict[RequirementKey, float]]:
    """Calcula peso x puntaje para cada arquitectura y cada una de las 6 variables.

    `requirements` mapea cada variable a su nivel ya extraido (el valor del enum, p. ej.
    "high"). Se pasa solo ese diccionario, no el ConfirmedBusinessCase completo, para que
    el motor no dependa de la forma del contrato HTTP.
    """
    missing = [key for key in RequirementKey if key not in requirements or key not in weights]
    if missing:
        raise ValueError(f"Faltan requisitos o pesos para: {[str(key) for key in missing]}")

    contributions: dict[ArchitectureId, dict[RequirementKey, float]] = {}
    for architecture in ArchitectureId:
        per_variable: dict[RequirementKey, float] = {}
        for key in RequirementKey:
            level = str(requirements[key])
            if level == UNKNOWN_LEVEL:
                score = UNKNOWN_SCORE
            else:
                score = get_score(key, level, architecture)
            per_variable[key] = weights[key] * score
        contributions[architecture] = per_variable
    return contributions
