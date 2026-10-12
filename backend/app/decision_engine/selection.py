"""Eleccion de la arquitectura ganadora y deteccion de trade-off."""

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict

from app.decision_engine.architectures import ArchitectureId
from app.schemas.business_case import RequirementKey

# Hay trade-off si el margen entre el 1.o y el 2.o es menor al 20 % del total del ganador.
# En los 98.304 escenarios simulados el ganador siempre tuvo total > 0 (minimo 0.45), asi que
# la regla relativa es valida; tests/test_engine_invariants.py vigila que siga siendolo.
TRADE_OFF_RATIO = 0.20
# Los totales son sumas de floats; se redondea para que los empates sean exactos y el umbral
# no dependa del ruido de coma flotante (los pasos reales son multiplos de ~0.006).
ROUND_DIGITS = 9

_ARCHITECTURE_ORDER = list(ArchitectureId)  # A, B, C: orden del catalogo (desempate)
_KEY_ORDER = list(RequirementKey)


class SelectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    winner: ArchitectureId
    runner_up: ArchitectureId
    totals: dict[ArchitectureId, float]
    margin: float
    trade_off: bool
    # True si 1.o y 2.o tenian exactamente el mismo total y se desempato por orden del catalogo.
    tie_broken: bool
    # Contribucion del ganador menos la del segundo, por variable (negativo = favorece al 2.o).
    deltas: dict[RequirementKey, float]
    # Variables con delta distinto de cero, de mayor a menor |delta|
    # (si empatan, se respeta el orden de declaracion de RequirementKey).
    separating_variables: tuple[RequirementKey, ...]


def select(
    contributions: Mapping[ArchitectureId, Mapping[RequirementKey, float]],
) -> SelectionResult:
    """Suma las contribuciones, elige ganador y calcula margen y trade-off."""
    if set(contributions) != set(ArchitectureId):
        raise ValueError("Se necesitan las contribuciones de las 3 arquitecturas")

    totals = {
        architecture: round(sum(per_variable.values()), ROUND_DIGITS)
        for architecture, per_variable in contributions.items()
    }
    ranked = sorted(ArchitectureId, key=lambda a: (-totals[a], _ARCHITECTURE_ORDER.index(a)))
    winner, runner_up = ranked[0], ranked[1]

    margin = round(totals[winner] - totals[runner_up], ROUND_DIGITS)
    threshold = round(TRADE_OFF_RATIO * totals[winner], ROUND_DIGITS)
    tie_broken = margin == 0
    trade_off = tie_broken or margin < threshold

    deltas = {
        key: round(contributions[winner][key] - contributions[runner_up][key], ROUND_DIGITS)
        for key in RequirementKey
    }
    separating = sorted(
        (key for key in RequirementKey if deltas[key] != 0),
        key=lambda key: (-abs(deltas[key]), _KEY_ORDER.index(key)),
    )

    return SelectionResult(
        winner=winner,
        runner_up=runner_up,
        totals=totals,
        margin=margin,
        trade_off=trade_off,
        tie_broken=tie_broken,
        deltas=deltas,
        separating_variables=tuple(separating),
    )
