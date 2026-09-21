import pytest
from pydantic import ValidationError

from app.schemas.business_case import BusinessCaseAnalysis
from tests.helpers import analysis_payload, requirement


def test_normalizes_only_safe_enum_format_equivalents() -> None:
    payload = analysis_payload(
        service_interruption_tolerance=requirement(
            "near-zero",
            "detected",
            ["practicamente no puede interrumpirse"],
        )
    )

    analysis = BusinessCaseAnalysis.model_validate(payload)

    assert analysis.requirements.service_interruption_tolerance.value.value == "near_zero"


def test_rejects_value_outside_closed_enum() -> None:
    payload = analysis_payload(
        expected_load_volume=requirement("extreme", "detected", ["carga extrema"])
    )

    with pytest.raises(ValidationError):
        BusinessCaseAnalysis.model_validate(payload)


def test_unknown_requires_no_evidence() -> None:
    payload = analysis_payload(
        information_sensitivity=requirement("unknown", "unknown", ["sin datos"])
    )

    with pytest.raises(ValidationError):
        BusinessCaseAnalysis.model_validate(payload)


def test_conflict_requires_unknown_and_two_evidence_fragments() -> None:
    valid = analysis_payload(
        business_continuity_criticality=requirement(
            "unknown",
            "conflict",
            ["no es critica", "las ventas se detienen"],
        )
    )
    analysis = BusinessCaseAnalysis.model_validate(valid)
    assert analysis.requirements.business_continuity_criticality.status.value == "conflict"

    invalid = analysis_payload(
        business_continuity_criticality=requirement(
            "high",
            "conflict",
            ["no es critica", "las ventas se detienen"],
        )
    )
    with pytest.raises(ValidationError):
        BusinessCaseAnalysis.model_validate(invalid)


def test_missing_requirements_are_derived_from_unknown_values() -> None:
    payload = analysis_payload(
        available_budget=requirement("low", "detected", ["presupuesto limitado"])
    )

    analysis = BusinessCaseAnalysis.model_validate(payload)

    missing = [item.value for item in analysis.missing_requirements]
    assert "available_budget" not in missing
    assert len(missing) == 5


def test_schema_rejects_architecture_fields() -> None:
    payload = analysis_payload()
    payload["architecture"] = "C"

    with pytest.raises(ValidationError):
        BusinessCaseAnalysis.model_validate(payload)
