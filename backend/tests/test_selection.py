import pytest

from app.decision_engine.architectures import ArchitectureId as A
from app.decision_engine.scoring import score_by_variable
from app.decision_engine.selection import select
from app.schemas.business_case import RequirementKey as K
from tests.engine_fixtures import DOC_REQUIREMENTS, DOC_WEIGHTS


def _single(a: float, b: float, c: float) -> dict[A, dict[K, float]]:
    """Contribuciones donde todo el puntaje de cada arquitectura esta en una variable."""
    zero = {key: 0.0 for key in K}
    return {
        A.A: {**zero, K.AVAILABLE_BUDGET: a},
        A.B: {**zero, K.AVAILABLE_BUDGET: b},
        A.C: {**zero, K.AVAILABLE_BUDGET: c},
    }


def test_worked_example_picks_b_and_flags_c_as_a_close_second() -> None:
    result = select(score_by_variable(DOC_REQUIREMENTS, DOC_WEIGHTS))
    assert result.winner == A.B
    assert result.runner_up == A.C
    assert result.totals[A.B] == pytest.approx(1.70, abs=1e-9)
    assert result.margin == pytest.approx(0.30, abs=1e-9)
    assert result.trade_off is True  # 0.30 < 20 % de 1.70 = 0.34
    assert result.tie_broken is False


def test_separating_variables_are_ordered_by_size_then_declaration_order() -> None:
    result = select(score_by_variable(DOC_REQUIREMENTS, DOC_WEIGHTS))
    assert result.separating_variables == (
        K.BUSINESS_CONTINUITY_CRITICALITY,  # |-0.40|: unica que favorece a C
        K.SERVICE_INTERRUPTION_TOLERANCE,  # |0.20| empata con presupuesto -> orden de K
        K.AVAILABLE_BUDGET,
        K.DEMAND_PATTERN,  # |0.15| empata con volumen -> orden de K
        K.EXPECTED_LOAD_VOLUME,
    )
    assert result.deltas[K.BUSINESS_CONTINUITY_CRITICALITY] == pytest.approx(-0.40, abs=1e-9)
    assert K.INFORMATION_SENSITIVITY not in result.separating_variables  # delta 0


def test_clear_winner_is_not_a_trade_off() -> None:
    result = select(_single(a=0.0, b=2.0, c=0.5))
    assert result.winner == A.B
    assert result.trade_off is False


def test_margin_exactly_at_the_threshold_is_not_a_trade_off() -> None:
    # 1.0 - 0.8 en coma flotante da 0.19999999999999996: el redondeo evita falsear el borde.
    result = select(_single(a=1.0, b=0.8, c=0.0))
    assert result.margin == 0.2
    assert result.trade_off is False


def test_margin_just_under_the_threshold_is_a_trade_off() -> None:
    assert select(_single(a=1.0, b=0.81, c=0.0)).trade_off is True


def test_exact_tie_goes_to_the_earliest_architecture_in_the_catalog() -> None:
    result = select(_single(a=0.0, b=1.0, c=1.0))
    assert result.winner == A.B
    assert result.runner_up == A.C
    assert result.margin == 0
    assert result.tie_broken is True
    assert result.trade_off is True


def test_three_way_tie_picks_a_then_b() -> None:
    result = select(_single(a=1.0, b=1.0, c=1.0))
    assert (result.winner, result.runner_up) == (A.A, A.B)


def test_float_noise_does_not_break_a_tie() -> None:
    result = select(_single(a=0.1 + 0.2, b=0.3, c=0.0))
    assert result.tie_broken is True
    assert result.winner == A.A


def test_missing_architecture_raises_value_error() -> None:
    contributions = _single(1.0, 0.5, 0.2)
    del contributions[A.C]
    with pytest.raises(ValueError):
        select(contributions)
