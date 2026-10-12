"""Datos compartidos por los tests del motor de decision."""

from app.schemas.business_case import RequirementKey

# Caso de la seccion 5 de docs/motor_de_reglas_puntaje_ponderado.md:
# tolerancia media, criticidad alta, datos medio, presupuesto medio,
# picos predecibles, volumen medio.
DOC_REQUIREMENTS: dict[RequirementKey, str] = {
    RequirementKey.SERVICE_INTERRUPTION_TOLERANCE: "medium",
    RequirementKey.BUSINESS_CONTINUITY_CRITICALITY: "high",
    RequirementKey.INFORMATION_SENSITIVITY: "medium",
    RequirementKey.AVAILABLE_BUDGET: "medium",
    RequirementKey.DEMAND_PATTERN: "predictable_peaks",
    RequirementKey.EXPECTED_LOAD_VOLUME: "medium",
}

# Pesos de la Opcion A (lineal 40/30/20/10) que usa ese ejemplo del documento.
DOC_WEIGHTS: dict[RequirementKey, float] = {
    RequirementKey.SERVICE_INTERRUPTION_TOLERANCE: 0.20,
    RequirementKey.BUSINESS_CONTINUITY_CRITICALITY: 0.20,
    RequirementKey.INFORMATION_SENSITIVITY: 0.10,
    RequirementKey.AVAILABLE_BUDGET: 0.20,
    RequirementKey.DEMAND_PATTERN: 0.15,
    RequirementKey.EXPECTED_LOAD_VOLUME: 0.15,
}
