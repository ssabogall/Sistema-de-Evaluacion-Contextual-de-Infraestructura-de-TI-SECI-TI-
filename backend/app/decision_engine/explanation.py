"""Mensaje final al usuario: plantilla fija, sin LLM.

Todo lo que dice sale de numeros ya calculados por el motor (trazabilidad); el texto solo
rellena huecos con las variables de mayor contribucion ponderada (peso x puntaje).
"""

from collections.abc import Collection, Mapping

from app.decision_engine.architectures import ArchitectureId
from app.decision_engine.selection import SelectionResult
from app.schemas.business_case import RequirementKey

ARCHITECTURE_LABELS: dict[ArchitectureId, str] = {
    ArchitectureId.A: "la Arquitectura A (básica)",
    ArchitectureId.B: "la Arquitectura B (escalable)",
    ArchitectureId.C: "la Arquitectura C (resiliente)",
}

VARIABLE_LABELS: dict[RequirementKey, str] = {
    RequirementKey.SERVICE_INTERRUPTION_TOLERANCE: "la tolerancia a interrupciones del servicio",
    RequirementKey.BUSINESS_CONTINUITY_CRITICALITY: "la criticidad de continuidad del negocio",
    RequirementKey.INFORMATION_SENSITIVITY: "la sensibilidad de la información",
    RequirementKey.AVAILABLE_BUDGET: "el presupuesto disponible",
    RequirementKey.DEMAND_PATTERN: "el patrón de demanda",
    RequirementKey.EXPECTED_LOAD_VOLUME: "el volumen de carga esperado",
}

_KEY_ORDER = list(RequirementKey)
MAX_VARIABLES_NAMED = 2


def _join(labels: list[str]) -> str:
    return labels[0] if len(labels) == 1 else f"{labels[0]} y {labels[1]}"


def _capitalize(text: str) -> str:
    return text[0].upper() + text[1:]


def build_message(
    result: SelectionResult,
    contributions: Mapping[ArchitectureId, Mapping[RequirementKey, float]],
    unknown_variables: Collection[RequirementKey] = (),
) -> str:
    """Arma el texto final. `unknown_variables` evita presentar un dato faltante (valor
    neutro 0.5) como si fuera una razon a favor del ganador."""
    winner = ARCHITECTURE_LABELS[result.winner]
    parts = [f"Se recomienda {winner}, con un puntaje de {result.totals[result.winner]:.2f}."]

    winner_contributions = contributions[result.winner]
    top = sorted(
        (key for key in RequirementKey if key not in unknown_variables),
        key=lambda key: (-winner_contributions[key], _KEY_ORDER.index(key)),
    )[:MAX_VARIABLES_NAMED]
    top = [key for key in top if winner_contributions[key] > 0]
    if top:
        parts.append(f"Lo que más pesó a su favor: {_join([VARIABLE_LABELS[k] for k in top])}.")

    if result.trade_off:
        runner_up = ARCHITECTURE_LABELS[result.runner_up]
        if result.tie_broken:
            parts.append(
                f"{_capitalize(runner_up)} obtuvo exactamente el mismo puntaje; se eligió "
                f"{winner} por el orden del catálogo (de la más simple a la más resiliente)."
            )
        else:
            parts.append(f"{_capitalize(runner_up)} quedó muy cerca, a {result.margin:.2f} puntos.")
        favoring_runner_up = [k for k in result.separating_variables if result.deltas[k] < 0]
        if favoring_runner_up:
            names = _join([VARIABLE_LABELS[k] for k in favoring_runner_up[:MAX_VARIABLES_NAMED]])
            parts.append(f"Estaba mejor posicionada en {names}.")

    if unknown_variables:
        names = [VARIABLE_LABELS[k] for k in _KEY_ORDER if k in unknown_variables]
        parts.append(
            "No había información sobre "
            + ", ".join(names)
            + "; se usó un valor neutro para esos datos."
        )
    return " ".join(parts)
