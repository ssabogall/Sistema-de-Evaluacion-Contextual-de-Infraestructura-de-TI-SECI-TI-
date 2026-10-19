import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.ai.base import AIResponseValidationError
from app.ai.gemini_extractor import GeminiRequirementExtractor
from tests.helpers import analysis_payload, requirement

CASE = "Tienda con 600 usuarios concurrentes y 120 solicitudes por segundo."


class FakeModels:
    def __init__(self, text: str) -> None:
        self._text = text

    def generate_content(self, **_: Any) -> SimpleNamespace:
        return SimpleNamespace(text=self._text)


def extractor_returning(payload: dict[str, Any]) -> GeminiRequirementExtractor:
    payload = {k: v for k, v in payload.items() if k != "requires_user_confirmation"}
    client: Any = SimpleNamespace(models=FakeModels(json.dumps(payload)))
    return GeminiRequirementExtractor(api_key="key", model="model", client=client)


def test_detected_with_unknown_value_is_normalized_to_unknown() -> None:
    payload = analysis_payload(
        expected_load_volume=requirement("unknown", "detected", ["120 solicitudes por segundo"]),
        demand_pattern=requirement("unpredictable_peaks", "detected", ["picos imprevistos"]),
    )

    result = extractor_returning(payload).extract_requirements(CASE)

    load = result.requirements.expected_load_volume
    assert (load.value.value, load.status.value, load.evidence) == ("unknown", "unknown", [])
    # No toca las variables bien detectadas.
    demand = result.requirements.demand_pattern
    assert (demand.value.value, demand.status.value) == ("unpredictable_peaks", "detected")
    assert result.requires_user_confirmation is True


def test_unknown_with_stray_evidence_is_cleaned() -> None:
    payload = analysis_payload(
        available_budget=requirement("unknown", "unknown", ["2.500 USD mensuales"]),
    )

    result = extractor_returning(payload).extract_requirements(CASE)

    assert result.requirements.available_budget.evidence == []


def test_conflict_with_unknown_value_is_left_untouched() -> None:
    payload = analysis_payload(
        available_budget=requirement("unknown", "conflict", ["presupuesto limitado", "sin limite"]),
    )

    result = extractor_returning(payload).extract_requirements(CASE)

    assert result.requirements.available_budget.status.value == "conflict"


def test_other_invalid_responses_still_fail_validation() -> None:
    payload = analysis_payload(
        available_budget=requirement("enorme", "detected", ["mucho"]),
    )

    with pytest.raises(AIResponseValidationError):
        extractor_returning(payload).extract_requirements(CASE)
