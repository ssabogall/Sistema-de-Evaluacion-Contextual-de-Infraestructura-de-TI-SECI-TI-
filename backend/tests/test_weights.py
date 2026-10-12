from itertools import permutations

import pytest

from app.decision_engine.weights import rank_to_weights
from app.schemas.business_case import BusinessPriorityStatement as S
from app.schemas.business_case import RequirementKey as K

# 1.o confiabilidad, 2.o rendimiento, 3.o costo, 4.o seguridad
RANKING = {
    S.NEVER_STOP_WORKING: 1,
    S.FAST_UNDER_LOAD: 2,
    S.LOWEST_COST: 3,
    S.PROTECT_INFORMATION: 4,
}

EQUAL = {
    K.SERVICE_INTERRUPTION_TOLERANCE: 0.125,
    K.BUSINESS_CONTINUITY_CRITICALITY: 0.125,
    K.INFORMATION_SENSITIVITY: 0.25,
    K.AVAILABLE_BUDGET: 0.25,
    K.DEMAND_PATTERN: 0.125,
    K.EXPECTED_LOAD_VOLUME: 0.125,
}


@pytest.mark.parametrize("order", list(permutations(S)))
def test_weights_sum_to_one_for_every_possible_ranking(order: tuple[S, ...]) -> None:
    ranking = {statement: position for position, statement in enumerate(order, start=1)}
    assert sum(rank_to_weights(ranking).values()) == pytest.approx(1.0, abs=1e-9)


def test_smoothed_weights_split_each_pillar_among_its_variables() -> None:
    weights = rank_to_weights(RANKING)
    assert weights[K.SERVICE_INTERRUPTION_TOLERANCE] == pytest.approx(0.1625, abs=1e-9)
    assert weights[K.BUSINESS_CONTINUITY_CRITICALITY] == pytest.approx(0.1625, abs=1e-9)
    assert weights[K.DEMAND_PATTERN] == pytest.approx(0.1375, abs=1e-9)
    assert weights[K.EXPECTED_LOAD_VOLUME] == pytest.approx(0.1375, abs=1e-9)
    assert weights[K.AVAILABLE_BUDGET] == pytest.approx(0.225, abs=1e-9)
    assert weights[K.INFORMATION_SENSITIVITY] == pytest.approx(0.175, abs=1e-9)


def test_last_ranked_pillar_keeps_a_meaningful_weight() -> None:
    assert rank_to_weights(RANKING)[K.INFORMATION_SENSITIVITY] == pytest.approx(0.175, abs=1e-9)


def test_weights_come_back_in_canonical_key_order() -> None:
    assert list(rank_to_weights(RANKING)) == list(K)


@pytest.mark.parametrize(
    "ranking",
    [
        None,
        {},
        # incompleto
        {S.NEVER_STOP_WORKING: 1, S.LOWEST_COST: 2, S.FAST_UNDER_LOAD: 3},
        # posiciones repetidas
        {
            S.NEVER_STOP_WORKING: 1,
            S.LOWEST_COST: 1,
            S.FAST_UNDER_LOAD: 2,
            S.PROTECT_INFORMATION: 3,
        },
        # posicion fuera de rango
        {
            S.NEVER_STOP_WORKING: 1,
            S.LOWEST_COST: 2,
            S.FAST_UNDER_LOAD: 3,
            S.PROTECT_INFORMATION: 5,
        },
    ],
)
def test_missing_or_invalid_ranking_falls_back_to_equal_pillars(ranking) -> None:
    weights = rank_to_weights(ranking)
    for key, expected in EQUAL.items():
        assert weights[key] == pytest.approx(expected, abs=1e-9)
