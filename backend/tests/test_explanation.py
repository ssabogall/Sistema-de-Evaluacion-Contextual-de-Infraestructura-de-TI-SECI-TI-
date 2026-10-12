from app.decision_engine.architectures import ArchitectureId as A
from app.decision_engine.explanation import build_message
from app.decision_engine.scoring import score_by_variable, unknown_variables
from app.decision_engine.selection import select
from app.schemas.business_case import RequirementKey as K
from tests.engine_fixtures import DOC_REQUIREMENTS, DOC_WEIGHTS


def _build(requirements, weights=DOC_WEIGHTS) -> str:
    contributions = score_by_variable(requirements, weights)
    result = select(contributions)
    return build_message(result, contributions, unknown_variables(requirements))


def test_worked_example_message_names_winner_top_variables_and_runner_up() -> None:
    assert _build(DOC_REQUIREMENTS) == (
        "Se recomienda la Arquitectura B (escalable), con un puntaje de 1.70. "
        "Lo que más pesó a su favor: la tolerancia a interrupciones del servicio y el "
        "presupuesto disponible. "
        "La Arquitectura C (resiliente) quedó muy cerca, a 0.30 puntos. "
        "Estaba mejor posicionada en la criticidad de continuidad del negocio."
    )


def test_clear_winner_has_no_trade_off_text() -> None:
    requirements = {
        K.SERVICE_INTERRUPTION_TOLERANCE: "high",
        K.BUSINESS_CONTINUITY_CRITICALITY: "low",
        K.INFORMATION_SENSITIVITY: "low",
        K.AVAILABLE_BUDGET: "low",
        K.DEMAND_PATTERN: "constant",
        K.EXPECTED_LOAD_VOLUME: "low",
    }
    message = _build(requirements)
    assert message.startswith("Se recomienda la Arquitectura A (básica)")
    assert "quedó muy cerca" not in message


def test_unknown_variable_is_never_presented_as_a_reason_for_the_winner() -> None:
    # Peso enorme en la variable desconocida: su valor neutro (0.5 x 0.6 = 0.30) seria la
    # contribucion mas alta del ganador, asi que sin el filtro apareceria como "razon".
    weights = {key: 0.08 for key in K} | {K.SERVICE_INTERRUPTION_TOLERANCE: 0.60}
    requirements = {**DOC_REQUIREMENTS, K.SERVICE_INTERRUPTION_TOLERANCE: "unknown"}
    message = _build(requirements, weights)
    assert (
        "Lo que más pesó a su favor: el presupuesto disponible y el patrón de demanda." in message
    )
    assert message.endswith(
        "No había información sobre la tolerancia a interrupciones del servicio; "
        "se usó un valor neutro para esos datos."
    )
    assert message.count("tolerancia a interrupciones") == 1  # solo en la nota de datos faltantes


def test_exact_tie_is_explained_as_such() -> None:
    contributions = {
        A.A: {key: 0.0 for key in K},
        A.B: {key: 0.0 for key in K} | {K.AVAILABLE_BUDGET: 1.0},
        A.C: {key: 0.0 for key in K} | {K.DEMAND_PATTERN: 1.0},
    }
    message = build_message(select(contributions), contributions)
    assert "exactamente el mismo puntaje" in message
    assert "por el orden del catálogo" in message


def test_no_positive_contribution_omits_the_reasons_sentence() -> None:
    contributions = {
        A.A: {key: -0.1 for key in K},
        A.B: {key: -0.2 for key in K},
        A.C: {key: -0.3 for key in K},
    }
    assert "Lo que más pesó" not in build_message(select(contributions), contributions)
