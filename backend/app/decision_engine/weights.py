"""Conversion del ranking de prioridades del usuario a pesos por variable.

Decisiones cerradas (docs/motor_de_reglas_puntaje_ponderado.md, seccion 4):
- Formula suavizada por posicion: 32.5 / 27.5 / 22.5 / 17.5 %. Asi el pilar que el
  usuario puso ultimo conserva un peso relevante.
- El peso de cada pilar se reparte en partes iguales entre sus variables.
- Ranking ausente o incompleto -> 25 % por pilar. No se le pide nada mas al usuario.
"""

from collections.abc import Mapping

from app.schemas.business_case import BusinessPriorityStatement, RequirementKey

RANK_WEIGHTS: tuple[float, float, float, float] = (0.325, 0.275, 0.225, 0.175)
EQUAL_PILLAR_WEIGHT: float = 0.25

# Cada afirmacion de negocio gobierna las variables de su pilar:
# Reliability, Cost Optimization, Performance Efficiency y Security.
STATEMENT_VARIABLES: dict[BusinessPriorityStatement, tuple[RequirementKey, ...]] = {
    BusinessPriorityStatement.NEVER_STOP_WORKING: (
        RequirementKey.SERVICE_INTERRUPTION_TOLERANCE,
        RequirementKey.BUSINESS_CONTINUITY_CRITICALITY,
    ),
    BusinessPriorityStatement.LOWEST_COST: (RequirementKey.AVAILABLE_BUDGET,),
    BusinessPriorityStatement.FAST_UNDER_LOAD: (
        RequirementKey.DEMAND_PATTERN,
        RequirementKey.EXPECTED_LOAD_VOLUME,
    ),
    BusinessPriorityStatement.PROTECT_INFORMATION: (RequirementKey.INFORMATION_SENSITIVITY,),
}


def is_complete_ranking(ranking: Mapping[BusinessPriorityStatement, int] | None) -> bool:
    """True solo si estan las 4 afirmaciones con las posiciones 1, 2, 3 y 4 sin repetir."""
    if ranking is None or set(ranking) != set(BusinessPriorityStatement):
        return False
    return sorted(ranking.values()) == [1, 2, 3, 4]


def rank_to_weights(
    ranking: Mapping[BusinessPriorityStatement, int] | None,
) -> dict[RequirementKey, float]:
    """Devuelve el peso de cada una de las 6 variables; los pesos suman 1."""
    if is_complete_ranking(ranking):
        assert ranking is not None  # para el type checker; is_complete_ranking ya lo verifico
        pillar_weight = {
            statement: RANK_WEIGHTS[position - 1] for statement, position in ranking.items()
        }
    else:
        pillar_weight = dict.fromkeys(BusinessPriorityStatement, EQUAL_PILLAR_WEIGHT)

    weights: dict[RequirementKey, float] = {}
    for statement, variables in STATEMENT_VARIABLES.items():
        share = pillar_weight[statement] / len(variables)
        for key in variables:
            weights[key] = share
    return {key: weights[key] for key in RequirementKey}
