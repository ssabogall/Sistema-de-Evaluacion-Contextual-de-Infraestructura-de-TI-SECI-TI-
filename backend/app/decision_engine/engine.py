"""Orquesta el motor: requisitos confirmados + ranking -> recomendacion.

Es la unica pieza que conoce el orden de los pasos (pesos -> puntajes -> seleccion ->
mensaje); cada paso vive en su propio modulo y sigue siendo deterministico, sin LLM.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.decision_engine.architectures import ArchitectureId
from app.decision_engine.explanation import build_message
from app.decision_engine.scoring import score_by_variable, unknown_variables
from app.decision_engine.selection import select
from app.decision_engine.weights import rank_to_weights
from app.schemas.business_case import PriorityRanking, RequirementKey, Requirements


class WeightsSource(StrEnum):
    RANKING = "ranking"  # el usuario dio las 4 posiciones
    EQUAL = "equal"  # sin ranking o incompleto: 25 % por pilar


class Recommendation(BaseModel):
    """Resultado completo del motor. Guarda todo lo necesario para auditar la decision."""

    model_config = ConfigDict(extra="forbid")

    architecture: ArchitectureId
    runner_up: ArchitectureId
    totals: dict[ArchitectureId, float]
    margin: float
    trade_off: bool
    tie_broken: bool
    message: str
    weights: dict[RequirementKey, float]
    weights_source: WeightsSource
    unknown_variables: list[RequirementKey]
    contributions: dict[ArchitectureId, dict[RequirementKey, float]]


def evaluate(requirements: Requirements, ranking: PriorityRanking) -> Recommendation:
    levels = {
        key: str(requirement.value.value) for key, requirement in requirements.canonical_items()
    }
    engine_ranking = ranking.to_engine_ranking()

    weights = rank_to_weights(engine_ranking)
    contributions = score_by_variable(levels, weights)
    result = select(contributions)
    unknown = unknown_variables(levels)

    return Recommendation(
        architecture=result.winner,
        runner_up=result.runner_up,
        totals=result.totals,
        margin=result.margin,
        trade_off=result.trade_off,
        tie_broken=result.tie_broken,
        message=build_message(result, contributions, unknown),
        weights=weights,
        weights_source=WeightsSource.EQUAL if engine_ranking is None else WeightsSource.RANKING,
        unknown_variables=list(unknown),
        contributions=contributions,
    )
