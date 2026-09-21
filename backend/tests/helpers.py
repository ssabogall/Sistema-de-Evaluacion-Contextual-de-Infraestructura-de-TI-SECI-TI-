from typing import Any

from app.ai.base import AIRequirementExtractor
from app.schemas.business_case import BusinessCaseAnalysis


def requirement(
    value: str = "unknown",
    status: str = "unknown",
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "value": value,
        "status": status,
        "evidence": evidence or [],
    }


def analysis_payload(
    business_case: str = "Caso de negocio de prueba suficientemente descriptivo.",
    **overrides: dict[str, Any],
) -> dict[str, Any]:
    requirements = {
        "service_interruption_tolerance": requirement(),
        "business_continuity_criticality": requirement(),
        "information_sensitivity": requirement(),
        "available_budget": requirement(),
        "demand_pattern": requirement(),
        "expected_load_volume": requirement(),
    }
    requirements.update(overrides)
    return {
        "business_case": business_case,
        "requirements": requirements,
        "additional_context": {},
        "missing_requirements": [],
        "warnings": [],
        "requires_user_confirmation": True,
    }


class StaticExtractor(AIRequirementExtractor):
    def __init__(
        self,
        analysis: BusinessCaseAnalysis | None = None,
        error: Exception | None = None,
    ) -> None:
        self.analysis = analysis or BusinessCaseAnalysis.model_validate(analysis_payload())
        self.error = error

    def extract_requirements(self, business_case: str) -> BusinessCaseAnalysis:
        if self.error:
            raise self.error
        payload = self.analysis.model_dump(mode="python")
        payload["business_case"] = business_case
        return BusinessCaseAnalysis.model_validate(payload)
