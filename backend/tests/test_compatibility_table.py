import pytest

from app.decision_engine.architectures import ArchitectureId
from app.decision_engine.compatibility_table import (
    COMPATIBILITY_TABLE,
    CompatibilityLookupError,
    get_score,
)
from app.schemas.business_case import (
    DemandPattern,
    RequirementKey,
    ServiceInterruptionTolerance,
    StandardLevel,
)

STANDARD_LEVELS = {StandardLevel.LOW, StandardLevel.MEDIUM, StandardLevel.HIGH}

# Niveles que DEBE tener cada variable (sin 'unknown': ese caso lo resuelve
# scoring.py antes de consultar la tabla).
EXPECTED_LEVELS = {
    key: STANDARD_LEVELS
    for key in RequirementKey
    if key is not RequirementKey.DEMAND_PATTERN
}
EXPECTED_LEVELS[RequirementKey.DEMAND_PATTERN] = {
    DemandPattern.CONSTANT,
    DemandPattern.PREDICTABLE_PEAKS,
    DemandPattern.UNPREDICTABLE_PEAKS,
}


def test_table_covers_every_requirement_key() -> None:
    assert set(COMPATIBILITY_TABLE) == set(RequirementKey)


@pytest.mark.parametrize("key", list(RequirementKey))
def test_each_key_has_exactly_the_expected_levels(key: RequirementKey) -> None:
    assert set(COMPATIBILITY_TABLE[key]) == EXPECTED_LEVELS[key]


@pytest.mark.parametrize("key", list(RequirementKey))
def test_each_level_scores_all_three_architectures_in_range(
    key: RequirementKey,
) -> None:
    for level, row in COMPATIBILITY_TABLE[key].items():
        assert set(row) == set(ArchitectureId), (key, level)
        assert all(-2 <= score <= 3 for score in row.values()), (key, level)


def test_get_score_returns_float_from_table() -> None:
    score = get_score(
        RequirementKey.AVAILABLE_BUDGET, StandardLevel.LOW, ArchitectureId.A
    )
    assert score == 3.0
    assert isinstance(score, float)


def test_get_score_accepts_service_interruption_enum() -> None:
    score = get_score(
        RequirementKey.SERVICE_INTERRUPTION_TOLERANCE,
        ServiceInterruptionTolerance.LOW,
        ArchitectureId.C,
    )
    assert score == 3.0


def test_unpredictable_peaks_row_matches_document() -> None:
    expected = {ArchitectureId.A: -2, ArchitectureId.B: 1, ArchitectureId.C: 2}
    row = COMPATIBILITY_TABLE[RequirementKey.DEMAND_PATTERN][
        DemandPattern.UNPREDICTABLE_PEAKS
    ]
    assert row == expected


def test_high_load_volume_favors_architecture_c() -> None:
    score = get_score(
        RequirementKey.EXPECTED_LOAD_VOLUME, StandardLevel.HIGH, ArchitectureId.C
    )
    assert score == 2.0


@pytest.mark.parametrize(
    ("key", "level"),
    [
        (RequirementKey.AVAILABLE_BUDGET, StandardLevel.UNKNOWN),
        (RequirementKey.DEMAND_PATTERN, DemandPattern.UNKNOWN),
        # Nivel de otra variable: antes de corregir la tabla esto "funcionaba"
        (RequirementKey.DEMAND_PATTERN, StandardLevel.LOW),
        (RequirementKey.AVAILABLE_BUDGET, "typo"),
    ],
)
def test_get_score_raises_on_missing_combination(
    key: RequirementKey, level: str
) -> None:
    with pytest.raises(CompatibilityLookupError):
        get_score(key, level, ArchitectureId.A)