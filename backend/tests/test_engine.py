import pytest

from app.decision_engine.architectures import ArchitectureId
from app.decision_engine.engine import Recommendation, WeightsSource, evaluate
from app.schemas.business_case import PriorityRanking, RequirementKey, Requirements
from tests.helpers import analysis_payload, requirement

# Caso de la seccion 5 del documento (tolerancia media, criticidad alta, datos medio,
# presupuesto medio, picos predecibles, volumen medio) en forma de contrato HTTP.
DOC_CASE = analysis_payload(
    service_interruption_tolerance=requirement("medium", "detected", ["minutos"]),
    business_continuity_criticality=requirement("high", "detected", ["ventas"]),
    information_sensitivity=requirement("medium", "detected", ["interna"]),
    available_budget=requirement("medium", "detected", ["moderado"]),
    demand_pattern=requirement("predictable_peaks", "detected", ["campanas"]),
    expected_load_volume=requirement("medium", "detected", ["medio"]),
)["requirements"]

COMPLETE = PriorityRanking(
    never_stop_working=1, lowest_cost=2, fast_under_load=3, protect_information=4
)


def _requirements(payload: dict) -> Requirements:
    return Requirements.model_validate(payload)


def test_evaluate_returns_a_traceable_recommendation() -> None:
    recommendation = evaluate(_requirements(DOC_CASE), COMPLETE)

    assert recommendation.architecture in set(ArchitectureId)
    assert recommendation.runner_up != recommendation.architecture
    assert set(recommendation.totals) == set(ArchitectureId)
    assert set(recommendation.weights) == set(RequirementKey)
    assert sum(recommendation.weights.values()) == pytest.approx(1.0)
    assert recommendation.unknown_variables == []
    assert recommendation.message.startswith("Se recomienda ")
    for architecture in ArchitectureId:
        assert sum(recommendation.contributions[architecture].values()) == pytest.approx(
            recommendation.totals[architecture]
        )


def test_complete_ranking_uses_ranking_weights() -> None:
    recommendation = evaluate(_requirements(DOC_CASE), COMPLETE)

    assert recommendation.weights_source == WeightsSource.RANKING
    assert recommendation.weights[RequirementKey.AVAILABLE_BUDGET] == pytest.approx(0.275)


@pytest.mark.parametrize(
    "ranking",
    [PriorityRanking(), PriorityRanking(never_stop_working=1, lowest_cost=2)],
)
def test_missing_or_incomplete_ranking_falls_back_to_equal_weights(
    ranking: PriorityRanking,
) -> None:
    recommendation = evaluate(_requirements(DOC_CASE), ranking)

    assert recommendation.weights_source == WeightsSource.EQUAL
    assert recommendation.weights[RequirementKey.AVAILABLE_BUDGET] == pytest.approx(0.25)
    assert recommendation.weights[RequirementKey.SERVICE_INTERRUPTION_TOLERANCE] == pytest.approx(
        0.125
    )


def test_unknown_requirements_are_reported_and_use_neutral_value() -> None:
    recommendation = evaluate(_requirements(analysis_payload()["requirements"]), PriorityRanking())

    assert recommendation.unknown_variables == list(RequirementKey)
    assert "No había información sobre" in recommendation.message
    # Todo desconocido: las 3 arquitecturas reciben el mismo valor neutro -> empate.
    assert recommendation.tie_broken
    assert recommendation.architecture == ArchitectureId.A


def test_recommendation_survives_a_json_round_trip() -> None:
    recommendation = evaluate(_requirements(DOC_CASE), COMPLETE)

    restored = Recommendation.model_validate_json(recommendation.model_dump_json())

    assert restored == recommendation
