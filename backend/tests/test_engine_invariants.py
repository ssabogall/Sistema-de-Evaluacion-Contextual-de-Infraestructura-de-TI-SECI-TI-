"""Propiedades que el motor debe cumplir para TODA combinacion de entradas posible."""

from itertools import permutations, product

from app.decision_engine.scoring import score_by_variable
from app.decision_engine.selection import select
from app.decision_engine.weights import rank_to_weights
from app.schemas.business_case import (
    BusinessPriorityStatement,
    DemandPattern,
    RequirementKey,
    StandardLevel,
)

_LEVELS = {
    key: [
        level.value
        for level in (DemandPattern if key == RequirementKey.DEMAND_PATTERN else StandardLevel)
    ]
    for key in RequirementKey
}


def _all_rankings():
    for order in permutations(BusinessPriorityStatement):
        yield {statement: pos for pos, statement in enumerate(order, start=1)}


def test_winner_total_is_always_positive() -> None:
    """La regla de trade-off 'margen < 20 % del ganador' solo tiene sentido si el total del
    ganador es > 0. Hoy se cumple por la forma de la tabla; si alguien la cambia y esto
    falla, hay que revisar TRADE_OFF_RATIO antes de seguir."""
    lowest = None
    for ranking in _all_rankings():
        weights = rank_to_weights(ranking)
        for combo in product(*(_LEVELS[key] for key in RequirementKey)):
            requirements = dict(zip(RequirementKey, combo, strict=True))
            result = select(score_by_variable(requirements, weights))
            total = result.totals[result.winner]
            lowest = total if lowest is None else min(lowest, total)
            assert total > 0, (ranking, requirements, total)
    assert lowest is not None and lowest > 0.4
