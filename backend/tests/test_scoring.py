import pytest

from app.decision_engine.architectures import ArchitectureId
from app.decision_engine.compatibility_table import CompatibilityLookupError
from app.decision_engine.scoring import UNKNOWN_SCORE, score_by_variable, unknown_variables
from app.schemas.business_case import DemandPattern, RequirementKey, StandardLevel
from tests.engine_fixtures import DOC_REQUIREMENTS, DOC_WEIGHTS


def _total(contributions, architecture: ArchitectureId) -> float:
    return sum(contributions[architecture].values())


def test_matches_the_worked_example_in_the_design_document() -> None:
    contributions = score_by_variable(DOC_REQUIREMENTS, DOC_WEIGHTS)
    assert _total(contributions, ArchitectureId.A) == pytest.approx(-0.35, abs=1e-9)
    assert _total(contributions, ArchitectureId.B) == pytest.approx(1.70, abs=1e-9)
    assert _total(contributions, ArchitectureId.C) == pytest.approx(1.40, abs=1e-9)


def test_returns_every_architecture_and_every_variable() -> None:
    contributions = score_by_variable(DOC_REQUIREMENTS, DOC_WEIGHTS)
    assert set(contributions) == set(ArchitectureId)
    for per_variable in contributions.values():
        assert list(per_variable) == list(RequirementKey)


def test_unknown_is_neutral_half_point_times_weight_for_all_architectures() -> None:
    requirements = {**DOC_REQUIREMENTS, RequirementKey.AVAILABLE_BUDGET: "unknown"}
    contributions = score_by_variable(requirements, DOC_WEIGHTS)
    expected = DOC_WEIGHTS[RequirementKey.AVAILABLE_BUDGET] * UNKNOWN_SCORE
    for architecture in ArchitectureId:
        assert contributions[architecture][RequirementKey.AVAILABLE_BUDGET] == pytest.approx(
            expected, abs=1e-9
        )


def test_unknown_does_not_change_which_architecture_has_the_highest_total() -> None:
    known = score_by_variable(DOC_REQUIREMENTS, DOC_WEIGHTS)
    requirements = {**DOC_REQUIREMENTS, RequirementKey.INFORMATION_SENSITIVITY: "unknown"}
    with_unknown = score_by_variable(requirements, DOC_WEIGHTS)

    def best(contributions):
        return max(ArchitectureId, key=lambda a: _total(contributions, a))

    assert best(known) == best(with_unknown) == ArchitectureId.B


def test_accepts_enum_members_as_levels() -> None:
    requirements = {
        **DOC_REQUIREMENTS,
        RequirementKey.AVAILABLE_BUDGET: StandardLevel.MEDIUM,
        RequirementKey.DEMAND_PATTERN: DemandPattern.PREDICTABLE_PEAKS,
    }
    assert score_by_variable(requirements, DOC_WEIGHTS) == score_by_variable(
        DOC_REQUIREMENTS, DOC_WEIGHTS
    )


def test_enum_unknown_is_also_treated_as_unknown() -> None:
    requirements = {**DOC_REQUIREMENTS, RequirementKey.DEMAND_PATTERN: DemandPattern.UNKNOWN}
    assert unknown_variables(requirements) == (RequirementKey.DEMAND_PATTERN,)


def test_unknown_variables_are_listed_in_canonical_order() -> None:
    requirements = {
        **DOC_REQUIREMENTS,
        RequirementKey.EXPECTED_LOAD_VOLUME: "unknown",
        RequirementKey.INFORMATION_SENSITIVITY: "unknown",
    }
    assert unknown_variables(requirements) == (
        RequirementKey.INFORMATION_SENSITIVITY,
        RequirementKey.EXPECTED_LOAD_VOLUME,
    )


def test_missing_requirement_raises_value_error() -> None:
    incomplete = {k: v for k, v in DOC_REQUIREMENTS.items() if k != RequirementKey.DEMAND_PATTERN}
    with pytest.raises(ValueError):
        score_by_variable(incomplete, DOC_WEIGHTS)


def test_missing_weight_raises_value_error() -> None:
    incomplete = {k: v for k, v in DOC_WEIGHTS.items() if k != RequirementKey.DEMAND_PATTERN}
    with pytest.raises(ValueError):
        score_by_variable(DOC_REQUIREMENTS, incomplete)


def test_level_that_does_not_belong_to_the_variable_is_not_silently_scored() -> None:
    requirements = {**DOC_REQUIREMENTS, RequirementKey.DEMAND_PATTERN: "high"}
    with pytest.raises(CompatibilityLookupError):
        score_by_variable(requirements, DOC_WEIGHTS)
