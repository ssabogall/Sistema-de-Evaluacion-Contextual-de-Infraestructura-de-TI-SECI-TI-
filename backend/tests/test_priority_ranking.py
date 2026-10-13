import pytest
from pydantic import ValidationError

from app.ai.gemini_extractor import _GeminiAnalysisSchema, _strip_additional_properties
from app.ai.prompts.business_case_extractor import BUSINESS_CASE_EXTRACTOR_PROMPT
from app.decision_engine.weights import rank_to_weights
from app.schemas.business_case import (
    BusinessCaseAnalysis,
    BusinessPriorityStatement,
    PriorityRanking,
    RequirementKey,
)
from tests.helpers import StaticExtractor, analysis_payload

COMPLETE = {
    "never_stop_working": 1,
    "protect_information": 2,
    "fast_under_load": 3,
    "lowest_cost": 4,
}


def _confirmation_request(**ranking_fields: object) -> dict[str, object]:
    analysis = analysis_payload()
    request: dict[str, object] = {
        "business_case": analysis["business_case"],
        "requirements": analysis["requirements"],
        "additional_context": analysis["additional_context"],
    }
    if ranking_fields:
        request["priority_ranking"] = ranking_fields
    return request


# ---------------------------------------------------------------- PriorityRanking


def test_fields_match_the_business_priority_statements() -> None:
    assert set(PriorityRanking.model_fields) == {s.value for s in BusinessPriorityStatement}


def test_empty_ranking_is_valid_and_not_usable_by_the_engine() -> None:
    ranking = PriorityRanking()

    assert ranking.is_empty()
    assert ranking.to_engine_ranking() is None


def test_partial_ranking_is_valid_but_not_usable_by_the_engine() -> None:
    ranking = PriorityRanking(never_stop_working=1, lowest_cost=2)

    assert not ranking.is_empty()
    assert ranking.to_engine_ranking() is None


def test_complete_ranking_becomes_engine_dictionary() -> None:
    ranking = PriorityRanking(**COMPLETE)

    assert ranking.to_engine_ranking() == {
        BusinessPriorityStatement.NEVER_STOP_WORKING: 1,
        BusinessPriorityStatement.PROTECT_INFORMATION: 2,
        BusinessPriorityStatement.FAST_UNDER_LOAD: 3,
        BusinessPriorityStatement.LOWEST_COST: 4,
    }


def test_repeated_position_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PriorityRanking(never_stop_working=1, lowest_cost=1)


@pytest.mark.parametrize("position", [0, 5, -1])
def test_position_outside_one_to_four_is_rejected(position: int) -> None:
    with pytest.raises(ValidationError):
        PriorityRanking(never_stop_working=position)


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PriorityRanking.model_validate({"availability": 1})


def test_complete_ranking_feeds_the_engine_weights() -> None:
    ranking = PriorityRanking(**COMPLETE)

    weights = rank_to_weights(ranking.to_engine_ranking())

    # never_stop_working = 1 -> 32.5 % repartido entre sus dos variables.
    assert weights[RequirementKey.SERVICE_INTERRUPTION_TOLERANCE] == pytest.approx(0.1625)
    assert weights[RequirementKey.BUSINESS_CONTINUITY_CRITICALITY] == pytest.approx(0.1625)
    # lowest_cost = 4 -> 17.5 %.
    assert weights[RequirementKey.AVAILABLE_BUDGET] == pytest.approx(0.175)
    assert sum(weights.values()) == pytest.approx(1.0)


def test_empty_ranking_keeps_equal_pillar_weights() -> None:
    weights = rank_to_weights(PriorityRanking().to_engine_ranking())

    assert weights[RequirementKey.AVAILABLE_BUDGET] == pytest.approx(0.25)
    assert weights[RequirementKey.INFORMATION_SENSITIVITY] == pytest.approx(0.25)


# ---------------------------------------------------------------- BusinessCaseAnalysis


def test_analysis_without_ranking_keeps_previous_payloads_valid() -> None:
    analysis = BusinessCaseAnalysis.model_validate(analysis_payload())

    assert analysis.priority_ranking.is_empty()
    assert analysis.priority_ranking_evidence == []


def test_analysis_keeps_ranking_and_cleans_evidence() -> None:
    payload = analysis_payload()
    payload["priority_ranking"] = {"never_stop_working": 1, "lowest_cost": 2}
    payload["priority_ranking_evidence"] = [
        "  lo mas importante es que no se caiga ",
        "lo mas importante es que no se caiga",
        "   ",
    ]

    analysis = BusinessCaseAnalysis.model_validate(payload)

    assert analysis.priority_ranking.never_stop_working == 1
    assert analysis.priority_ranking_evidence == ["lo mas importante es que no se caiga"]


def test_evidence_is_dropped_when_there_is_no_ranking() -> None:
    payload = analysis_payload()
    payload["priority_ranking_evidence"] = ["texto sin orden explicito"]

    analysis = BusinessCaseAnalysis.model_validate(payload)

    assert analysis.priority_ranking_evidence == []


def test_analysis_rejects_repeated_positions() -> None:
    payload = analysis_payload()
    payload["priority_ranking"] = {"never_stop_working": 2, "protect_information": 2}

    with pytest.raises(ValidationError):
        BusinessCaseAnalysis.model_validate(payload)


# ---------------------------------------------------------------- API


def test_analyze_returns_the_ranking_transcribed_by_the_extractor(client_factory) -> None:
    payload = analysis_payload()
    payload["priority_ranking"] = {"never_stop_working": 1, "lowest_cost": 2}
    payload["priority_ranking_evidence"] = ["primero que no se caiga, luego el costo"]
    client = client_factory(StaticExtractor(BusinessCaseAnalysis.model_validate(payload)))

    response = client.post(
        "/api/business-cases/analyze",
        json={"description": "Caso suficientemente largo para ser analizado."},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["priority_ranking"] == {
        "never_stop_working": 1,
        "lowest_cost": 2,
        "fast_under_load": None,
        "protect_information": None,
    }
    assert body["priority_ranking_evidence"] == ["primero que no se caiga, luego el costo"]


def test_analyze_without_ranking_returns_empty_ranking(client_factory) -> None:
    response = client_factory().post(
        "/api/business-cases/analyze",
        json={"description": "Caso suficientemente largo para ser analizado."},
    )

    body = response.json()
    assert set(body["priority_ranking"].values()) == {None}
    assert body["priority_ranking_evidence"] == []


def test_confirm_returns_the_ranking_edited_by_the_user(client_factory) -> None:
    response = client_factory().post(
        "/api/business-cases/confirm", json=_confirmation_request(**COMPLETE)
    )

    assert response.status_code == 200
    assert response.json()["priority_ranking"] == COMPLETE


def test_confirm_without_ranking_returns_empty_ranking(client_factory) -> None:
    response = client_factory().post("/api/business-cases/confirm", json=_confirmation_request())

    assert response.status_code == 200
    assert set(response.json()["priority_ranking"].values()) == {None}


def test_confirm_rejects_repeated_positions(client_factory) -> None:
    response = client_factory().post(
        "/api/business-cases/confirm",
        json=_confirmation_request(never_stop_working=1, lowest_cost=1),
    )

    assert response.status_code == 422


# ---------------------------------------------------------------- esquemas para el LLM


def _open_objects(node: object, path: str = "$") -> list[str]:
    """Rutas de objetos del JSON Schema sin propiedades fijas o con claves libres."""
    found: list[str] = []
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" not in node:
            found.append(path)
        if isinstance(node.get("additionalProperties"), dict):
            found.append(path)
        for key, value in node.items():
            found.extend(_open_objects(value, f"{path}.{key}"))
    elif isinstance(node, list):
        for index, item in enumerate(node):
            found.extend(_open_objects(item, f"{path}[{index}]"))
    return found


def test_schema_sent_to_openai_has_no_open_dictionaries() -> None:
    assert _open_objects(BusinessCaseAnalysis.model_json_schema()) == []


def test_schema_sent_to_openai_has_no_numeric_range_keywords() -> None:
    ranking_schema = PriorityRanking.model_json_schema()

    assert "minimum" not in str(ranking_schema)
    assert "maximum" not in str(ranking_schema)


def test_gemini_schema_requests_the_ranking_without_additional_properties() -> None:
    schema = _strip_additional_properties(_GeminiAnalysisSchema.model_json_schema())

    assert "priority_ranking" in schema["properties"]
    assert "priority_ranking_evidence" in schema["properties"]
    assert "additionalProperties" not in str(schema)
    assert _open_objects(schema) == []


# ---------------------------------------------------------------- prompt


def test_prompt_names_every_priority_and_forbids_inferring_the_order() -> None:
    for statement in BusinessPriorityStatement:
        assert statement.value in BUSINESS_CASE_EXTRACTOR_PROMPT
    assert "priority_ranking_evidence" in BUSINESS_CASE_EXTRACTOR_PROMPT
    assert "NUNCA infieras" in BUSINESS_CASE_EXTRACTOR_PROMPT


def test_prompt_uses_only_values_that_exist_in_the_schema() -> None:
    assert "near_zero" not in BUSINESS_CASE_EXTRACTOR_PROMPT
